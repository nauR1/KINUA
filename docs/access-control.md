# Controle de acesso e administração comercial — KINUA 2.3.0

## Papéis

- `platform_admin`: administração global/comercial. Não ganha acesso a prontuários por ser global.
- `admin`: administração da própria clínica e operação clínica.
- `physiotherapist`: operação clínica no tenant autorizado.

`platform_admin` só acessa rotas globais/auth apropriadas; o backend bloqueia o uso de privilégios globais para atravessar o domínio clínico.

## Sessões

- senha Argon2;
- sessão aleatória com token opaco;
- apenas SHA-256 do token é persistido;
- cookie HttpOnly, SameSite Strict e Secure em produção;
- duração padrão de 8 horas;
- logout remove a sessão;
- suspensão/revogação administrativa elimina sessões afetadas conforme a ação.

Cinco tentativas inválidas na janela de 15 minutos geram bloqueio temporário. A resposta de credencial inválida é genérica.

## Política de acesso

`backend/app/core/access.py` é a fonte de decisão para login e requisições autenticadas.

Códigos atuais incluem:

- `account_disabled`
- `user_access_expired`
- `clinic_suspended`
- `subscription_expired`
- `subscription_cancelled`
- `access_not_started`

### Herança e overrides

`User.access_starts_at = NULL` significa herdar o início aplicável da clínica. `User.access_expires_at = NULL` significa não impor um vencimento individual adicional.

Para planos comuns, o limite efetivo respeita clínica e usuário. Override individual restringe o usuário; não deve ampliar uma janela clínica já encerrada.

### Lifetime

Para `plan_code=lifetime`:

- a clínica não tem vencimento comercial (`access_expires_at = NULL`);
- uma data antiga/futura de início da clínica não deve transformar automaticamente um usuário novo sem override em `access_not_started`;
- um **início individual explícito** ainda pode bloquear aquele usuário até a data;
- usuário inativo e clínica suspensa continuam bloqueando normalmente.

Essa semântica foi adicionada/corrigida na migration `9e1609260000` e nos testes de acesso.

## UTC

Datas persistidas são timezone-aware e normalizadas em UTC. O browser não é fonte de verdade para “começar agora”. Campo vazio no formulário envia `null`, não uma data automática futura. Inputs `datetime-local` explícitos são convertidos uma vez para UTC, evitando deslocamento duplo.

## Planos

`trial`, `monthly`, `quarterly`, `annual`, `custom`, `lifetime`.

O plano é metadado comercial; estado/datas são aplicados pelo backend. Ainda não há gateway, webhook de cobrança nem renovação automática.

## Limite de usuários

`max_users` limita contas ativas. Reduzir o limite não apaga usuários existentes. Nova ativação/cadastro ativo é recusado quando a capacidade é atingida.

## Bootstrap

Primeiro administrador global:

```sh
cd backend
python -m alembic upgrade head
python -m app.seed --platform-admin --email seu-email@dominio.com
```

Senha mínima: 12 caracteres. `BOOTSTRAP_PASSWORD` pode ser usado temporariamente em automação segura e deve ser removido depois. Conta existente não é promovida silenciosamente.

## Demo

A clínica demo é explicitamente marcada e isolada. Em produção `ALLOW_DEMO_SEED=false`. `DEMO_PASSWORD` vazia no runtime não altera a senha já persistida de uma conta demo existente.

## Pendências

- MFA;
- recuperação de senha self-service;
- política de rotação/expiração de credenciais administrativas;
- SSO para clientes enterprise;
- paginação server-side das telas globais em alta escala;
- gateway financeiro/billing automático.
