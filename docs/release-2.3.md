# KINUA 2.3 — Access & Commercial Administration
Entrega de engenharia: 14/09/2026. Base c17eddb (2.2.1).

## Resultado
Administração comercial integrada, com autenticação e isolamento verificados. Nenhum módulo clínico novo nem alteração de fórmulas biomecânicas. Protocolos, ROM, câmera, foto, vídeo, worker, revisão, histórico e PDF continuaram funcionando na regressão.
A instalação local foi atualizada e as contas clínicas existentes conservaram acesso ilimitado. Um novo administrador global foi criado por bootstrap explícito em clínica administrativa separada; não houve promoção automática de contas existentes.

## 1. Arquivos alterados
Lista completa em [release-2.3-files.txt](release-2.3-files.txt).
- app/core/access.py: política UTC; core/security.py e main.py: aplicação em login/requisições.
- app/api_admin.py: DTOs validados, endpoints comerciais, escopo, locks, capacidade e auditoria.
- models.py e migration: campos aditivos.
- storage.py: factory, operações com staging privado e S3; api_video/jobs/reports/services.analysis usam o mesmo provider.
- seed.py: bootstrap explícito.
- PlatformAdmin, AccessBlocked, SettingsView, page, api e CSS: telas e tratamento de bloqueio.
- requirements, env examples, compose e Dockerfiles: configuração.
- test_access_admin.py e e2e/access.spec.ts: regressão nova.
- docs/access-control.md, docs/deployment.md, README e este relatório.

## 2. Migration
7c301a230000, filha de 2a9c071bf630. Acrescenta controle de clínica/usuário, integração financeira futura e changes JSON no audit existente. Não altera assessment_media/storage_key.
Existentes recebem is_active=true, status active, expiração NULL e plano custom. Timestamps anteriores inexistentes são inicializados no momento da migration; não representam data histórica comprovada.
PostgreSQL: upgrade/check/downgrade/upgrade/check em banco descartável PASS.
SQLite preenchido: a primeira tentativa encontrou limitação de DEFAULT CURRENT_TIMESTAMP em ALTER TABLE. Foi corrigida com batch recreation Alembic; registros do QA preservados e check passou.
Banco local: cópia PostgreSQL anterior, nenhuma contagem de pacientes/avaliações/análises/usuários/clínicas mudou durante a migration. Bootstrap global posterior adicionou intencionalmente uma conta e clínica administrativa. Nenhum paciente fictício de teste foi inserido no banco clínico local.

## 3. Endpoints
| Método | Rota | Autorização |
|---|---|---|
| GET | /platform/dashboard | platform_admin |
| GET, POST | /platform/clinics | platform_admin |
| GET, PATCH | /platform/clinics/{id} | platform_admin |
| POST | /platform/clinics/{id}/extend | platform_admin |
| GET, POST | /platform/users | platform_admin |
| PATCH | /platform/users/{id} | platform_admin |
| GET | /platform/audit | platform_admin |
| GET, POST | /admin/users | admin da própria clínica |
| PATCH | /admin/users/{id} | admin da própria clínica |

Contratos: schemas da API/OpenAPI em /docs e [controle de acesso](access-control.md). Filtros q, clinic_id e status em usuários. Timestamps de escrita exigem timezone; nulos somente nos campos opcionais. Endpoints clínicos existentes continuam protegidos por clínica.

## 4. Telas
Painel global com Visão geral, Clínicas, Usuários e acessos e Auditoria. Indicadores, busca/filtros, badges, edição, trial/extensões/data personalizada/ilimitado, confirmação de suspensão, feedback e estados vazios.
Equipe da clínica usa o mesmo componente com rotas e permissões restritas.
Tela específica de acesso expirado/suspenso/cancelado/início futuro remove componentes clínicos. API inválida gera 401; acesso comercial bloqueado gera 403 estruturado. A API verifica cada requisição e a tela aberta faz verificação periódica a cada 15 segundos.

