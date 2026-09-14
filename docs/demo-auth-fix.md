# KINUA 2.3.0 — investigação da autenticação demo

## Conclusão e limite da evidência

**Defeito de código reproduzido:** o seed de uma conta existente, executado SEM --reset com uma nova DEMO_PASSWORD, preservava o hash antigo e imprimia a mesma mensagem de sucesso de uma criação/reset. O operador podia concluir que a nova senha estava ativa; o POST com ela retornava 401. A correção elimina esse falso sucesso: a divergência aborta explicitamente sem alterar dados. Conta já existente com a mesma senha continua idempotente.

**A causa específica do incidente online após --reset ainda não foi comprovada.** A sequência obrigatória A→B com reset e criação C passou no código original b97f34c, em PostgreSQL e HTTP real através do proxy Next.js. Portanto, não há evidência de que --reset deixasse o hash antigo nesse código. Não se afirma que o incidente de produção esteja definitivamente resolvido. É necessário conferir usuário/hash/bloqueio no mesmo serviço e banco que atendem o frontend e a saída do seed/reset utilizado online. Não foi executado reset em produção nesta investigação.

## Evidência Railway, somente leitura

Frontend e backend estavam usando b97f34ccf48fff120172d15e50b49043774ee51e. Backend com start command Uvicorn, pre-deploy Alembic e healthcheck /health. As variáveis DATABASE_URL, DEMO_PASSWORD, ALLOW_DEMO_SEED e APP_MODE estão declaradas no backend. O conector OAuth permite consultar nomes, não valores; não foi possível conferir o valor efetivo da senha, o destino do banco ou o BACKEND_URL compilado. Não há acesso SQL/SSH pelo conector utilizado.

Logs HTTP confirmam POST /api/auth/login com 401, incluindo 14/09/2026 21:07:21 UTC. Eles não contêm corpo de autenticação, por isso não identificam qual conta/senha produziu cada 401. Não se deduziu identidade de usuário a partir desses logs.

## Rastreamento do código

- DEMO_PASSWORD é lida do ambiente do processo CLI. Se ausente, há prompt oculto. Agora, se definida vazia, é recusada, sem recorrer silenciosamente ao prompt. Alterar a variável/redeploy não modifica o banco por si só.
- UserCreate e Login aplicam strip de whitespace na entrada e lowercase ao e-mail para busca/gravação. Essa normalização existente foi preservada.
- Senha é armazenada com Argon2, nunca plaintext. Salt permanece aleatório. Não se exige hash textual idêntico, e sim verificação da nova senha e rejeição da antiga.
- --reset remove somente o tenant demo e recria a conta usando a senha recebida. O novo código relê e confere o hash persistido antes do commit; falha cancela a transação.
- Reset já apagava apenas LoginAttempt correspondente aos e-mails dos usuários daquela demo; regressão comprova que o bloqueio de usuário comum permanece.
- POST /auth/login retorna 401 exclusivamente para usuário ausente ou senha inválida. Cinco falhas na janela de 15 minutos produzem 429. Restrições de is_active, clínica e expiração são aplicadas após conferir senha e produzem 403. /auth/me pode produzir 401 por sessão; é outro endpoint.
- O frontend envia os campos do formulário sem transformação; a regra Next.js reescreve /api/:path* para BACKEND_URL/:path*. Nenhuma lógica especial para e-mail demo.
- Não foram alterados login, verificação Argon2, política de acesso, models, proxy, fórmulas, regras clínicas, protocolos ou ROM.

## Diagnóstico não destrutivo online

Após esta versão estar disponível no backend, executar no shell do MESMO serviço/ambiente usado pelo frontend:

```sh
python -m app.demo_seed --email demo@kinua.app --verify-only
python -m app.demo_seed --email demo2026@kinua.app --verify-only
```

Usa DEMO_PASSWORD daquele processo ou prompt oculto. Retorna somente status, booleans, origem da senha, tipo de banco e IDs Railway, sem senha/hash/URL do banco. Não faz POST, não cria sessão, não altera tentativas, usuários ou dados. Não exige habilitar seed para leitura. statuses: user_not_found, not_demo, password_mismatch, locked, credentials_valid ou código de acesso restrito. Saída 0 apenas para credentials_valid.

Esse resultado distingue causas sem outro reset cego. Se credentials_valid nesse processo e o frontend ainda retorna 401, conferir diferença de senha digitada e destino/backend/banco do proxy. Não atribuir automaticamente a falha a assinatura ou is_demo.

## POST real antes/depois em QA PostgreSQL

Banco PostgreSQL dedicado e descartável, credenciais aleatórias externas ao repositório. API Uvicorn em localhost e frontend Next.js compilado com BACKEND_URL dessa API. Requisições HTTP POST /api/auth/login, não somente TestClient.

| Passo | Antes | Depois |
|---|---:|---:|
| Criar demo com A e autenticar A | 200 | 200 |
| Seed normal com B em conta existente | CLI 0 enganoso | CLI 1 explícito |
| Autenticar B sem reset (hash A preservado) | 401 | 401, comportamento esperado |
| --reset com B; autenticar A | 401 | 401 |
| Autenticar B após reset | 200 | 200 |
| Criar outro e-mail com C e autenticar | 200 | 200 |
| Conta comum | 200 | 200 |
| platform_admin | 200 | 200 |

Novo E2E também executa login pelo formulário depois da troca, confirma dashboard e banner demo. Nenhuma credencial de QA foi enviada à produção.

## Arquivos da correção

- backend/app/demo_seed.py — validação explícita de senha de conta existente, conferência do hash gravado, env vazio recusado e diagnóstico somente de leitura.
- backend/tests/test_demo_auth.py — sete regressões, executadas também no PostgreSQL.
- frontend/e2e/demo-auth.spec.ts — fluxo CLI e login real através do frontend em PostgreSQL.
- docs/demo-environment.md — comportamento e diagnóstico documentados.
- docs/demo-auth-fix.md — este relatório.

## Validação final

- Backend SQLite completo: 207 testes passaram.
- Backend PostgreSQL completo: 207 testes passaram.
- Frontend unitário: 6 testes passaram; TypeScript, Prettier e build Next.js passaram.
- E2E anterior: 13 passaram em QA; o novo teste PostgreSQL foi executado separadamente e passou (14 fluxos aprovados no conjunto).
- Ruff em app/tests/migrations: passou.
- Alembic em PostgreSQL descartável: upgrade/check/downgrade/upgrade/check passou.
- Diagnóstico --verify-only no PostgreSQL QA retornou credentials_valid sem senha/hash na saída.
- Avisos de depreciação Starlette/httpx/AnyIO e codec OpenCV não causaram falhas.

A versão permanece 2.3.0; nenhuma migration nova é necessária. A cadeia continua incluindo 7c301a230000 e 8d402b230000. Nenhuma alteração clínica ou de infraestrutura online foi feita. Credenciais, banco QA, logs e evidências privadas estão fora do Git.
