# KINUA 2.3 — Access & Commercial Administration

Esta versão acrescenta administração global, assinaturas/expiração, controle individual de acesso e storage S3 privado. Os módulos e algoritmos clínicos da 2.2.1 foram preservados.

- [Controle de acesso e bootstrap](docs/access-control.md)
- [Implantação Railway, storage e backup](docs/deployment.md)
- [Relatório da entrega 2.3](docs/release-2.3.md)

Atualização: faça backup, pare workers antigos, execute `python -m alembic upgrade head` e `python -m alembic check` no backend e recompile o frontend. Migration atual: `8d402b230000` (sucede `7c301a230000`). Clínicas e usuários existentes permanecem ativos, sem expiração. O primeiro administrador global exige bootstrap explícito; nenhum admin atual é promovido automaticamente.

## Histórico e instalação — KINUA

Inteligência em movimento humano. A versão 2.2.1 estabiliza o núcleo existente: autenticação, pacientes, foto/câmera/vídeo, Protocolos e ROM. Consulte o [relatório de auditoria](docs/audit-2.2.1.md) para correções, testes e limites. A identidade KINUA usa SVGs nativos e Manrope local.

Plataforma de avaliação corporal assistida para fisioterapeutas. Versão 2 executável de foto/webcam e vídeo, landmarks reais, medição geométrica 2D, revisão profissional e relatório PDF. **Não fornece diagnóstico automático e não está clinicamente validado. Use somente dados fictícios nesta versão de desenvolvimento.**

## Funcionalidades do núcleo
- Login com sessão segura, administrador e fisioterapeuta; isolamento por clínica.
- Cadastro de pacientes, dashboard real, avaliações e histórico persistido.
- Webcam com skeleton em Web Worker, FPS configurável e upload de foto.
- Captura guiada anterior/posterior/laterais, confirmação de plano e nivelamento.
- MediaPipe real; nenhuma medida de demonstração inventada.
- Medidas de ombros, cabeça, tronco, pelve, base de apoio e joelhos com limitações explícitas.
- Visibilidade técnica, cobertura corporal, recusa de medidas inviáveis.
- Revisões com autoria/data, conclusão profissional, snapshots imutáveis e PDF.
- Auditoria, cadastro de profissionais, regras clínicas pendentes de validação e desativadas.

Também inclui gravação/upload de vídeo, processamento real no servidor, agachamento bilateral/unipodal, elevação de braço, fases experimentais, timeline com skeleton, gráficos D/E, mapa corporal e comparação longitudinal compatível. Veja [métodos e limites dos movimentos](docs/movements.md). Os tipos de avaliação organizam o registro; o protocolo escolhido determina a análise.

## Stack e estrutura
```
frontend/                 Next.js, React, TypeScript
  app/                    Interface clínica
  components/             Captura, pacientes, resultados e revisão
  vision/                 PoseProvider, MediaPipe em Worker, skeleton
  e2e/                    Testes reais de navegador
backend/
  app/core/               Configuração, banco e autenticação
  app/models.py           Entidades relacionais
  app/schemas.py          Contratos e validação
  app/repositories.py     Escopo de acesso e auditoria
  app/services/           Processamento e snapshots
  app/biomechanics/       Geometria pura
  app/clinical/           Motor e regras versionadas
  app/storage.py          StorageProvider local privado
  app/reports.py          PDF
  migrations/             Alembic
  tests/                  API, segurança, validação e matemática
infra/                    Dockerfiles
docs/                     Arquitetura, métodos, segurança e roadmap
compose.yaml              Frontend + backend + worker + PostgreSQL
```

## Opção A — Docker Compose e PostgreSQL
Requisitos: Docker Engine/Desktop com Compose v2, internet na instalação e aproximadamente 4 GB livres. Não depende de serviços pagos. Docker está configurado, mas não foi executado na máquina de desenvolvimento; a validação local utilizou Windows e PostgreSQL.

1. Copie `.env.example` para `.env` na raiz. Substitua `POSTGRES_PASSWORD` por senha aleatória longa. Para a URL de conexão, use caracteres seguros de URL (ex.: hexadecimal), ou percent-encode caracteres especiais.
2. Na raiz execute:
   ```sh
   docker compose up -d db
   docker compose run --rm --build backend python -m alembic upgrade head
   docker compose run --rm backend python -m alembic check
   docker compose up --build -d
   docker compose exec backend python -m app.seed
   ```
   O comando app.seed cria uma clínica vazia e solicita a senha inicial do administrador (mínimo 12 caracteres). O antigo `--demo` foi desativado; demonstração exige o comando explícito descrito em [Ambiente demo](docs/demo-environment.md). E-mail padrão: `admin@biometria.local`; personalize com `--email profissional@exemplo.com`.
3. Abra **http://localhost:3000** e entre com a senha escolhida.

