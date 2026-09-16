# Análise de movimentos — KINUA 2.3.0

## Captura e execução

Crie uma avaliação em modo Vídeo e escolha o protocolo/movimento disponível. Grave pelo navegador ou envie **MP4, WebM ou MOV/QuickTime** de até 100 MiB e 60 segundos. O arquivo só é aceito quando assinatura/conteúdo e decoder são compatíveis; a extensão isolada não basta.

A gravação do navegador não solicita áudio. Uploads da biblioteca podem conter áudio/metadados originais; ficam privados e esses dados não são usados na inferência. Para minimizar dados, prefira a gravação pela aplicação quando ela atender ao caso de uso.

Compatibilidade MOV/QuickTime foi validada no pipeline de engenharia. Isso não garante todos os codecs de iPhone: HEVC/H.265 precisa de ensaio físico e pode exigir orientação ao usuário para gravar/exportar em formato mais compatível.

Confirme câmera fixa/nivelada, vista e plano. Comece imóvel por pelo menos um segundo e termine na posição inicial. Use configuração semelhante em acompanhamentos. A captura não prova sozinha que o paciente executou o protocolo corretamente; essa conferência pertence ao profissional.

## Medidas e limitações

`MotionEngine` reutiliza a geometria estática e acrescenta séries temporais. Entre as medidas atuais estão flexão projetada de quadril/joelho, ângulo joelho–tornozelo–pé, elevação de braço, inclinação do tronco, deslocamento medial relativo e posição vertical normalizada da pelve, conforme protocolo/vista.

Coordenadas são corrigidas pelo aspecto da imagem antes da geometria. Landmarks abaixo dos filtros técnicos, fora de enquadramento, com iluminação insuficiente ou plano incompatível produzem valor indisponível com motivo. Esses filtros são de engenharia, não referências clínicas.

Cada frame amostrado pode persistir landmarks, timestamp, qualidade, fase e medidas. Velocidade usa intervalo temporal real; não é interpolada através de lacunas longas. Resumos guardam estatísticas e extremos observados nas amostras, portanto picos entre frames podem ser perdidos.

## Fases experimentais

Regras de fase permanecem técnicas/experimentais e não representam normalidade clínica. O sistema exige condições de estabilidade/excursão para reconhecer ciclos; movimento incompleto não deve virar ciclo completo artificialmente.

## Fila e resiliência

`python -m app.jobs` reivindica jobs persistidos. Cada tentativa possui `run_token`; publicação, heartbeat e falha tardia são condicionados à tentativa corrente. Cancelamento/retry não deve permitir que um worker antigo publique resultado sobre uma tentativa nova.

O decodificador utiliza timestamps do arquivo e recusa sequências inválidas em vez de assumir FPS constante. Processamento ocorre em subprocesso com limites de duração/frames/resolução.

## Versionamento

- MediaPipe Python: 0.10.35.
- Modelo: Pose Landmarker Lite float16 v1.
- SHA-256 do modelo: `59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a`.
- Runtime browser: `@mediapipe/tasks-vision 0.10.32`.
- Motor de movimento: 2.0.0.

Mudanças futuras de modelo/provider/motor não devem recalcular silenciosamente registros existentes e devem passar por regressão/versionamento.

## Evolução e relatórios

Comparações exigem compatibilidade de paciente, protocolo, lado/plano e versões relevantes. Diferenças são apresentadas como diferenças observadas; o sistema não deve inferir “melhora percentual” sem fundamento clínico.

O mapa corporal é uma forma de navegação/agrupamento, não um diagnóstico. Revisões e conclusão permanecem responsabilidade profissional.

## Validação

A matemática implementada e o pipeline são testados; isso não valida precisão clínica em movimentos reais. Antes de uso quantitativo para decisão clínica, caracterizar erro, repetibilidade e influência de câmera/perspectiva/oclusão contra referência apropriada.
