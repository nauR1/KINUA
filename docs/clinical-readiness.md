# Prontidão clínica e operacional — KINUA

**Atualização de estado:** 16/09/2026.  
**Decisão clínica/regulatória atual:** **NÃO considerar validado para decisões clínicas autônomas nem regulatoriamente liberado com base apenas nas evidências de engenharia.**

Este documento separa três questões diferentes: (1) software funciona; (2) produção é recuperável/segura; (3) medidas são clinicamente válidas para a finalidade pretendida. Resolver uma não resolve automaticamente as outras.

## 1. Engenharia/produção — estado atual

Itens que eram bloqueios em auditorias anteriores e foram tecnicamente comprovados:

- ambiente Railway real com frontend/backend/worker;
- HTTPS/cookies Secure e origens explícitas;
- PostgreSQL persistente após restart;
- storage S3 real;
- isolamento entre clínicas para mídia/PDF;
- backup PostgreSQL automático;
- restore drill real em banco descartável;
- worker/MediaPipe funcional em produção;
- CI principal verde;
- proteção anti-indexação (`robots`/`noindex`).

Esses itens não devem mais aparecer como “não comprovados” em documentação corrente.

## 2. Bloqueios ainda reais

| ID | Tema | Estado / condição de encerramento |
|---|---|---|
| CL-01 | Acurácia | comparar medidas com referência clínica/instrumental e critérios pré-definidos |
| CL-02 | Confiabilidade | testar intra/interavaliador, teste-reteste, SEM/MDC/ICC conforme medida |
| CL-03 | Perspectiva/posicionamento | caracterizar erro por distância, plano, câmera, roupa, oclusão e população |
| SEC-01 | Identidade | implementar recuperação segura de senha e avaliar MFA obrigatório |
| SEC-02 | Segurança externa | pentest autorizado e correção/reteste dos achados |
| SEC-03 | Supply chain/repo | tornar repo privado, proteger `main`, manter dependências/modelo versionados |
| OPS-01 | Continuidade | definir RPO/RTO, retenção, alertas e rotina de restore drill |
| OPS-02 | Capacidade | teste de carga, concorrência de worker e limites por tenant |
| OPS-03 | Dispositivos | matriz física iOS/Android, câmera, orientação e codecs incluindo HEVC |
| DATA-01 | Proveniência | decidir/verificar estratégia para landmarks browser versus imagem persistida |
| GOV-01 | LGPD | finalidade, base legal, retenção, titulares, incidentes, contratos e transferência internacional |
| REG-01 | Regulação | avaliar formalmente enquadramento da finalidade de uso e obrigações aplicáveis |

## 3. O que os testes de software demonstram

Eles demonstram contratos, isolamento, persistência, matemática implementada, integração do modelo, estados, UI e regressão. Eles **não demonstram** que um ângulo estimado por câmera tenha erro aceitável em pacientes reais.

No estado atual, a suíte backend contém 218 testes e o CI também executa Alembic e validações do frontend. E2E cobrem fluxos sintéticos. Resultados de auditorias antigas (51, 91, 140, 210 testes etc.) são históricos.

## 4. Protocolo de validação clínica

Usar [`clinical-validation-protocol.md`](clinical-validation-protocol.md) como ponto de partida. Para cada medida/movimento, definir previamente:

- população e critérios de inclusão/exclusão;
- instrumento/referência;
- posição e protocolo de captura;
- número de avaliadores/repetições;
- erro clinicamente aceitável;
- análise estatística (por exemplo ICC, SEM, MDC e Bland–Altman quando apropriado);
- comportamento esperado em falhas/oclusões;
- versão exata do KINUA, MediaPipe e modelo.

Não misturar atualização de algoritmo/modelo durante uma coleta de validação sem reversionamento e análise.

## 5. Segurança/LGPD

A presença de criptografia em trânsito, autenticação, isolamento e backup não fecha conformidade. É necessário documentar agentes de tratamento, finalidade/base legal, ciclo de vida dos dados, solicitações dos titulares, incident response e transferência internacional. O bucket e a infraestrutura estão na região `ams`.

## 6. Regulação

A finalidade declarada envolve medição para avaliação/reabilitação e apoio profissional. O enquadramento regulatório deve ser avaliado formalmente; o texto “não fornece diagnóstico automático” não determina sozinho se o software se enquadra ou não em requisitos de software como dispositivo médico.

## 7. Critério para mudar o status deste documento

Qualquer futura declaração de “validado” deve registrar:

- versão/SHA do software;
- versões do frontend/backend do MediaPipe e hash do modelo;
- ambiente e dispositivos;
- população/amostra;
- método de referência;
- resultados estatísticos;
- limitações e indicação de uso;
- responsável clínico/científico;
- data e evidência arquivada.

Mudança de infraestrutura ou correção de bug, por si só, não altera o status clínico.
