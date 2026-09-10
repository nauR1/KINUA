# Arquitetura e decisões

Monorepositório com Next.js/React/TypeScript e FastAPI/Pydantic/SQLAlchemy. PostgreSQL é o banco de implantação; SQLite existe apenas como alternativa local e para testes. Alembic gerencia o esquema em ambos.

## Fluxo
Captura ou upload → validação de mídia → PoseProvider no Web Worker → landmarks normalizados → API → BiomechanicsEngine → AttentionEngine → regras versionadas → revisão profissional → PDF.

Em fotos/webcam, MediaPipe opera no dispositivo; o backend calcula medidas a partir dos landmarks recebidos. Em vídeo, upload validado → ProcessingJob no PostgreSQL → subprocesso MediaPipe/OpenCV → MotionEngine → frames/séries/resumos → revisão. O provider Python permanece substituível. Nenhum caminho recebe medidas clínicas prontas do cliente. Resultados são snapshots imutáveis, com versão do modelo e motores. Novas capturas não reescrevem resultados antigos.

Componentes: `frontend/vision` e `backend/app/vision` contêm providers substituíveis; `backend/app/biomechanics` geometria pura; `backend/app/clinical` regras; `backend/app/services` orquestração/comparação; `backend/app/storage` mídia privada; `backend/app/jobs.py` fila durável. Geometria e esquema canônico não dependem de MediaPipe.

Autenticação: senha Argon2, token de sessão aleatório com hash no banco, cookie HttpOnly/SameSite, validade e revogação. Requisições mutáveis validam Origin. Recursos são isolados por clínica e todas as consultas de domínio exigem esse escopo. Arquivos são servidos após autorização, sem diretório público.

## Escopo e sequência
1. Autenticação, pacientes, avaliações, migração e auditoria.
2. Webcam/foto real, skeleton, upload separado e medição objetiva.
3. Revisão, histórico, PDF, testes e instalação reproduzível.
4. Vídeo e séries temporais; fases de agachamento somente experimentais até validação.

## Decisões de implantação
Sites foi avaliado: seu runtime Cloudflare Workers não executa este backend Python/PostgreSQL. Mantemos a stack e a entrega de repositório solicitadas, com execução local/Docker. Não publicamos uma interface sem backend acessível.

## Riscos
Medição 2D depende de perspectiva, roupa, oclusão e enquadramento. Visibility não é probabilidade clínica. Sem calibração não há centímetros, profundidade métrica ou diagnóstico. Câmera exige HTTPS ou localhost. Validação clínica e regulatória é uma etapa independente antes do uso assistencial. Desenvolvimento e demonstração usam dados fictícios.