Migrações são executadas explicitamente antes de iniciar API e worker; o startup do backend apenas inicia o Uvicorn, preservando a correção remota. Não execute migrations em cada réplica. Banco e mídia persistem em volumes separados. `docker compose down` para parar; não use `down -v` se quiser preservar dados. Logs: `docker compose logs backend frontend`.

O arquivo Compose restringe a porta web a localhost e não expõe PostgreSQL. Para disponibilizar em rede, configure HTTPS, origins corretas, cookies Secure, proxy com limites de upload e política de segurança; não exponha esta configuração de desenvolvimento diretamente à internet.

## Opção B — execução local
Requisitos: Python 3.12, Node.js 22.18 ou superior e npm. PostgreSQL 17+ recomendado. SQLite pode ser usado para desenvolvimento sem instalar banco.

Na raiz, crie o ambiente Python:
```sh
python -m venv .venv
```
Ative-o: Windows PowerShell ` .\.venv\Scripts\Activate.ps1`; Linux/macOS `source .venv/bin/activate`. Alternativamente invoque o executável Python dentro de `.venv` diretamente.

```sh
pip install -r backend/requirements.txt
cd backend
```
Copie `backend/.env.example` para `backend/.env`. O padrão usa SQLite. Para PostgreSQL, crie banco/usuário e defina:
```dotenv
DATABASE_URL=postgresql+psycopg://usuario:senha@127.0.0.1:5432/biometria
```
Ainda em `backend/`:
```sh
python -m alembic upgrade head
python -m app.seed
python -m app.vision.provider
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```
Em outro terminal com o mesmo ambiente Python ativo, dentro de `backend/`, execute `python -m app.jobs` e mantenha-o aberto. Esse worker é obrigatório para vídeo. Em Linux, instale também as bibliotecas de sistema `libgl1`, `libglib2.0-0` e `libportaudio2` (nomes Debian/Ubuntu).

Em outro terminal, a partir de `frontend/`:
```sh
npm ci
npm run prepare:vision
npm run dev
```
Abra **http://127.0.0.1:3000**. A interface encaminha `/api` para `http://127.0.0.1:8000`; ajuste `BACKEND_URL` no `frontend/.env.local` se necessário. Não coloque segredos em variáveis `NEXT_PUBLIC_*`.

`prepare:vision` baixa o modelo uma vez, verifica SHA-256 contra o manifesto, copia WASM do pacote instalado e compila o worker. Nenhuma imagem clínica é enviada ao fornecedor do modelo. Internet é necessária para instalar pacotes/modelo; a análise funciona localmente após essa etapa.

## Primeiro uso
1. Entre, cadastre um paciente e inicie uma avaliação em câmera ou foto.
2. Selecione a vista, confira iluminação, corpo inteiro e nivelamento.
3. Autorize a câmera para ver landmarks reais. Capture uma imagem ou envie JPEG/PNG/WebP.
4. Confirme o plano e o nivelamento; clique em **Analisar e salvar captura**.
5. Confira medidas e qualidade. Abra os registros para confirmar ou descartar; escreva notas.
6. Registre a conclusão e conclua. Para repetir a vista ou acrescentar outra, retorne à captura antes de concluir.
7. Baixe o PDF. Pelo histórico, reabra a avaliação posteriormente.

O PDF reflete observações **salvas**. A interface impede gerar relatório com alterações locais pendentes; use Salvar observações. Concluir exige revisão de todos os registros e uma conclusão preenchida. Avaliações concluídas ficam imutáveis.

## Câmera e smartphone
Webcam exige `localhost` ou HTTPS e autorização do navegador. Uma URL HTTP por IP de rede não garante acesso à câmera. Câmera traseira é preferida quando disponível; confirme o enquadramento. Tablet é suportado pela interface responsiva. Smartphone exige servir a aplicação por HTTPS acessível ao dispositivo; não existe aplicativo nativo. Gravação de movimento usa MediaRecorder, sem áudio, até 60 segundos; alternativamente envie MP4/WebM até 100 MiB. Autorize a câmera no modo Vídeo, grave, confira as duas confirmações e clique Processar vídeo. Pode sair da tela: acompanhe o job ao reabrir Captura pelo histórico.

## Testes e build
Com o ambiente Python ativo, em `backend/`:
```sh
python -m pytest -q
python -m alembic check
```
Lint do backend: instale `ruff` no ambiente de desenvolvimento e execute `python -m ruff check app tests migrations` (configuração em `backend/ruff.toml`).
Para executar a mesma suíte contra PostgreSQL, defina `TEST_DATABASE_URL` com uma conexão de teste. Cada teste cria um schema aleatório `test_*` e o remove ao terminar; o usuário de teste precisa de permissão para criar schemas. Use um banco dedicado a testes. A CI inclui PostgreSQL 17.
Os testes usam banco temporário e dados sintéticos. Não apontam para pacientes reais. Em `frontend/`:
```sh
npm run typecheck
npm test
npm run lint
npm run build
npm audit
```
Os testes de navegador exigem Chrome, backend/frontend/worker executando em banco dedicado a QA, `E2E_ISOLATED=1` e uma conta fictícia. Configure `E2E_BASE_URL` para esse ambiente; nunca use o banco da clínica. Defina `E2E_PASSWORD`, opcionalmente `E2E_EMAIL`, e `E2E_IMAGE` apontando para foto de teste autorizada. Para webcam/gravação, defina também `E2E_CAMERA_FILE` com um arquivo Y4M autorizado para a câmera de teste do Chrome. Execute `npm run test:e2e`. A inferência utiliza o modelo real; testes de integração ficam explicitamente skipped sem as respectivas variáveis. As mídias de teste não são incluídas no repositório.

