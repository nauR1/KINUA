# Verificação de engenharia — KINUA 2.2

Data: 09/09/2026. Escopo: Assessment Protocols e ROM.

- Migration 6d49ba3c72e9: upgrade/check/downgrade/upgrade em PostgreSQL temporário; aplicação no banco local após cópia de segurança; alembic check sem divergência.
- 91 testes backend passaram em SQLite e 91 em PostgreSQL usando schemas isolados. Incluem 40 novos casos de protocolos/ROM.
- Dois testes unitários frontend passaram; TypeScript, Prettier e build de produção passaram.
- Cinco cenários E2E passaram em banco QA separado: protocolo/ROM completo, vídeo existente, foto existente, webcam existente e login responsivo. O teste de foto foi executado separadamente com E2E_IMAGE após ser omitido na primeira execução sem essa variável.
- MediaPipe real usado no navegador e no servidor com imagem/vídeo de fixture. As posições do fixture não representam avaliação clínica válida.
- Telas Protocolos/ROM verificadas em 1440, 768 e 390 pixels e tema escuro. Relatório agregado e relatório final renderizados e inspecionados.
- Ruff select F passou para app e tests; a seleção ampla de estilos do ambiente tem pendências legadas e não é apresentada como aprovada.

Permanecem avisos de depreciação de dependências FastAPI/Starlette e aviso do codec VP80 no OpenCV; os arquivos de teste foram processados com sucesso. Não houve teste com Docker nesta máquina, que não dispõe desse runtime.

Este registro valida integração e matemática com fixtures, não acurácia clínica, eficácia diagnóstica ou autorização para implantação pela internet. Seguem válidos os documentos de prontidão e segurança existentes. Etapas de módulos futuros permanecem indisponíveis e justificáveis; uma etapa ROM vincula uma avaliação filha por execução.
