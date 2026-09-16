# Arquitetura e decisões — KINUA 2.3.0

## Visão geral

Monorepositório com frontend Next.js/React/TypeScript e backend FastAPI/Pydantic/SQLAlchemy. PostgreSQL é o banco de produção; SQLite permanece opção local. Alembic controla o schema. Mídia privada fica fora do banco, via `StorageProvider` local ou S3.

## Fluxo clínico

```text
Navegador
  ├─ foto/webcam → MediaPipe Web Worker → landmarks
  ├─ vídeo → upload privado
  └─ /api → proxy Next.js → FastAPI
                         ├─ autorização/tenant
                         ├─ PostgreSQL
                         ├─ storage S3
                         ├─ geometria/ROM/regras
                         ├─ revisão profissional/PDF
                         └─ ProcessingJob → worker Python → MediaPipe/OpenCV
```

Fotos/webcam: a inferência inicial ocorre no navegador; o backend valida a estrutura e calcula medidas. Vídeos: o arquivo persistido é processado pelo worker Python. Resultados registram versões/proveniência e avaliações concluídas não são reescritas.

## Componentes

- `frontend/app`, `frontend/components`: interface clínica/comercial.
- `frontend/vision`: provider browser, WASM, worker e skeleton.
- `backend/app/core`: configuração, banco, autenticação e acesso.
- `backend/app/biomechanics`: geometria e movimento.
- `backend/app/rom.py`: motor ROM (`rom-1.0.0`).
- `backend/app/clinical`: regras clínicas versionadas e separadas da medição.
- `backend/app/services`: análise, comparação e serialização.
- `backend/app/storage.py`: storage privado local/S3.
- `backend/app/jobs.py`: fila durável no PostgreSQL e worker.
- `backend/app/reports.py`: PDF.
- `backend/migrations`: Alembic; head atual `9e1609260000`.

## Infraestrutura de produção

Railway, região `ams`, com frontend, backend, worker, PostgreSQL persistente/serviço de backup e bucket S3. Frontend é o ponto público; backend/worker/banco devem permanecer privados. Healthchecks: `/` e `/health`.

## Autenticação e autorização

- senha Argon2;
- token de sessão aleatório, somente hash no banco;
- cookie HttpOnly/Secure/SameSite Strict em produção;
- sessão padrão de 8 h;
- CORS/origin explícito e cabeçalho anti-CSRF para mutações;
- `platform_admin` separado do domínio clínico;
- todos os recursos clínicos escopados por `clinic_id`.

## Acesso comercial

`Clinic` e `User` possuem estado e janela de acesso. Usuário sem override herda a clínica. Overrides individuais podem restringir. Lifetime não expira e não deve ser bloqueado por datas comerciais antigas herdadas. O backend usa UTC como fonte de verdade.

## Visão computacional e versionamento

Browser: `@mediapipe/tasks-vision 0.10.32`. Servidor: `mediapipe 0.10.35`. Ambos usam `pose_landmarker_lite/float16/1` com SHA-256 fixado no projeto. Atualizações devem passar por regressão comparativa e registro explícito das versões.

## Resiliência

- `ProcessingJob.run_token` isola tentativas e impede publicação tardia após cancel/retry.
- backup PostgreSQL diário para S3;
- restore drill real aprovado;
- storage S3 testado com put/get/delete;
- migrations aplicadas em pre-deploy do backend.

## Limitações arquiteturais atuais

- frontend ainda funciona majoritariamente como aplicação de página única por estado, sem URL própria para toda avaliação;
- lista de pacientes/usuários precisa evoluir para paginação server-side em escala;
- worker não possui health endpoint externo dedicado;
- fila usa PostgreSQL, suficiente no estágio atual, mas pode exigir fila/broker dedicado sob carga elevada;
- landmarks de foto gerados no cliente não possuem verificação independente completa contra a imagem no servidor;
- não existe isolamento entre profissionais dentro da mesma clínica;
- MFA e recuperação de senha ainda não existem.

## Princípio clínico

Medição objetiva e interpretação profissional permanecem separadas. Visibility é qualidade técnica do landmark, não probabilidade de correção clínica. O sistema não deve ativar thresholds/diagnósticos sem validação apropriada.
