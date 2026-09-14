# Implantação KINUA 2.3

A configuração abaixo prepara infraestrutura; não declara validação clínica/regulatória. Deploy na conta Railway e bucket real: **NÃO VALIDADO nesta rodada**. O provider S3 foi testado offline com cliente simulado.

## Railway: serviços
Use a raiz do repositório (onde estão backend, frontend e infra) como root directory em todos os serviços de código. Crie no mesmo projeto/ambiente:
1. PostgreSQL gerenciado.
2. Bucket privado de storage.
3. Serviço chamado backend, com RAILWAY_DOCKERFILE_PATH=infra/backend.Dockerfile.
4. Serviço worker com o mesmo Dockerfile, start command: python -m app.jobs.
5. Serviço frontend com RAILWAY_DOCKERFILE_PATH=infra/frontend.Dockerfile.

### Backend e worker: mesmas variáveis
```env
DATABASE_URL=${{Postgres.DATABASE_URL}}
ENVIRONMENT=production
SECURE_COOKIES=true
ALLOWED_ORIGINS=https://SEU-DOMINIO-FRONTEND
STORAGE_BACKEND=s3
S3_ENDPOINT_URL=VALOR-DA-ABA-CREDENTIALS-DO-BUCKET
S3_REGION=REGIAO-DA-ABA-CREDENTIALS
S3_BUCKET=NOME-EXATO-DO-BUCKET
S3_ACCESS_KEY_ID=SECRET-DO-BUCKET
S3_SECRET_ACCESS_KEY=SECRET-DO-BUCKET
POSE_MODEL_PATH=/app/models/pose_landmarker_lite.task
```
Troque Postgres pelo nome real do serviço na referência Railway. O backend normaliza URLs postgres/postgresql para o driver psycopg. Nunca copie secrets para o frontend.
No backend defina PORT=8000 e healthcheck path /health. Não gere domínio público para backend/PostgreSQL; o frontend usa a rede privada.
O Dockerfile faz download do modelo com verificação de hash no build. Não monte um volume vazio sobre /app/models.

### Frontend
Configure BACKEND_URL=http://backend.railway.internal:8000 como variável disponível no build (Docker ARG). Use o nome real do serviço backend. Refaça o build quando mudar a URL; o rewrite é compilado.
HOSTNAME=0.0.0.0, PORT=3000. Gere domínio HTTPS somente para frontend e configure o target port 3000. Atualize ALLOWED_ORIGINS de API e worker para esse domínio exato; reimplante os serviços.
Não coloque S3_* no frontend. O navegador usa /api e cookies HttpOnly/Secure/SameSite strict no mesmo domínio. Mídia passa pela autorização da API; nenhuma URL pública ou presigned URL é devolvida.

### Ordem de partida e migrations
Faça backup, pare/aguarde jobs e suspenda tráfego de gravação antes do upgrade. Execute uma única vez, no container backend:
```sh
python -m alembic upgrade head
python -m alembic check
```
O CMD padrão do backend também executa upgrade; para rollout com réplicas use pre-deploy command único alembic upgrade head e start command uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log.
Inicie backend, confira healthcheck; depois worker e frontend. Worker não tem endpoint HTTP e deve permanecer sempre ativo; desative suspensão serverless para ele.
Execute o bootstrap conforme access-control.md via terminal seguro dentro do serviço backend. Não use uma conta clínica existente esperando promoção silenciosa.

## Local
Continue com STORAGE_BACKEND=local, STORAGE_DIR compartilhado entre API e worker, PostgreSQL ou SQLite, origens HTTP locais e SECURE_COOKIES=false. Siga o README para venv/npm/modelo/build. compose.yaml repassa as mesmas variáveis de storage a backend/worker.
Docker/Compose nesta máquina: **NÃO VALIDADO**, runtime ausente. Builds frontend e execução Python foram realizados fora do container.

## S3 e migração da mídia existente
Chaves UUID existentes são preservadas. Antes de trocar local por S3, copie os arquivos para o bucket usando exatamente storage_key, sem alterar nomes/extensões. Verifique quantidade, tamanho e SHA256 contra assessment_media e mantenha o original como backup até ensaio de leitura e restauração.
Trocar somente a variável não transfere arquivos. Não misture instâncias local/S3 ou buckets diferentes.
O provider usa autenticação S3 e virtual-hosted addressing, timeout e retries limitados. Cada análise materializa arquivos em diretório temporário privado, removido ao terminar; respostas FileResponse limpam após envio. Jobs encerrados abruptamente podem deixar temporários no disco efêmero até reciclagem da instância. Preveja espaço temporário para uploads/vídeos concorrentes.
Configure retenção/backups e criptografia do provedor; não presuma recuperação automática do bucket.

## Backup e verificação operacional
Faça backup PostgreSQL e da mídia coordenados antes da migration 7c301a230000. Ela acrescenta campos sem expirar usuários existentes. Não use create_all em produção.
Teste restauração em ambiente separado, login, vídeo/worker, PDF, expiração e suspensão antes de tráfego real. Downgrade remove os campos comerciais; use apenas banco descartável ou recuperação planejada.
Validar na conta: rede privada, HTTPS/cookies, secrets, bucket privado, quotas/disco, timeouts para vídeos, observabilidade, backup/restore e carga. Estes ensaios externos não foram executados aqui.

Referências oficiais consultadas: [Buckets](https://docs.railway.com/storage-buckets), [rede privada](https://docs.railway.com/networking/private-networking), [healthchecks](https://docs.railway.com/deployments/healthchecks), [Docker Compose em Railway](https://docs.railway.com/guides/docker-compose).
