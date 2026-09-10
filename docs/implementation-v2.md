# Plano de finalização funcional

1. Manter snapshots antigos e aplicar migration aditiva para protocolo, metadados de mídia, séries e jobs duráveis.
2. Upload e gravação de vídeo até 60 s / 100 MB; aceitar MP4/WebM decodificáveis. Worker Python separado: OpenCV → PoseProvider MediaPipe → geometria → séries → resumos → revisão. Sem LLM e sem thresholds clínicos.
3. Agachamento bilateral, unipodal (lado declarado) e elevação de braço por protocolo. Medidas dependem do plano: frontal não vira flexão sagital e um vídeo lateral não estima simetria de flexão D/E.
4. Fases experimentais, gaps preservados, timestamps, picos, amplitude, velocidade e timeline sincronizada. Repetições incompletas não são consideradas completas.
5. Comparação longitudinal estritamente compatível, mapa de regiões para revisão, relatório com gráficos e frames.
6. Testes matemáticos, API, jobs, migrations e navegador com inferência real. Atualizar operação local/Compose, documentação e pacote.

Limites de produção permanecem explícitos: não há validação clínica/regulatória automática nem autorização para ativar limiares científicos inexistentes. Nenhuma alteração de resultado antigo é permitida.
