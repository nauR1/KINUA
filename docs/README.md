# Documentação do KINUA

**Fonte canônica de estado atual:** [`estado-atual.md`](estado-atual.md)  
**Última consolidação:** 16/09/2026  
**Versão do produto:** KINUA 2.3.0

Esta pasta contém dois tipos de documento e eles não devem ser confundidos:

1. **Documentação viva** — descreve o código e a produção atuais e deve ser atualizada junto com mudanças relevantes.
2. **Evidência histórica** — auditorias, resultados e notas de release preservam o que era verdadeiro na data em que foram produzidos. Não devem ser reescritos para parecer atuais.

## Documentação viva

- [`estado-atual.md`](estado-atual.md) — visão consolidada do produto, produção, evidências e pendências.
- [`architecture.md`](architecture.md) — arquitetura de aplicação, dados, processamento e infraestrutura.
- [`deployment.md`](deployment.md) — topologia Railway, deploy, migrations e operação.
- [`backup-recovery.md`](backup-recovery.md) — backup diário, restauração e procedimento de desastre.
- [`access-control.md`](access-control.md) — papéis, sessões, planos e regras de acesso.
- [`privacy-security.md`](privacy-security.md) — controles técnicos, riscos e pendências de segurança/LGPD.
- [`api.md`](api.md) — contratos HTTP principais.
- [`protocols.md`](protocols.md) — Assessment Protocols.
- [`rom.md`](rom.md) — KINUA ROM.
- [`movements.md`](movements.md) — análise temporal e movimentos.
- [`biomechanics.md`](biomechanics.md) — métodos geométricos e limitações.
- [`clinical-engine.md`](clinical-engine.md) — separação entre medição e interpretação.
- [`clinical-readiness.md`](clinical-readiness.md) — prontidão técnica versus validação clínica/regulatória.
- [`clinical-validation-protocol.md`](clinical-validation-protocol.md) — proposta de validação clínica.
- [`roadmap.md`](roadmap.md) — próximos incrementos priorizados.
- [`third-party.md`](third-party.md) — dependências, MediaPipe e versões de inferência.
- [`tutorial-clientes.md`](tutorial-clientes.md) — uso da plataforma por clientes/profissionais.

## Evidência histórica

Os arquivos abaixo registram momentos específicos do projeto. Números de testes, SHAs, limitações e resultados neles contidos são **históricos** e podem ter sido superados por versões posteriores:

- `audit-2.2.1.md`, `audit-results.json`, `audit-files.txt`
- `verification-2.2.md`, `validation.md`
- `release-2.3.md`, `release-2.3-results.json`, `release-2.3-files.txt`
- `demo-release.md`, `demo-auth-fix.md`
- `implementation-v2.md`

Ao existir divergência entre um documento histórico e a realidade atual, prevalecem, nesta ordem:

1. código da `main`;
2. configuração/runtime verificados da produção;
3. `estado-atual.md`;
4. demais documentos vivos;
5. documentos históricos.

## Regra de atualização

Uma mudança deve atualizar a documentação no mesmo PR/commit quando alterar qualquer um destes pontos:

- versão de dependência, modelo de visão ou migration head;
- topologia de produção, serviço, bucket, volume, backup ou restore;
- autenticação, sessão, papel, plano ou regra de acesso;
- formato/tamanho de mídia aceito;
- API pública/interna ou contrato de frontend;
- comportamento de protocolos, ROM, PDF ou worker;
- resultado de readiness que deixa de ser pendência;
- limitação clínica, regulatória ou de segurança.

Auditorias antigas não são “corrigidas”; em vez disso, o estado novo é registrado nos documentos vivos ou em uma nova auditoria datada.
