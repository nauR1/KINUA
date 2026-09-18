# Implantação e operação — KINUA

**Estado verificado:** Railway production em 18/09/2026.

Este documento descreve a topologia realmente usada. Não implica validação clínica/regulatória.

## Topologia atual

Projeto Railway: `KINUA`, região `ams`.

1. `frontend` — `infra/frontend.Dockerfile`, Node 22, domínio público HTTPS, healthcheck `/`.
2. `backend` — `infra/backend.Dockerfile`, FastAPI/Uvicorn, pre-deploy `alembic upgrade head`, healthcheck `/health`.
3. `worker` — mesmo Dockerfile do backend, start `python -m app.jobs`.
4. `kinua-backup-once` — **PostgreSQL persistente de produção**. O nome é legado. Usa `postgres:17-alpine`, volume `kinua-postgres-data` de 500 MB em `/var/lib/postgresql/data` e start `docker-entrypoint.sh postgres`.
5. `postgres` — serviço sem volume reaproveitado como **cron de backup**, porque o plano Railway atual não permite provisionar outro serviço. Executa backup e termina; não atende tráfego da aplicação.
6. bucket `kinua-media` — storage S3 privado, região `ams`.

Frontend, backend e worker estão publicados no SHA `975db156b538eed678144deb3a5d3be7b6883306` e ficaram `SUCCESS`.

> O nome `kinua-backup-once` não representa mais sua função. Antes de qualquer operação de banco, identificar o serviço pelo volume `kinua-postgres-data`, não pelo nome.

## Mudança de 18/09/2026

Antes desta fase, o processo do PostgreSQL persistente também:

- instalava AWS CLI;
- restaurava backup no boot dependendo de marker;
- criava script de `pg_dump`;
- iniciava `crond`;
- executava backup imediato.

Essa lógica foi removida do processo de produção.

Agora:

```text
kinua-backup-once
  └─ postgres + volume persistente

postgres (sem volume)
  └─ cron Railway 06:15 UTC
      └─ pg_dump → validação → S3
```

Dois backups reais foram aprovados durante a migração, incluindo um após o restart do banco simplificado.

## Variáveis essenciais

Backend/worker:

```env
DATABASE_URL=...
ENVIRONMENT=production
APP_MODE=production
SECURE_COOKIES=true
ALLOWED_ORIGINS=https://SEU-FRONTEND
STORAGE_BACKEND=s3
S3_ENDPOINT_URL=...
S3_REGION=...
S3_BUCKET=kinua-media
S3_ACCESS_KEY_ID=...
S3_SECRET_ACCESS_KEY=...
ALLOW_DEMO_SEED=false
```

Job de backup:

```env
BACKUP_DATABASE_URL=...
BACKUP_PREFIX=backups/postgres
BACKUP_KEEP_COUNT=30
BACKUP_PRUNE_ENABLED=false
S3_ENDPOINT_URL=...
S3_REGION=...
S3_BUCKET=kinua-media
S3_ACCESS_KEY_ID=...
S3_SECRET_ACCESS_KEY=...
```

`BACKUP_DATABASE_URL` deve apontar para o PostgreSQL persistente. Não expor segredos em logs/documentação.

## Deploy da aplicação

1. confirmar backup recente;
2. verificar jobs em execução;
3. publicar commit aprovado na `main`;
4. backend executa `alembic upgrade head`;
5. aguardar healthcheck do backend;
6. verificar worker;
7. verificar frontend;
8. conferir SHA efetivamente publicado.

Nunca usar downgrade de schema em produção como rollback comum.

## Migration atual

Head esperado: `a91809260001`.

O workflow valida:

```sh
python -m alembic upgrade head
python -m alembic check
python -m alembic downgrade base
python -m alembic upgrade head
```

O round-trip destrutivo é somente para banco descartável de CI/QA.

## Storage S3

Backend e worker usam `STORAGE_BACKEND=s3`. Mídia é privada e sujeita a autorização de tenant.

O mesmo bucket contém atualmente o prefixo de backup PostgreSQL `backups/postgres/`. Isso é funcional, mas uma separação futura em bucket/credenciais dedicados para backup é recomendável quando o plano de infraestrutura permitir.

## PostgreSQL persistente

O volume de produção permanece:

- nome: `kinua-postgres-data`;
- mount: `/var/lib/postgresql/data`;
- tamanho observado: 500 MB;
- serviço atual: `kinua-backup-once`.

No restart de 18/09/2026 o entrypoint detectou dados existentes e pulou inicialização. O banco fez recuperação automática de WAL devido ao encerramento não limpo do wrapper antigo e ficou pronto para conexões. Um backup posterior confirmou 28 tabelas e Alembic `a91809260001`.

## Backup

Cron Railway: `15 6 * * *` UTC.

O job:

1. gera `pg_dump` custom;
2. valida arquivo com `pg_restore --list`;
3. consulta tabelas e Alembic;
4. calcula SHA-256;
5. envia dump + checksum + manifest;
6. confirma tamanho remoto;
7. termina.

O pruning existe no script, mas está desativado em produção até aprovação da política de retenção.

Detalhes: [`backup-recovery.md`](backup-recovery.md).

## Restore

Restore nunca roda dentro do processo PostgreSQL persistente.

`ops/postgres-restore-drill.sh` exige alvo descartável e confirmação explícita. O último drill completo real foi em 16/09/2026 no head antigo; o drill deve ser repetido no head `a91809260001` quando houver slot de serviço descartável disponível.

## Healthchecks e observabilidade

- frontend: `/`;
- backend: `/health`, `/health/live`, `/health/ready`;
- versão: `/version`;
- worker: processo/logs e estado dos jobs;
- PostgreSQL: logs e conectividade via backend/backup;
- backup: estado da execução cron + linha `KINUA backup: PASS`.

## Limitações operacionais atuais

- nomes de serviços de banco continuam históricos/ambíguos;
- plano Railway atingiu o limite de serviços, impedindo um serviço dedicado adicional de backup/restore;
- backup ainda compartilha o bucket de mídia;
- pruning está desligado;
- restore drill do head atual precisa ser repetido;
- RPO/RTO formais ainda precisam ser aprovados;
- alertas automáticos de falha de backup/disco/fila/5xx ainda precisam ser configurados.
