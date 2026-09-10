# Regras clínicas e revisão

O `BiomechanicsEngine` produz medidas; `AttentionEngine` cria registros informativos para revisão. Nenhuma medida isolada é classificada como lesão, síndrome, alteração clínica ou diagnóstico.

`app/clinical/rules.json` contém versão, identificação, categoria, estado de validação, origem e threshold. A regra experimental inicial está desativada com `threshold_pending_validation`, referência nula e threshold nulo. O executor falha de forma conservadora: regras sem validação, origem ou valor não geram associação, mesmo que alguém altere somente `enabled`.

Há uma cópia das definições em `clinical_rules` para rastreabilidade inicial. Nesta versão, a fonte executável é o arquivo versionado. Não existe editor clínico na interface; a página de configurações é informativa. Não editar o banco esperando alterar o motor. Novas regras precisam de revisão clínica, testes e nova versão do motor; sincronização versionada das regras no banco é necessária antes de um editor administrativo futuro.

Estados de revisão: `detected`, `needs_review`, `professional_confirmed`, `professional_rejected`. Registros informativos começam em `needs_review`. Confirmar significa aceitar o registro da medida, não um diagnóstico. Cada mudança acrescenta uma revisão com profissional, nota e data; registros antigos são preservados.

Para concluir uma avaliação é obrigatório haver medidas revisadas, nenhuma revisão pendente e conclusão textual do profissional. Avaliações concluídas não aceitam edição, captura ou alteração de revisão. Um acompanhamento cria outra avaliação. Snapshots armazenam as versões de pose, biomecânica e regras.

Possíveis fatores e testes complementares somente serão expostos quando houver protocolo e regras validados. Os fatores experimentais do arquivo não são apresentados como associações clínicas ativas.
