# KINUA 2.3.0 — documentação atual do sistema

Referência: auditoria de 14/09/2026 (Bahia). Este documento descreve o código e as evidências disponíveis; não representa uma nova verificação do ambiente online.

## Comece por aqui

- Clientes e profissionais: [tutorial de uso](tutorial-clientes.md).
- Instalação e comandos: [README](../README.md).
- Evidências: [auditoria online](final-online-readiness-audit.md) e [matriz de testes](final-online-test-matrix.md).
- Operação: [implantação](deployment.md), [acessos](access-control.md) e [backup e recuperação](backup-recovery.md).

## Finalidade e limites

KINUA organiza avaliações corporais, estima landmarks e calcula medidas geométricas para apoiar o fisioterapeuta. A medição objetiva é separada da interpretação profissional. O sistema não fornece diagnóstico automático; testes de software não validam precisão clínica.

A versão permanece **2.3.0**. Não há liberação para uso assistencial com dados reais com base na auditoria atual. Persistência e recuperação de dados precisam ser comprovadas, e os fluxos online de vídeo e ROM precisam ser corrigidos e retestados.

## Código disponível versus ambiente online

| Área | Implementação | Última evidência online |
| --- | --- | --- |
| Acesso e administração | Sessões, perfis, planos, expiração, suspensão e auditoria | Fluxos com contas sintéticas passaram, com limites descritos na auditoria |
| Pacientes e isolamento | Cadastro, edição e escopo por clínica | Cadastro, histórico e isolamento entre duas clínicas QA passaram |
| Foto | Inferência real no navegador, medidas, revisão e PDF | Fluxo completo com imagem sintética passou |
| Câmera | Skeleton, captura e salvamento | Passou com câmera virtual; hardware físico não validado |
| Protocolos | Catálogo versionado, etapas, autosave, capturas e relatório | Falha de seleção sob latência; correção local ainda não publicada. Etapa ROM bloqueada |
| ROM | Sete movimentos, lado/plano, série temporal, revisão e histórico | Criação passou; processamento falhou |
| Vídeo | Upload/gravação, fila, worker e análise temporal | Jobs terminaram com falha no início; causa ainda não comprovada |
| Demo | Tenant separado, banner, seed/reset e PDF marcado | Testes locais passaram; login demo online não verificado nesta auditoria |
| Relatórios | PDF com revisão e conclusão | Foto passou. Ajustes locais de apresentação ainda não publicados |
| Persistência e backup | Procedimento documentado | Volume efetivo e restauração não comprovados |

