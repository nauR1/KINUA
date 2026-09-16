# Backup e recuperação — KINUA

**Última validação operacional:** 16/09/2026.

Este documento descreve o procedimento atual de backup/restauração. Ele não substitui uma política formal de continuidade de negócio.

## Estado atual

- Banco PostgreSQL persistente com volume montado em `/var/lib/postgresql/data`.
- Backup automático diário às **06:15 UTC**.
- Formato: `pg_dump --format=custom --no-owner --no-privileges`.
- Destino: bucket privado S3 `kinua-media`, prefixo `backups/postgres/`.
- Cada dump recebe arquivo `.sha256` correspondente.
- Um backup imediato também é usado como validação da automação após configuração/restart do serviço.

## Evidência de restauração

Em 16/09/2026 foi executado um drill em PostgreSQL auxiliar descartável:

1. download do backup real do S3;
2. restore em banco vazio com `pg_restore`;
3. conferência de tabelas e Alembic;
4. verificação de tabelas essenciais.

Resultado:

- 28 tabelas recuperadas;
- migration `9e1609260000`;
- `clinics`, `users`, `patients`, `assessments` presentes;
- `KINUA_RESTORE_DRILL overall=PASS`.

## Restore de desastre

Nunca testar restore destrutivo no banco de produção.

Procedimento recomendado:

1. criar PostgreSQL descartável/isolado;
2. obter o backup desejado do bucket;
3. verificar SHA-256 antes do restore;
4. restaurar com `pg_restore --clean --if-exists --no-owner --no-privileges`;
5. conferir `alembic_version`;
6. conferir contagem de tabelas e tabelas críticas;
7. iniciar uma instância de aplicação apontada **somente** para esse banco restaurado;
8. executar smoke test sintético de login, paciente, avaliação e PDF quando apropriado;
9. destruir o ambiente de drill após registrar evidência.

## Mídia

O PostgreSQL não contém os binários de imagem/vídeo. A mídia clínica reside no S3. Portanto, continuidade completa exige preservar **banco + objetos do bucket** de forma coerente.

O teste de bucket em 16/09 aprovou put/get/delete, mas isso não é um backup versionado de mídia. Antes de ampliar uso com dados reais, definir retenção/versionamento/lifecycle do bucket e procedimento de recuperação de objetos removidos/corrompidos.

## RPO/RTO

Ainda não há metas formais aprovadas. Com um backup diário, a perda máxima teórica pode se aproximar do intervalo entre backups se não houver outro mecanismo de recuperação. A equipe deve definir:

- RPO máximo aceitável;
- RTO máximo aceitável;
- retenção diária/semanal/mensal;
- quantidade mínima de cópias independentes;
- responsável por revisar falhas;
- frequência de restore drill.

Recomendação inicial: restore drill trimestral e verificação automática diária de backup recente/tamanho/hash, ajustando após definição de risco e volume.

## Alertas recomendados

Criar alerta para:

- backup não gerado no horário esperado;
- arquivo vazio ou SHA ausente;
- falha de upload S3;
- disco acima de 70/80/90%;
- banco indisponível;
- erro de restore drill;
- crescimento anormal de mídia ou dumps.

## Segurança

- nunca registrar senha, URL completa com credencial ou secret S3 em logs/documentação;
- restringir credenciais de backup ao menor escopo possível;
- revisar rotação de secrets;
- tratar backup como dado sensível equivalente ao banco de produção;
- registrar quem executou restore manual e em qual ambiente.
