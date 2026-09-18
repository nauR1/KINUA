# Roadmap técnico — após KINUA 2.3.0

Atualizado em 18/09/2026. Itens já concluídos não permanecem como “futuro”.

## Já entregue/operacional

- foto, webcam e vídeo com MediaPipe;
- worker Python e jobs duráveis;
- Protocolos e ROM;
- revisão profissional, histórico, comparação e PDF;
- administração global/comercial;
- planos, suspensão, expiração e lifetime;
- tenant demo isolado;
- storage S3 privado;
- PostgreSQL persistente;
- backup automático separado do processo PostgreSQL;
- restore drill protegido e último ensaio real documentado;
- isolamento cross-tenant de mídia/PDF;
- CI backend/frontend e migrations;
- bloqueio de crawlers (`robots/noindex`);
- suporte validado a MOV/QuickTime decodificável.

## Prioridade P0/P1 — segurança e operação

1. tornar repositório privado e ativar branch protection na `main`;
2. recuperação de senha com token de uso único, expiração, revogação e auditoria;
3. MFA para `platform_admin` e, idealmente, administradores de clínica;
4. observabilidade: erros, latência, fila, worker, 5xx, disco, backup e health;
5. alertas operacionais e runbooks;
6. formalizar RPO/RTO e retenção de backup/mídia, habilitar pruning e repetir restore drill no head atual;
7. pentest externo autorizado + reteste;
8. load test com cenários de vídeo/ROM concorrentes;
9. mover o cron de backup para serviço repo-sourced dedicado quando o limite de recursos Railway permitir;

## P1 — qualidade mobile

- matriz física iPhone/iPad/Android;
- Safari/Chrome, orientação portrait/landscape;
- câmera traseira/frontal e troca de câmera;
- MOV H.264 e HEVC/H.265;
- vídeos da biblioteca versus gravados no navegador;
- PWA/offline shell apenas onde não comprometer prontuário/consistência;
- mensagens de compatibilidade orientando formato/codec quando necessário.

## P1/P2 — produto clínico

- wizard de calibração/enquadramento;
- score de qualidade técnica da captura (sem chamar de confiança clínica);
- gráficos longitudinais por medida/ROM;
- comparação bilateral e evolução com baseline definido;
- templates de relatório por clínica;
- assinatura/validação do relatório e QR de verificação;
- módulo de prescrição/reabilitação após definição clínica;
- catálogo/versionamento administrativo de protocolos quando houver governança adequada.

## P2 — comercial e enterprise

- onboarding de clínica;
- gateway/billing e webhooks;
- organizações com múltiplas unidades;
- SSO/SAML/OIDC para enterprise;
- feature flags;
- suporte com export sanitizado;
- portal do paciente somente após definir autenticação, consentimento e escopo.

## P2/P3 — escala

- paginação server-side e busca remota;
- presigned/direct upload ao S3 se necessário, mantendo autorização/proveniência;
- broker/fila dedicada se PostgreSQL deixar de atender o throughput;
- réplicas adicionais de backend/worker conforme métricas;
- políticas de lifecycle/storage tier;
- API pública versionada, rate limit por cliente e webhooks;
- estudar padrões de interoperabilidade em saúde apenas quando houver caso de uso concreto.

## Pesquisa/validação

- validação contra referência instrumental;
- ICC/SEM/MDC/Bland–Altman quando aplicáveis;
- impacto de câmera, distância, perspectiva, roupa e oclusão;
- versões do MediaPipe/modelo como variável controlada;
- dataset somente com finalidade/base legal/consentimento e governança definidos;
- investigar 3D/sensores somente após consolidar valor do pipeline 2D.

## Regra de priorização

Não adicionar “IA clínica” ou novos módulos por marketing antes de fechar segurança, observabilidade, dispositivos físicos e validação das medidas já existentes. O roadmap deve ser guiado por risco, evidência de uso e custo operacional.
