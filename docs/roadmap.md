# Evolução após a versão 2

## Implementado — vídeo e agachamento bilateral
- Armazenamento privado de vídeo, limites de duração/codecs e jobs duráveis com estado explícito.
- MediaPipe/OpenCV no worker de processamento; amostragem de FPS e timestamps originais.
- Séries temporais com frames inválidos preservados; filtros documentados e cálculo da velocidade pelo intervalo temporal real.
- Fases de agachamento com histerese e testes de movimentos incompletos; critérios experimentais identificados até validação.
- Flexão sagital D/E apenas com planos adequados; duas vistas para análise frontal e sagital, sem misturar projeções.
- Timeline clicável, gráfico sincronizado, máximos/mínimos/amplitude e frames associados.

## Implementado — recursos da terceira entrega
Agachamento unipodal, elevação de braço, comparação longitudinal apenas entre protocolos/planos compatíveis, imagens lado a lado e mapa corporal. Relatórios com gráficos e comparação absoluta, sem porcentagem de melhora sem fundamento.

## Pesquisa e produção
Validação de confiabilidade contra padrão de referência, calibração, detecção de perspectiva, versionamento de features/modelos, consentimento e governança de dataset, editor controlado de regras validadas, jobs Redis, armazenamento S3, backups e monitoramento. Arquitetura futura para portal do paciente, sensores e 3D.

A implementação de engenharia inclui foto/webcam, vídeo, protocolos adicionais e evolução. As fases são experimentais e os protocolos precisam de validação com movimentos reais e padrão de referência. Docker está configurado, mas sua execução no ambiente alvo permanece pendente. A seção de pesquisa e produção é trabalho futuro explícito.
