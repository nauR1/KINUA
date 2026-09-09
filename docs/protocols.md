# KINUA Assessment Protocols

## Decisão de arquitetura e escopo

A avaliação existente é preservada. Um roteiro associa `AssessmentProtocol` à avaliação principal; capturas de postura, movimentos já existentes e ROM são avaliações filhas, ligadas a etapas. Isso permite reaproveitar mídia, fila, resultados, histórico e revisão sem alterar análises antigas.

`ProtocolCategory`, `Protocol`, `ProtocolVersion` e `ProtocolStep` armazenam o catálogo. Cada execução guarda uma cópia da definição e versão; alterações futuras no catálogo não reescrevem execuções existentes. Não há editor de protocolos nesta rodada.

Etapas têm estado, datas, resultado, observação, profissional e revisão numérica para impedir sobrescrita silenciosa por abas concorrentes. A interface salva rascunhos automaticamente e oferece salvamento explícito. Pular exige justificativa e permissão na definição. Concluir captura exige análise real. A conclusão do roteiro exige revisão e conclusão das avaliações filhas vinculadas.

Categorias iniciais: corpo inteiro, ombro, coluna, quadril, joelho, tornozelo e esportivo. A categoria esportiva reaproveita avaliações existentes; não implementa KINUA Sport. O roteiro de joelho preserva as 12 etapas do briefing. Mapa da dor e step-down estão indisponíveis nesta rodada e só admitem registro de justificativa de salto. Anamnese e testes manuais são registros textuais do profissional, não módulos de anamnese estruturada ou testes automatizados novos.

## Ordem de implementação

1. Modelos, catálogo versionado e migration aditiva.
2. API com escopo por clínica, estados e concorrência.
3. Roteiro guiado com retomada e avaliações filhas.
4. ROM, integração à fila, revisão, histórico e relatório.
5. Testes matemáticos, API, migrations em banco temporário, regressão e interface.

## Riscos controlados

- Confundir observação livre com análise automatizada: etapas textuais têm origem profissional explícita.
- Perder dados ao navegar: salvar antes de avançar, avisar erro e manter rascunho.
- Alterar histórico por atualização de catálogo: snapshot em cada execução.
- Misturar clínicas ou pacientes: todo vínculo é criado no servidor a partir da avaliação autorizada.
- Confundir ROM projetado com goniometria clínica: planos, fórmulas e limitações documentados em `rom.md`.

## Operação e atualização

Abra Protocolos, selecione paciente e categoria e inicie. Registre ou capture cada etapa; alterações textuais têm autosave e salvamento explícito. Retome em Protocolos em andamento ou no histórico. Pular exige permissão e justificativa. Avaliações filhas devem ser concluídas antes do protocolo.

Cada etapa de captura vincula uma avaliação filha. A etapa ROM oferece um movimento/lado por execução; medições adicionais ficam disponíveis no módulo ROM independente. Comparação no roteiro recebe observação profissional; mapa da dor e step-down estão indisponíveis nesta entrega.

A migration 6d49ba3c72e9 acrescenta oito tabelas e sete definições, sem pacientes demo. Faça backup; no backend execute `python -m alembic upgrade head` e `python -m alembic check`. Downgrade elimina dados dos novos módulos e exige plano de recuperação.

Novas definições devem usar nova ProtocolVersion e seus ProtocolStep em migration, preservando versões em uso. migrations/data/protocols_v1.json é a cópia imutável do catálogo inicial; app/protocols/catalog_v1.json documenta sua origem.