## 5. Regras de autorização
Global não acessa prontuário de nenhuma clínica, inclusive a que consta em sua FK administrativa. Admin de clínica não acessa /platform, não altera assinatura nem cria/promove global. Physiotherapist não administra usuários.
Suspensão revoga sessões; expiração bloqueia sem cron e sem esperar o vencimento da sessão. Papel atualizado é consultado no servidor, nunca confiado ao frontend.
Último global ativo não pode ser suspenso ou rebaixado pela API. Locks protegem concorrência no PostgreSQL. Auditoria global não aparece na auditoria clínica, mesmo se contas compartilharem clinic_id.

## 6. Modelo de assinatura
Seis planos e cinco estados, limite de usuários ativos, início/vencimento UTC, override individual restritivo e NULL sem limite. Global ignora assinatura e expiração individual, mas pode ser desativado quando houver outro global ativo.
Campos provider/external_subscription_id/external_customer_id/period_start/period_end preparam integração futura. Sem gateway, cobrança ou webhook nesta entrega.
Extensões retomam clínica suspensa/expirada; override individual continua independente. Evento de expiração administrativa é auditado; o vencimento natural é calculado, sem cron/evento agendado.

## 7. Testes e execução
| Verificação final | Aprovados | Falhas | Skips |
|---|---:|---:|---:|
| Backend SQLite | 178 | 0 | 0 |
| Backend PostgreSQL | 178 | 0 | 0 |
| Frontend unitário | 6 | 0 | 0 |
| Navegador E2E | 12 | 0 | 0 |

São os mesmos 178 casos backend em dois bancos. Os 140 casos anteriores foram mantidos, com 38 novos. Dois avisos de depreciação FastAPI/Starlette permanecem.
Build de produção local e no checkout QA, TypeScript, Ruff, Prettier e pip check: PASS.
S3 offline: put/get/delete, integridade, chave inválida, arquivo ausente, factory compartilhada, limpeza de temporário, upload real de vídeo, leitura autenticada, worker e geração PDF: PASS.
Fluxo E2E administrativo usa UI e requisições autenticadas reais: bootstrap global, login, clínica, trial, admin clínico, profissional, paciente fictício/avaliação, suspensão/bloqueio, reativação, vencimento/tela, +30 dias/restauração e audit. Executado somente no QA.
As tentativas iniciais do E2E revelaram seletor inadequado de select e login repetido com sessão restaurada; a automação foi corrigida sem remover verificações. A criação de usuário passou a aguardar a resposta 201 explicitamente para evitar corrida com a listagem sob carga de testes.
Screenshots do painel global e bloqueio foram inspecionados; regressão desktop/tablet e resoluções clínicas passou. Login e consultas dos dois papéis foram repetidos após atualizar a instalação local.

## 8. Limitações / NÃO VALIDADO
- Deploy real Railway, bucket real e execução Docker: NÃO VALIDADO. Nenhuma credencial/conta de nuvem foi usada.
- S3 exige bucket privado e cópia das mídias existentes antes de mudar o backend; não há transferência automática. Temporários podem sobreviver a kill abrupto até reciclar instância.
- Não há MFA, recuperação de senha self-service, gateway ou renovação automática.
- Listagens comerciais ainda sem paginação; não houve ensaio de milhares de clínicas ou carga concorrente de produção.
- Sessões revogadas retornam 401 sem reidentificar o usuário; o próximo login válido informa o motivo comercial.
- Requisições já autorizadas/em andamento e dados previamente visualizados não podem ser recolhidos. Jobs aceitos antes de suspensão não são automaticamente cancelados.
- SQLite é desenvolvimento; concorrência de múltiplas instâncias requer PostgreSQL.
- Dispositivos físicos, pentest externo, restauração operacional cloud, validação clínica e aprovação regulatória: NÃO VALIDADO. Alertas clínicos originais mantidos.

## 9. Railway
Instruções exatas de serviços, Dockerfiles, variáveis, rede privada, domínio, portas, migrations, storage e backup estão em [deployment.md](deployment.md), com referências oficiais. Aplicá-las na conta e validar os itens operacionais antes de uso externo.

## 10. Bootstrap
[access-control.md](access-control.md) descreve o processo. No backend:
```sh
python -m app.seed --platform-admin --email seu-email@dominio.com
```
A senha é solicitada sem eco. Não promove usuário existente nem troca sua senha. A credencial criada para esta instalação local está em outputs/ACESSO-PLATAFORMA.md, fora do repositório/ZIP. O login clínico anterior permanece separado.
