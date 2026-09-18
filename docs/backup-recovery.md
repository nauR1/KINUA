# Backup e recuperação — KINUA

**Última validação operacional de backup:** 18/09/2026.  
**Último restore drill completo:** 16/09/2026.

Este documento descreve o procedimento operacional atual. Ele não substitui uma política formal de continuidade de negócio.

## Arquitetura atual

As responsabilidades foram separadas em 18/09/2026:

- `kinua-backup-once` é o PostgreSQL persistente de produção. Apesar do nome legado, seu processo agora executa apenas `docker-entrypoint.sh postgres`.
- O volume `kinua-postgres-data` permanece montado em `/var/lib/postgresql/data` no mesmo serviço persistente.
- O serviço Railway `postgres`, que não possui volume e era usado como banco auxiliar descartável, foi reaproveitado como job de backup por limitação de quantidade de serviços do plano atual.
- O job de backup roda via cron Railway às **06:15 UTC** e termina após concluir a tarefa.
- A implementação canônica está em `ops/postgres-backup.sh`; a imagem prevista para um serviço dedicado está em `infra/postgres-ops.Dockerfile`.
- O restore drill protegido está em `ops/postgres-restore-drill.sh`.

O processo PostgreSQL de produção não contém mais lógica de restore, instalação de AWS CLI, cron ou `pg_dump`.

## Backup

Formato:

```
pg_dump --format=custom --no-owner --no-privileges
```

Destino:

- bucket privado S3 `kinua-media`;
- prefixo `backups/postgres/`;
- dump `.custom`;
- checksum `.sha256`;
- manifest `.manifest.json`.

Antes de publicar o backup, o job:

1. executa `pg_dump`;
2. exige arquivo não vazio;
3. valida a estrutura com `pg_restore --list`;
4. consulta quantidade de tabelas públicas;
5. consulta `alembic_version`;
6. calcula SHA-256;
7. envia dump, checksum e manifest ao S3;
8. confirma o tamanho remoto com `head-object`.

O job não registra URL do banco, senha ou segredo S3.

## Evidência de 18/09/2026

Foram executados dois backups reais durante a separação da infraestrutura.

Antes da simplificação do processo PostgreSQL:

- key: `backups/postgres/kinua-20260918T013313Z.custom`;
- bytes: `641160`;
- tabelas públicas: `28`;
- Alembic: `a91809260001`;
- resultado: `PASS`.

Depois da simplificação e restart do PostgreSQL persistente:

- key: `backups/postgres/kinua-20260918T013510Z.custom`;
- bytes: `641160`;
- tabelas públicas: `28`;
- Alembic: `a91809260001`;
- resultado: `PASS`.

O segundo backup comprova que o volume permaneceu acessível e que o novo job consegue ler a base após a separação das responsabilidades.

## Retenção

O script suporta `BACKUP_KEEP_COUNT` e expurgo de dumps antigos em conjunto com seus arquivos `.sha256` e `.manifest.json`.

Na migração de 18/09/2026:

```
BACKUP_KEEP_COUNT=30
BACKUP_PRUNE_ENABLED=false
```

Portanto, **nenhum backup histórico foi apagado**. O expurgo deve ser habilitado somente depois de aprovar formalmente a política de retenção.

## Restore drill

Nunca executar restore destrutivo no banco de produção.

O script `ops/postgres-restore-drill.sh` exige:

```
RESTORE_DRILL_CONFIRM=KINUA_DISPOSABLE_ONLY
```

e recusa a execução se origem e destino forem a mesma URL de banco.

Procedimento:

1. disponibilizar PostgreSQL descartável/isolado;
2. configurar `RESTORE_DATABASE_URL` somente para esse banco;
3. obter o backup desejado do S3;
4. validar SHA-256;
5. validar o dump com `pg_restore --list`;
6. restaurar com `pg_restore --clean --if-exists --no-owner --no-privileges`;
7. conferir `alembic_version`;
8. conferir tabelas essenciais `clinics`, `users`, `patients` e `assessments`;
9. registrar `KINUA_RESTORE_DRILL overall=PASS`;
10. destruir ou reciclar o alvo descartável.

### Evidência histórica de restore

Em 16/09/2026 foi executado um drill completo em PostgreSQL auxiliar descartável:

- 28 tabelas recuperadas;
- Alembic `9e1609260000`;
- tabelas essenciais presentes;
- resultado `KINUA_RESTORE_DRILL overall=PASS`.

Após a migration `a91809260001`, backups reais foram validados, mas o restore drill completo ainda precisa ser repetido em um alvo descartável no head atual. O plano Railway atual atingiu o limite de provisionamento de serviços, então não foi criado um sexto serviço apenas para esse ensaio.

## Comportamento do restart de 18/09/2026

Ao retirar o wrapper antigo e iniciar o PostgreSQL diretamente pelo entrypoint oficial, o servidor detectou a base já existente no mesmo volume e pulou inicialização.

O primeiro boot com o processo simplificado executou recuperação automática de WAL porque o wrapper antigo não havia encerrado o processo PostgreSQL de forma limpa. A recuperação concluiu e o banco informou `database system is ready to accept connections`. O backup pós-restart confirmou 28 tabelas e Alembic `a91809260001`.

A arquitetura nova melhora esse ponto porque o PostgreSQL passa a ser o processo principal do container e recebe sinais diretamente.

## Mídia

O PostgreSQL não contém os binários de imagem/vídeo. A mídia clínica reside no S3. Continuidade completa exige preservar **banco + objetos do bucket**.

Backup do banco não substitui estratégia de versionamento/recuperação de objetos do bucket.

## RPO/RTO

Ainda não há metas formais aprovadas. O backup diário às 06:15 UTC limita a estratégia atual a um ponto de recuperação diário, salvo outros mecanismos do provedor.

Definir formalmente:

- RPO máximo aceitável;
- RTO máximo aceitável;
- retenção diária/semanal/mensal;
- quantidade mínima de cópias independentes;
- responsável por revisar falhas;
- frequência do restore drill.

Recomendação inicial: restore drill trimestral e verificação automática diária de backup recente/tamanho/hash.

## Alertas recomendados

Criar alerta para:

- execução cron ausente;
- job de backup diferente de `Completed/SUCCESS`;
- arquivo vazio ou checksum ausente;
- falha de upload S3;
- banco indisponível;
- disco acima de 70/80/90%;
- restore drill com falha;
- crescimento anormal de mídia ou dumps.

## Segurança

- nunca registrar senha, URL completa com credencial ou secret S3;
- restringir credenciais de backup ao menor escopo possível;
- rotacionar secrets de forma planejada;
- tratar backup como dado sensível equivalente ao banco clínico;
- registrar execução de restore manual e ambiente utilizado;
- manter restore destrutivo tecnicamente separado do PostgreSQL persistente.
