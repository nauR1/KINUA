# Protocolo proposto de validação clínica — pendente de aprovação

Responsável indicado: Ruan Rocha. Métodos informados pelo solicitante: **análise de movimento e testes ortopédicos**. Sistema/instrumento quantitativo, procedimentos e calibração ainda não especificados. População, tolerâncias clínicas, desenho amostral e aprovação: **pendentes**. Este documento organiza a coleta futura; não contém resultados clínicos fabricados nem autoriza iniciar atendimento ou estudo.

## Escopo a aprovar

Definir quais medidas terão utilidade clínica pretendida. Validar separadamente foto estática, agachamento bilateral, unipodal e elevação de braço. A conclusão de um protocolo não deve ser extrapolada aos demais. Registrar população, condições de inclusão/exclusão e cenários não cobertos, inclusive dor/limitação funcional, uso de dispositivos auxiliares e necessidade de adaptação do teste.

Para cada medida, definir constructo e unidade: ângulo projetado em 2D, inclinação aparente ou razão normalizada. Não comparar automaticamente uma projeção frontal com flexão sagital ou tratar uma estimativa de quadril como marcador anatômico palpado. Revisar se a medida implementada responde à finalidade clínica pretendida antes de medir sua concordância.

## Referência e captura

Separar a concordância da avaliação funcional feita por Ruan da precisão das medidas em graus/razões e dos eventos temporais. Testes ortopédicos podem contribuir para o contexto clínico, mas não constituem automaticamente uma referência numérica para ângulos ou timestamps. Se a análise de movimento disponível usa um sistema quantitativo, registrar qual é e quais medidas ele produz; se é observacional, definir também uma referência quantitativa apropriada.

Ruan deve selecionar e justificar a referência para cada constructo. Uma proposta para discutir é anotação independente dos mesmos pontos/projeções em imagens padronizadas, acompanhada de referência clínica adequada quando houver equivalência. Um goniômetro não constitui automaticamente referência para todas as projeções produzidas pelo sistema.

Documentar instrumento, identificação, resolução, calibração, método de posicionamento, examinador e sincronização. Em vídeo, associar a medição de referência ao frame/timestamp correspondente. Avaliadores de referência devem avaliar sem consultar inicialmente o resultado automático, quando o desenho permitir, para reduzir influência na comparação.

Padronizar câmera, resolução, distância, altura, inclinação, iluminação, plano, roupa e instruções. Registrar o que foi realmente observado; não converter uma confirmação manual de nivelamento em evidência de que a câmera estava nivelada. Manter versão e SHA do modelo, motor, regras, FPS e parâmetros de captura.

## Repetibilidade e condições difíceis

Predefinir repetições dentro da sessão, entre sessões e entre examinadores. Definir tamanho amostral e distribuição com apoio estatístico segundo precisão pretendida; não usar um número arbitrário de participantes para declarar validade. Repetições da mesma pessoa não são observações independentes.

Planejar análise de variação de câmera, distância/perspectiva, iluminação, roupa, enquadramento, oclusão, movimentos incompletos e mais de uma pessoa. Não expor participantes a movimentos inadequados para produzir casos difíceis; Ruan define a execução segura. Registrar desistências, resultados indisponíveis e eventos adversos, sem excluir retrospectivamente capturas difíceis para melhorar os números.

## Métricas e critérios definidos antes da coleta

Para medidas contínuas, planejar erro absoluto, viés, distribuição do erro, concordância e repetibilidade na unidade original, com intervalos de incerteza apropriados ao desenho. Se usar ICC ou limites de concordância, especificar método, modelo e tratamento de repetições com profissional de estatística. Correlação isolada não será critério de aceitação do projeto.

Para fases, comparar início/máximo/final com anotações temporais de referência, incluindo erro de tempo, ciclos omitidos, falsos ciclos e segmentos incompletos. Para qualidade, medir tanto falhas aceitas quanto capturas utilizáveis recusadas. Declarar limites por medida/protocolo e avaliar desempenho em condições/grupos relevantes sem alegar validade universal.

Campos de tolerância permanecem `threshold_pending_validation`. Não preencher “erro aceitável de X graus”, tamanho amostral, probabilidade de confiança ou taxa mínima sem definição e justificativa de Ruan e dos responsáveis pelo estudo.

## Dados, relatório e decisão

Antes da coleta, definir finalidade, autorização, base legal, responsabilidades, retenção e requisitos éticos aplicáveis. O formulário de coleta usa código de participante, mas as mídias continuam potencialmente identificáveis e precisam de proteção. A coleta não é autorização para treinamento futuro.

Registrar todos os pares e indisponibilidades no modelo CSV em `validation/clinical-observations-template.csv`. Não enviar nomes, contatos ou histórico clínico desnecessário nesse arquivo. Guardar a chave de identificação separadamente sob responsabilidade da clínica. O CSV está vazio de propósito: não existe dataset clínico validado nesta entrega.

Congelar versão e critérios antes da avaliação confirmatória. Se ajustar algoritmo/limiar com os dados de validação, separar dados de desenvolvimento e validação e repetir a avaliação necessária. O relatório final deverá conter método, população, perdas, resultados, limitações, divergências, riscos residuais e decisão assinada pelos responsáveis. Até lá, situação: **não validado para uso assistencial**.