O endereço verificado na auditoria foi [KINUA online](https://frontend-production-1acc.up.railway.app/). Localhost aponta para a instalação do próprio computador; dados locais e online não são sincronizados automaticamente.

## Arquitetura

```text
Navegador — Next.js / React / TypeScript
  ├─ câmera/foto → MediaPipe em Web Worker → landmarks
  └─ /api → proxy Next.js → FastAPI
                            ├─ autorização e escopo da clínica
                            ├─ PostgreSQL: registros e rastreabilidade
                            ├─ StorageProvider: mídia privada local ou S3
                            ├─ geometria → achados → revisão profissional
                            └─ fila de vídeo → worker Python / MediaPipe
```

- `frontend/`: interface, proxy, captura, provider de pose e testes de navegador.
- `backend/app/biomechanics/`: cálculos independentes dos componentes visuais.
- `backend/app/clinical/`: regras transparentes e versionadas; referências pendentes não viram diagnóstico.
- `backend/app/services/`: processamento e snapshots de resultados.
- `backend/app/storage.py`: abstração para arquivos fora do banco relacional.
- `backend/migrations/`: histórico Alembic; head esperado `8d402b230000`, incluindo `7c301a230000`.
- `infra/` e `compose.yaml`: execução dos serviços.

Cada análise registra versões dos motores e do provider. A revisão registra autoria e data. Avaliações concluídas são imutáveis; uma nova avaliação registra a evolução sem reescrever resultados anteriores.

## Perfis e dados

| Perfil | Responsabilidade |
| --- | --- |
| Administrador global (`platform_admin`) | Administração comercial e acessos; não recebe acesso automático aos prontuários |
| Administrador da clínica (`admin`) | Operação clínica e gestão de usuários da própria clínica |
| Fisioterapeuta (`physiotherapist`) | Pacientes, avaliações, revisão e relatórios no escopo autorizado |

A demonstração usa clínica identificada como demo, separada dos demais tenants. Não se deve transformar uma clínica real em ambiente de testes. O portal do paciente não está implementado.

Senhas são armazenadas como hash, não como texto. Sessões, bloqueio por tentativas, expiração e autorização atuam no backend. A auditoria verificou cookies Secure, HttpOnly e SameSite Strict no ambiente online e recusas de acesso cruzado. Isso não comprova conformidade integral de segurança ou LGPD.

Não versionar `.env`, credenciais, arquivos `ACESSO*`, bancos QA/SQLite, dumps, backups, mídia ou evidências privadas. Logs e suporte não devem conter senhas, cookies ou prontuários. A conta temporária da auditoria foi desativada após os testes.

## Instalação e verificação técnica

Siga o [README](../README.md) para Docker Compose ou Windows/local. Ele contém requisitos, exemplos de configuração e comandos completos. O Compose está configurado, mas não foi executado na máquina da última auditoria.

Sequência de atualização: backup consistente e verificável; aguardar jobs; parar workers antigos; aplicar migrations uma única vez; verificar esquema; iniciar API e worker compatíveis; reconstruir frontend; testar login e um fluxo sintético. Não executar downgrade ou testes destrutivos no banco da clínica.

No backend, com ambiente e banco corretos:

```sh
python -m alembic current
python -m alembic heads
python -m alembic check
```

Em ambiente exclusivamente de QA:

```sh
python -m pytest -q
python -m ruff check app tests migrations
```

No frontend:

```sh
npm ci
npm run typecheck
npm test
npm run lint
npm run build
```

O E2E depende de backend, frontend, worker, credenciais sintéticas e mídia de teste. Consulte as variáveis do README antes de `npm run test:e2e`. Nunca aponte a suíte de escrita para a clínica real. Um teste ignorado por falta de configuração não equivale a aprovação.

## Resultados existentes e pendências

Na última auditoria, passaram 210 testes SQLite, 210 PostgreSQL, seis testes unitários frontend e 16 E2E locais: **442 testes locais**, sem ignorados. No ambiente online, quatro dos sete E2E passaram e três falharam. Ruff, tipagem, build e verificação de migrations locais passaram. Esses resultados são históricos, não foram reexecutados para esta atualização documental.

Correções de seleção de paciente em Protocolos/ROM e apresentação de PDF estavam somente no código local ao encerrar a auditoria. Não presumir que estão online. A [auditoria completa](final-online-readiness-audit.md) registra os SHAs observados por serviço.

Antes de liberar o ambiente:

1. Identificar a falha do worker com diagnóstico sem dados sensíveis e obter processamento de vídeo/ROM aprovado online.
2. Comprovar volume do PostgreSQL, armazenamento compartilhado privado de mídia e restauração em ambiente isolado.
3. Publicar as correções aprovadas pelo processo de release e conferir versões dos serviços.
4. Repetir os três E2E online que falharam e validar demo com conta própria.
5. Testar câmera física e dispositivos pretendidos; concluir validação clínica e governança de uso com o responsável profissional.

Consulte [validação clínica proposta](clinical-validation-protocol.md), [métodos biomecânicos](biomechanics.md), [regras clínicas](clinical-engine.md), [ROM](rom.md), [protocolos](protocols.md) e [privacidade](privacy-security.md) para detalhes. A existência de um procedimento não significa que ele já foi executado.
