# Implantação e operação — KINUA 2.3.0

**Estado verificado:** Railway production em 16/09/2026.

Este documento descreve a topologia realmente usada. Não implica validação clínica/regulatória.

## Topologia atual

Projeto Railway: `KINUA`.

Serviços de aplicação:

1. `frontend` — `infra/frontend.Dockerfile`, Node 22, Next.js standalone, uma réplica em `ams`, domínio público HTTPS, healthcheck `/`.
2. `backend` — `infra/backend.Dockerfile`, Python 3.12, FastAPI/Uvicorn, uma réplica em `ams`, rede privada, pre-deploy `alembic upgrade head`, healthcheck `/health`.
3. `worker` — mesmo Dockerfile do backend, start `python -m app.jobs`, uma réplica em `ams`, sem endpoint público.
4. `postgres` — PostgreSQL 17 Alpine usado na infraestrutura de persistência/DR.
5. `kinua-backup-once` — serviço PostgreSQL 17 Alpine com volume persistente e automação de restore/backup.
6. bucket `kinua-media` — storage compatível com S3, região `ams`.

Frontend, backend e worker foram publicados no SHA `c21484f5ab07fdc9f9a8db61ba1e822d71f74e32` e ficaram `SUCCESS`.

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

Não expor segredos como `NEXT_PUBLIC_*`. O frontend precisa apenas da URL privada do backend durante o build/rewrite.

## Deploy

Sequência recomendada para release:

1. confirmar backup recente e saúde do bucket;
2. verificar jobs em execução e evitar troca de versão no meio de processamento crítico;
3. publicar commit aprovado na `main`;
4. backend executa `alembic upgrade head` no pre-deploy;
5. aguardar `/health` do backend;
6. verificar worker;
7. verificar frontend;
8. executar smoke test sintético de login/fluxo mínimo;
9. conferir SHA efetivamente publicado em cada serviço.

Nunca executar downgrade em produção para “corrigir” release. Rollback de aplicação deve respeitar compatibilidade de schema. Restore de banco é procedimento de desastre, não mecanismo comum de deploy.

## Migration atual

Head esperado: `9e1609260000`.

Após qualquer alteração de schema, validar em banco descartável:

```sh
python -m alembic upgrade head
python -m alembic check
python -m alembic downgrade base
python -m alembic upgrade head
python -m alembic check
```

Em produção, apenas `upgrade head`/`check` conforme plano de release; não usar o round-trip destrutivo.

## Storage S3

O backend e o worker usam `STORAGE_BACKEND=s3`. Foi executado teste real com arquivo temporário: put, get, comparação do conteúdo, delete e confirmação de exclusão, todos aprovados.

Chaves são privadas e continuam sujeitas à autorização de tenant. Não publicar bucket nem devolver URL pública de mídia clínica.

Vídeo aceito: MP4, WebM ou MOV/QuickTime **quando o conteúdo é válido e decodificável**. Aceitar extensão não substitui validação de contêiner/decoder.

## Banco persistente

O banco que atende o KINUA foi reiniciado em teste operacional; o volume foi remontado e os dados existentes foram reconhecidos sem reinicialização. O volume observado tinha 500 MB, com cerca de 0,111 GB usados na medição de 16/09/2026. Essa capacidade deve ser monitorada e ampliada antes de se aproximar do limite.

## Backup e desastre

O backup automático é executado diariamente às **06:15 UTC** e enviado ao S3 em formato custom do `pg_dump`, acompanhado de SHA-256.

Um drill de restauração real foi executado em PostgreSQL auxiliar descartável:

- backup baixado do S3;
- restore do zero;
- 28 tabelas recuperadas;
- Alembic `9e1609260000`;
- `clinics`, `users`, `patients` e `assessments` presentes;
- resultado `KINUA_RESTORE_DRILL overall=PASS`.

Detalhes operacionais em [`backup-recovery.md`](backup-recovery.md).

## Healthchecks

- frontend: `/`
- backend: `/health`, que também verifica acesso ao banco
- worker: observar processo/logs e progresso dos jobs; não há health HTTP atualmente

Recomendação: adicionar health/heartbeat explícito do worker ou métrica de último job/heartbeat para observabilidade externa.

## Local/Compose

O Compose permanece útil para desenvolvimento. A realidade de produção, porém, é Railway + PostgreSQL + S3. Não usar as limitações de auditorias locais antigas para descrever o estado da produção atual.

## Riscos operacionais ainda abertos

- definir RPO/RTO formais;
- política de retenção e expurgo de backups;
- alertas de disco, fila, falha de backup e erro 5xx;
- separar ainda mais responsabilidades de banco persistente e automação de backup quando a escala exigir;
- teste de carga/concorrrência;
- plano de incident response e rotação de segredos;
- conferir periodicamente que todos os serviços estão no mesmo release esperado.