## Banco, migrações e arquivos
As migrations criam entidades relacionais de clínica, usuários/profissionais, sessão, pacientes, avaliações, mídia, análise, frames, landmarks, medidas, regras, achados, revisões, relatórios e auditoria. Para alterar esquema: `alembic revision --autogenerate -m descricao`, revisar o arquivo e testar upgrade/downgrade em banco descartável antes de aplicar. Não usar `create_all` no startup.

Não há binários de mídia no PostgreSQL. Os arquivos JPEG normalizados são armazenados em `STORAGE_DIR`; cada registro guarda hash, tamanho, tipo, dimensões, proprietário e avaliação. Não apague diretórios de mídia isoladamente: eles estão referenciados no banco.

Vídeos originais também ficam privados em `STORAGE_DIR`, com hash e metadados técnicos; áudio/metadados de uploads não são removidos nesta versão. Faça backup consistente de banco e diretório de mídia. O modelo do servidor fica em `POSE_MODEL_PATH`, separado das mídias; no Docker é preparado durante o build.

## Documentação
- [Avaliação de prontidão clínica pela internet — não liberado](docs/clinical-readiness.md)
- [Protocolo de validação clínica proposto](docs/clinical-validation-protocol.md)
- [Arquitetura e decisões](docs/architecture.md)
- [Métodos biomecânicos](docs/biomechanics.md)
- [Movimentos, fases e evolução](docs/movements.md)
- [Motor clínico](docs/clinical-engine.md)
- [Privacidade e segurança](docs/privacy-security.md)
- [API](docs/api.md)
- [Próximas entregas](docs/roadmap.md)
- [Evidências e limites da validação](docs/validation.md)

O projeto separa medição objetiva de interpretação profissional. Sem referência científica validada no projeto, nenhum threshold clínico é ativado. As porcentagens de visibility são indicadores técnicos, não confiança diagnóstica nem garantia de acurácia.

## Expansão 2.2 — Protocolos e ROM

Inclui roteiros versionados em sete categorias, etapas com autosave/retomada, capturas vinculadas, revisão e PDF agregado. ROM acrescenta sete movimentos com landmarks reais, câmera e vídeo, pico/série temporal, revisão e histórico. Consulte [Protocolos](docs/protocols.md) e [ROM](docs/rom.md).

Atualização: faça backup do PostgreSQL e armazenamento. No backend execute `python -m alembic upgrade head` e `python -m alembic check`; reinicie API e worker. No frontend execute `npm ci`, `npm run build` e `npm start`. A migration 6d49ba3c72e9 é aditiva e não insere pacientes.

Verificação: `python -m pytest -q` no backend; `npm run typecheck`, `npm test`, `npm run lint` e `npm run build` no frontend. O E2E protocols-rom.spec.ts exige E2E_ISOLATED=1, credenciais e câmera de fixture em banco separado. Nunca execute testes de escrita na clínica.

Os próximos módulos do roadmap não foram implementados nesta rodada. Testes de engenharia não constituem validação clínica; permanecem as restrições de uso e implantação previamente documentadas.

## Atualização de estabilização 2.2.1

Faça backup consistente. Aguarde jobs ativos terminarem, pare API e worker e execute `python -m alembic upgrade head`; a revisão 2a9c071bf630 acrescenta somente o identificador de tentativa do worker. Execute `python -m alembic check`, reinicie API/worker e reconstrua o frontend. Não mantenha workers antigos rodando durante a troca de versão.

Edição de paciente fica no perfil, em Editar paciente. Alterações concorrentes pelo formulário são recusadas por revisão; preserve o texto e reabra antes de reaplicar. Notas e conclusão também usam comparação com o valor originalmente carregado. Protocolos serializam o autosave e preservam a revisão de cada etapa.

Não foram adicionados novos módulos. O ambiente local permanece sem liberação assistencial pela internet, conforme [prontidão clínica](docs/clinical-readiness.md).

## Produção e demonstração — KINUA 2.3.0

KINUA 2.3 — Access, Commercial Administration & Demo Environment.

O bootstrap normal nunca cria pacientes. `Clinic.is_demo` identifica a demonstração, isolada por tenant, com banner permanente, PDFs marcados e exclusão das métricas comerciais. `APP_MODE` não concede acesso. Consulte [criação, reset e armazenamento da demo](docs/demo-environment.md).
