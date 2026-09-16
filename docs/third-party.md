# Componentes de terceiros e versões

Atualizado em 16/09/2026. Dependências são instaladas a partir de PyPI/npm e preservam as licenças de cada projeto. Antes de redistribuição comercial, revisar licenças/metadados das versões efetivamente resolvidas.

## Runtime principal

| Componente | Versão/linha atual |
|---|---|
| Python | 3.12 (`python:3.12-slim`) |
| Node.js | 22 (`node:22-bookworm-slim`) |
| PostgreSQL produção/infra | 17 Alpine |
| FastAPI | 0.141.1 |
| Starlette | 1.6.0 |
| Uvicorn | 0.52.4 |
| SQLAlchemy | 2.0.52 |
| Alembic | 1.19.2 |
| psycopg | 3.3.5 |
| Pydantic settings | 2.15.0 |
| Argon2 | argon2-cffi 25.1.0 |
| MediaPipe Python | 0.10.35 |
| OpenCV contrib Python | 5.0.0.93 |
| Pillow | 12.3.0 |
| ReportLab | 5.0.1 |
| boto3 | 1.43.93 |
| pypdf | 6.18.1 |
| Next.js resolvido | 16.3.4 |
| React resolvido | 19.2.8 |
| React DOM resolvido | 19.2.8 |
| TypeScript resolvido | 5.9.3 |
| Playwright resolvido | 1.63.0 |
| Vitest | 5.0.0 |
| Prettier | 3.6.2 |
| esbuild | 0.28.2 |
| lucide-react | 0.468.0 |
| MediaPipe Tasks Vision browser | 0.10.32 |

`package.json` usa algumas faixas `^`; para reprodução exata do frontend, o `package-lock.json` é a fonte de resolução. No backend, `requirements.txt` + `constraints.txt` fixam as versões.

## Modelo de pose

Provider: `MediaPipePoseProvider`  
Modelo: `pose_landmarker_lite/float16/1`  
SHA-256: `59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a`

Browser e servidor usam o mesmo artefato/hash do modelo. O script `frontend/scripts/prepare-vision.mjs` confere o hash e prepara WASM/worker. O backend também verifica o hash no build via `python -m app.vision.provider`.

## Compatibilidade browser versus servidor

Existe diferença intencional/atual de pacote:

- browser: `@mediapipe/tasks-vision 0.10.32`;
- servidor: `mediapipe 0.10.35`.

Isso não é tratado como falha por si só, mas deve ser controlado. Antes de atualizar qualquer um dos lados, executar regressão com fixtures comuns e comparar disponibilidade de landmarks, medidas, ROM e resultados temporais. Registrar as versões em qualquer estudo de validação clínica.

## Assets de integração

A imagem pública `pose.jpg` do projeto MediaPipe pode ser usada como fixture de engenharia, fora de dados clínicos. Fixtures sintéticas/públicas não representam validação clínica.

## Política de atualização

1. não atualizar modelo/MediaPipe silenciosamente;
2. atualizar lock/constraints no mesmo PR;
3. executar testes backend/frontend/E2E relevantes;
4. conferir build Docker/Railway;
5. registrar mudança em `estado-atual.md` e, se alterar inferência, em nova evidência de validação;
6. usar `npm audit`/auditoria Python e revisão de CVEs como sinal, não como substituto de security review.
