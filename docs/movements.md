# Análise de movimentos · versão 2

## Captura e execução

Crie uma avaliação em modo Vídeo e escolha agachamento bilateral, agachamento unipodal (lado de apoio obrigatório) ou elevação de braço. Grave pelo navegador ou envie MP4/WebM de até 100 MiB e 60 segundos. O navegador grava sem áudio. Arquivos enviados podem conter áudio/metadados originais; ficam privados e esses dados não são usados na inferência. Para minimizar dados, prefira gravação pela aplicação.

Confirme câmera fixa/nivelada e vista. Comece imóvel por pelo menos um segundo e termine na posição inicial. Aplique a mesma configuração em acompanhamentos. A captura não comprova automaticamente que o paciente executou o protocolo escolhido ou que apoiou somente um pé; essa conferência pertence ao profissional.

A vista frontal permite projeção dos joelhos, deslocamento medial relativo, linha da pelve e inclinação do tronco. **Flexão de joelho exige vista lateral**, e apenas o lado próximo da câmera é medido. Não é possível obter flexão sagital bilateral confiável de uma única vista frontal. Elevação de braço usa quadril–ombro–cotovelo, não mede movimento escapular ou rotação glenoumeral isolada.

## Medidas

`MotionEngine` chama a geometria estática v1 preservada e acrescenta métodos v2:

- Flexão de quadril projetada: 180° menos o ângulo ombro–quadril–joelho, no lado visível da vista lateral.
- Tornozelo/pé: ângulo joelho–tornozelo–ponta do pé. Não é dorsiflexão clínica validada.
- Elevação do braço: ângulo quadril–ombro–cotovelo, no plano visível.
- Inclinação sagital do tronco: direção quadril–ombro em relação à vertical da imagem.
- Deslocamento medial relativo: distância horizontal do joelho à linha quadril–tornozelo na altura do joelho, orientada em direção ao quadril contralateral e dividida pela largura da pelve. Sinal positivo é medial; não classifica valgo patológico.
- Posição vertical da pelve: diferença vertical entre pontos médios de quadris e tornozelos dividida pelo comprimento do tronco. Sinal aumenta durante a descida frontal, sob câmera fixa.

Coordenada X é corrigida pelo aspecto largura/altura antes da geometria. Landmarks abaixo de 0,65 de visibilidade, fora do enquadramento, iluminação abaixo de 0,12 ou plano incompatível produzem `null` com motivo. Esses limites são filtros técnicos de engenharia herdados da v1, não referências clínicas.

Cada frame amostrado persiste valores, landmarks, timestamps, qualidade, fase e derivada temporal. Velocidade = diferença entre amostras / intervalo real em segundos; não é calculada através de lacunas ou intervalos superiores a 2,1/FPS. O resumo guarda média, mínimo, máximo, amplitude, índices dos extremos e contagem de amostras válidas. D/E usa amostras simultaneamente válidas, com convenção direito menos esquerdo. Extremos entre amostras podem ser perdidos.

## Fases experimentais

Regras técnicas `PHASE_RULES` versão 1.0.0, origem: especificação de engenharia deste documento. **Sem validação clínica ou populacional**. Não são usadas para alertas de normalidade.

Sinal do agachamento lateral: flexão do joelho do lado visível. Frontal: posição vertical normalizada da pelve. Elevação de braços: elevação do braço direito em vista frontal bilateral; lado visível em lateral. A interface identifica o sinal usado.

Três amostras consecutivas com variação até metade da histerese estabelecem a linha de base. Histerese angular: 4°; excursão mínima: 10°. Para razão da pelve: histerese 0,02 e excursão mínima 0,05. Esses números foram escolhidos para exercitar uma máquina de estados explicável; precisam de validação antes de uso quantitativo em pacientes. Não representam amplitude funcional adequada.

A máquina identifica inicial → descida/elevação → máximo observado → subida/retorno → final. Exige duas amostras de retorno à linha de base + histerese para fechar um ciclo. Captura interrompida produz ciclo incompleto. Landmark ausente ou intervalo superior a 1.100 ms reinicia a busca da posição estável; não junta movimentos através de lacunas. Sem posição inicial estável ou excursão suficiente, não afirma um ciclo completo. Um vídeo de pessoa imóvel deve produzir zero ciclos.

## Fila, falhas e versionamento

`python -m app.jobs` reivindica um job persistente por vez e executa cada análise em subprocesso com limite de quatro minutos. Progresso é atualizado por amostra; jobs sem atividade por cinco minutos passam a falha recuperável e geram auditoria. Cancelamento impede publicação parcial. Repetição reaproveita o mesmo job apenas quando falhou/foi cancelado; análises bem-sucedidas são imutáveis.

O decodificador lê timestamps de apresentação reais; recusa tempos não monotônicos em vez de supor FPS constante. Metadados incompletos de WebM do MediaRecorder são obtidos por varredura limitada. OpenCV não fornece garantia universal de detectar corrupção no final de todos os contêineres; use formatos compatíveis e confira a duração exibida. Máximo de 7.200 frames decodificados, resolução até 4K e 601 amostras de análise. Inferência redimensiona o maior lado para até 1.280 px.

Provider Python: MediaPipe 0.10.35, Pose Landmarker Lite float16 versão 1, SHA-256 fixo no código. Motor de movimento: 2.0.0. Regras clínicas permanecem desativadas com `threshold_pending_validation`. Mudanças futuras não recalculam registros existentes.

## Evolução e relatórios

Comparação exige mesmo paciente, avaliações distintas, vista, protocolo, lado, versões de provider/motores e FPS de análise. Medidas exigem mesmo método, unidade e estatística. A diferença é B − A; nenhuma porcentagem de melhora é inferida. Câmera/perspectiva, variabilidade natural e erro de medição continuam relevantes mesmo quando os metadados coincidem.

O mapa corporal filtra medidas por região, sem colorir estruturas como doentes. Os registros permitem abrir o instante do máximo observado e confirmar/descartar a medida. PDF de vídeo inclui amostra inicial, até dois máximos de ciclos, skeleton, gráfico do sinal de fase, estatísticas, revisões e conclusão salva.

Referências de implementação: [MediaPipe Pose Landmarker Python](https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker/python), [OpenCV VideoCapture](https://docs.opencv.org/4.x/d8/dfe/classcv_1_1VideoCapture.html). São documentação técnica, não validação das medidas clínicas.
