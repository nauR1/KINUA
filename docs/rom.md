# KINUA ROM

## Uso e escopo

Em ROM, escolha paciente, movimento e lado. Também é possível entrar pela etapa ROM do protocolo. Confira câmera fixa/nivelada e plano, grave começando e terminando parado ou envie vídeo. Os três pontos usados devem estar visíveis. A prévia exibe ângulo corrente e máximo observado; o vídeo salvo é processado no servidor. Revise o pico, a série temporal e a medida antes de concluir a avaliação.

Sete movimentos: flexão e abdução do ombro, flexão e extensão do cotovelo, flexão do quadril, flexão e extensão do joelho. Somente abdução aceita ambos os lados no plano frontal; demais movimentos usam vista lateral do lado escolhido.

## Fórmulas

ROMEngine recebe landmarks do PoseProvider e corrige proporção da imagem com (x × largura/altura, y). O ângulo entre vetores usa produto escalar normalizado e acos limitado a [-1,1].

| Movimento | Pontos | Fórmula |
|---|---|---|
| Ombro: flexão/abdução | quadril, ombro, cotovelo | ângulo |
| Cotovelo: flexão/extensão | ombro, cotovelo, punho | 180 − ângulo |
| Quadril: flexão | ombro, quadril, joelho | 180 − ângulo |
| Joelho: flexão/extensão | quadril, joelho, tornozelo | 180 − ângulo |

Extensão seleciona o menor ângulo residual; flexão e abdução selecionam o maior. Excursão é máximo menos mínimo observado. Ombro mede braço relativo ao tronco, sem isolar glenoumeral. Quadril usa tronco/coxa, sem orientação pélvica. Ângulos não orientados não distinguem hiperextensão nem movimentos opostos. A confirmação humana de plano e direção é necessária.

## Regras técnicas experimentais

Origem: escolhas de engenharia em app/rom.py, sem referência clínica validada.

- Visibilidade mínima 0,65, herdada do motor biomecânico.
- Brilho médio normalizado mínimo 0,12; comprimento mínimo do segmento 0,0001 na coordenada corrigida.
- Início: três amostras estáveis dentro de 4° seguidas por deslocamento superior a 4° no sentido escolhido.
- Lacuna máxima: menor entre 1100 ms e 2100/FPS. Velocidade somente entre amostras válidas consecutivas com intervalo até 2100/FPS.
- Prévia limitada a aproximadamente 3 inferências/s, uma em andamento. Análise persistida usa FPS selecionado.

Não há faixa clínica de normalidade: threshold_pending_validation. Visibilidade não é acurácia ou probabilidade clínica. Frames inválidos não são interpolados nem preenchidos com zero. Picos entre amostras podem ser perdidos. Esta entrega não adiciona contagem de repetições.

Coordenadas do detector seguem a documentação oficial: https://github.com/google-ai-edge/mediapipe/blob/master/docs/solutions/pose.md . As fórmulas são geometria 2D; não representam goniometria clinicamente validada.

## Histórico e persistência

ROMSession congela fórmula, versão, plano, regras e limitações. ROMMeasurement guarda mínimo, máximo, excursão, pico, frame/instante e confiança, ligado à medida revisável. PoseFrame preserva série e landmarks. Relatórios usam snapshots.

Histórico mostra dados reais e estado de revisão. Gráfico longitudinal usa medidas confirmadas de mesmo movimento, lado, vista, provider, engine e FPS. Mostra variação absoluta, sem percentual de melhora. A comparabilidade clínica ainda depende da técnica de execução.

## Testes

Testes matemáticos cobrem sete movimentos, ângulos conhecidos, três resoluções, espelhamento, oclusão, planos, extensão, lacunas e início. API/worker cobrem persistência, revisão, relatório e isolamento por clínica. E2E usa câmera de fixture e MediaPipe real em banco isolado. Essas verificações não estabelecem validade clínica.
