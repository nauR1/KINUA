# KINUA 2.3 — Access & Commercial Administration

## Roles e separação
platform_admin acessa somente /platform/* e /auth/*. Mesmo quando vinculado a uma clínica por compatibilidade relacional, não recebe acesso aos seus pacientes, relatórios, mídia ou endpoints clínicos.
admin administra usuários da própria clínica em /admin/users; physiotherapist usa as funcionalidades clínicas. Ambos dependem do acesso da clínica.
Somente platform_admin cria/promove outro platform_admin. Desativar ou rebaixar o último global ativo retorna 409; mudanças globais são serializadas por locks das contas globais no PostgreSQL. O seed explícito cria uma nova conta; nunca promove uma conta existente nem troca sua senha.

## Política UTC
app/core/access.py calcula uma única decisão para login, requisição autenticada e painéis. now >= vencimento bloqueia. Não há cron necessário. Início futuro também bloqueia (access_not_started).
Conta global ignora a assinatura e overrides temporais, mas não is_active=false.
Conta clínica exige usuário ativo, clínica ativa, status trial/active, início alcançado e ambos os vencimentos não alcançados. NULL remove o respectivo limite. Override individual pode restringir, nunca ampliar o limite da clínica.
Expiração é calculada: o campo subscription_status não precisa ser alterado automaticamente para a data produzir bloqueio.

403 contém detail com code, plan, expires_at (limite efetivo) e days_remaining. Códigos: account_disabled, user_access_expired, clinic_suspended, subscription_expired, subscription_cancelled, access_not_started.
401 significa sessão ausente/revogada/expirada; após revogação não guardamos o usuário em cookie recuperável. O login seguinte, após senha correta, informa o motivo comercial.
Suspender usuário revoga todas as suas sessões. Suspender/cancelar clínica revoga sessões clínicas; não desabilita implicitamente administradores globais.
A interface remove estado clínico quando recebe bloqueio e consulta /auth/me a cada 15 s enquanto aberta. A API bloqueia cada nova requisição imediatamente; uma resposta já autorizada/em andamento não pode ser recolhida.

## Assinaturas
Planos trial, monthly, quarterly, annual, custom, lifetime. O plano é descritivo: datas/status são explícitos.
Teste 7 dias redefine início/agora e vencimento/agora+7. Extensão soma à maior data entre agora e vencimento vigente, restaura active/is_active e remove suspensão. Não elimina override individual vencido nem início futuro configurado; ajustar esses campos separadamente.
Acesso ilimitado remove vencimento/início e ativa lifetime na UI.
max_users limita contas ativas cadastradas/reativadas; contas expiradas ainda ativas ocupam vaga. Reduzir limite não apaga contas existentes; novas ativações são recusadas até regularizar.
Clinic contém provider, external_subscription_id, external_customer_id, period_start e period_end para integração futura. Não há gateway, cobrança, webhook ou renovação automática.

## Auditoria e privacidade
Ações globais platform.* não incluem prontuários. Alterações feitas pelo admin de clínica usam clinic.* e permanecem em seu escopo. Nenhuma senha/hash é registrada.
Eventos de expiração são registrados ao definir estado/data vencida administrativamente. A passagem natural do tempo é calculada no acesso, sem evento agendado.
Endpoints globais retornam campos explícitos de identificação comercial, sem relacionamentos clínicos. Não há exclusão física de usuários/clínicas nesta entrega.

## Primeiro administrador global
No diretório backend, com DATABASE_URL e demais variáveis corretas:
```sh
python -m alembic upgrade head
python -m app.seed --platform-admin --email seu-email@dominio.com
```
Digite uma senha exclusiva com pelo menos 12 caracteres no prompt. Automação pode fornecer BOOTSTRAP_PASSWORD temporariamente em secret do ambiente; remova-o após executar.
Se o e-mail já existir, nada será promovido ou alterado. Use outra conta para o bootstrap e depois gerencie permissões pelo painel global.
O seed não é executado automaticamente no startup e --platform-admin não pode ser combinado com --demo.

## Limitações
Não há MFA, recuperação de senha self-service, gateway financeiro ou validação clínica nova. A API comercial ainda retorna listas completas; escalar paginação antes de milhares de contas.
A proteção de concorrência exige PostgreSQL para múltiplas instâncias; SQLite é desenvolvimento local de um processo.
