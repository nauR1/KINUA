# KINUA 2.3.0

Plataforma web para apoio à avaliação fisioterapêutica com pacientes, foto/webcam, vídeo, MediaPipe, medições geométricas, análise temporal, Assessment Protocols, ROM, revisão profissional, histórico, relatórios PDF e administração comercial multi-tenant.

> **Estado atual:** consulte [`docs/estado-atual.md`](docs/estado-atual.md). Auditorias antigas são evidência histórica, não descrição da produção presente.

## Produção

Em 18/09/2026, frontend, backend e worker estavam `SUCCESS` no Railway no SHA `975db156b538eed678144deb3a5d3be7b6883306`. O PostgreSQL persistente foi separado da automação de backup, dois dumps reais foram validados após a mudança e o head Alembic atual é `a91809260001`. O último restore drill completo permanece o de 16/09/2026 e deve ser repetido no head atual.

Isso comprova engenharia/infraestrutura, **não validação clínica ou liberação regulatória**.

## Stack

### Frontend
- Node 22
- Next.js 16.3.4 resolvido
- React/React DOM 19.2.8 resolvidos
- TypeScript 5.9.3
- `@mediapipe/tasks-vision` 0.10.32
- Vitest + Playwright

### Backend/worker
- Python 3.12
- FastAPI 0.141.1
- SQLAlchemy 2.0.52
- Alembic 1.19.2
- PostgreSQL/psycopg 3.3.5
- MediaPipe Python 0.10.35
- OpenCV contrib 5.0.0.93
- ReportLab 5.0.1
- boto3/S3

Modelo de visão: `pose_landmarker_lite/float16/1`, SHA-256 `59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a`.

Versões completas: [`docs/third-party.md`](docs/third-party.md).

## Arquitetura

```text
Browser / Next.js
  ├─ foto/webcam → MediaPipe Web Worker
  └─ /api → FastAPI
             ├─ PostgreSQL
             ├─ S3 privado
             ├─ biomecânica / ROM / protocolos
             ├─ revisão / PDF
             └─ jobs → worker MediaPipe/OpenCV
```

Detalhes: [`docs/architecture.md`](docs/architecture.md).

## Funcionalidades atuais

- autenticação por sessão e isolamento por clínica;
- papéis `platform_admin`, `admin`, `physiotherapist`;
- planos trial/monthly/quarterly/annual/custom/lifetime;
- início/expiração por clínica e override individual;
- cadastro/edição/histórico de pacientes;
- captura de foto e câmera com skeleton;
- upload/processamento de vídeo MP4, WebM e MOV/QuickTime decodificável;
- análise temporal e movimentos;
- Assessment Protocols;
- KINUA ROM;
- revisão profissional, conclusão e PDF;
- comparação longitudinal compatível;
- ambiente demo isolado;
- auditoria comercial/clínica;
- storage S3 privado;
- backup PostgreSQL isolado do processo do banco;
- restore drill protegido e documentado.

## Instalação local

Requisitos: Python 3.12, Node.js 22, npm e opcionalmente PostgreSQL 17+.

### Backend

```sh
python -m venv .venv
# ative o ambiente
pip install -r backend/requirements.txt
cd backend
python -m alembic upgrade head
python -m app.vision.provider
python -m app.seed
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Em outro terminal:

```sh
cd backend
python -m app.jobs
```

### Frontend

```sh
cd frontend
npm ci
npm run prepare:vision
npm run dev
```

Abra `http://127.0.0.1:3000`.

Para produção/Compose, consulte [`docs/deployment.md`](docs/deployment.md).

## Testes

Backend:

```sh
cd backend
python -m pytest -q
python -m alembic check
```

Frontend:

```sh
cd frontend
npm ci
npm run prepare:vision
npm run typecheck
npm run lint
npm test
npm run build
```

No SHA de aplicação `975db156...`, a suíte backend contém 219 testes e o workflow normal da `main` concluiu com sucesso. O CI também valida a imagem/scripts de operações PostgreSQL. Números de auditorias antigas devem ser lidos como históricos.

E2E de escrita devem rodar somente contra banco/tenant sintético e isolado. Nunca apontar Playwright/pytest de escrita para pacientes reais.

## Segurança e privacidade

Produção usa cookies Secure/HttpOnly/SameSite Strict, CORS/origens explícitas, storage privado, tenant scope e proteção anti-indexação. O repositório ainda está público e a `main` sem branch protection; MFA e recuperação self-service de senha também permanecem pendentes.

Veja [`docs/privacy-security.md`](docs/privacy-security.md).

## Backup

Backup PostgreSQL diário às 06:15 UTC para S3, executado fora do processo do banco. Em 18/09/2026 dois dumps reais passaram com 28 tabelas e Alembic `a91809260001`; o restore drill completo do head atual ainda precisa ser repetido.

Veja [`docs/backup-recovery.md`](docs/backup-recovery.md).

## Limites clínicos

KINUA separa medição objetiva de interpretação profissional. Visibility/qualidade do modelo não é “confiança diagnóstica”. Perspectiva, oclusão, posicionamento e câmera podem alterar medidas. Acurácia e confiabilidade precisam ser estudadas contra referência apropriada antes de afirmações clínicas quantitativas.

Veja [`docs/clinical-readiness.md`](docs/clinical-readiness.md) e [`docs/clinical-validation-protocol.md`](docs/clinical-validation-protocol.md).

## Documentação

Índice e política documental: [`docs/README.md`](docs/README.md).

Principais documentos vivos:

- [`docs/estado-atual.md`](docs/estado-atual.md)
- [`docs/architecture.md`](docs/architecture.md)
- [`docs/deployment.md`](docs/deployment.md)
- [`docs/backup-recovery.md`](docs/backup-recovery.md)
- [`docs/access-control.md`](docs/access-control.md)
- [`docs/privacy-security.md`](docs/privacy-security.md)
- [`docs/api.md`](docs/api.md)
- [`docs/protocols.md`](docs/protocols.md)
- [`docs/rom.md`](docs/rom.md)
- [`docs/movements.md`](docs/movements.md)
- [`docs/roadmap.md`](docs/roadmap.md)
