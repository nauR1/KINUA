# Medição biomecânica 2D

## Contrato e normalização
O provider retorna nome anatômico, X/Y normalizados, Z opcional e visibility. O backend aceita nomes canônicos únicos, números finitos e visibility entre 0 e 1. Antes da geometria, transforma `(x,y)` em `(x × largura/altura,y)`. Isso corrige a diferença de escala entre os eixos; não recupera perspectiva ou profundidade. Z é preservado, nunca utilizado como centímetro.

## Medidas implementadas
| Medida | Método | Plano |
|---|---|---|
| Inclinação aparente dos ombros | atan2(abs(Δy), abs(Δx)) | Anterior/posterior |
| Obliquidade aparente da pelve | mesma fórmula entre quadris | Anterior/posterior |
| Inclinação aparente da cabeça | mesma fórmula entre orelhas | Anterior/posterior |
| Inclinação frontal do tronco | desvio da vertical entre centros dos ombros e quadris | Anterior/posterior |
| Base de apoio relativa | distância entre tornozelos / distância entre quadris | Anterior/posterior |
| Ângulo projetado de joelho D/E | acos do produto escalar dos segmentos quadril–joelho e tornozelo–joelho | Anterior/posterior |
| Flexão aparente do joelho | 180° menos o ângulo de três pontos | Lateral do lado correspondente |

Inclinações são módulos: não identificam automaticamente qual lado está elevado. O ângulo frontal projetado NÃO identifica varo/valgo, torsão, lesão ou alinhamento ósseo. Landmarks de quadril não substituem pontos anatômicos palpados. Anteriorização da cabeça não foi implementada: faltam calibração e protocolo adequado.

## Critérios técnicos (não clínicos)
- Visibility mínima: 0,65, decisão de engenharia conservadora e versionada em `engine.py`.
- Iluminação: luminância média abaixo de 0,12 na escala 0–1 bloqueia medidas. Heurística não validada; não detecta todo contraluz.
- Pontos utilizados precisam estar dentro do enquadramento. Segmentos nulos bloqueiam o cálculo.
- Plano e nivelamento exigem confirmação humana. Não há inferência automática de inclinação da câmera.
- Coordenadas perto das bordas (5% horizontal, 2% vertical) geram orientação de enquadramento; não estimam distância em centímetros.
- Critérios não determinam normalidade clínica. Alterações exigem incremento da versão e testes.

## Qualidade e confiança
Cada medida usa a menor visibility entre seus landmarks. A captura mostra a média dos pontos visíveis e a cobertura dos pontos essenciais separadamente. **Esse indicador não é probabilidade de precisão clínica.** Não combinamos arbitrariamente iluminação e visibility em uma porcentagem clínica. Estabilidade temporal aparece como não avaliada para captura única. Uma medida impossível tem `value=null` e motivo explícito, nunca zero.

## Validação
Testes cobrem 45°/90°/180°, invariância da escala, correção de proporção, oclusão, plano, iluminação, segmentos nulos e pontos inválidos. Isso comprova implementação matemática; validade e reprodutibilidade clínicas exigem estudos com padrão de referência, populações e protocolos definidos.

Referência técnica do provider: https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker/web_js
