# Validação da entrega — 09/09/2026

## Evidências executadas
| Verificação | Resultado |
|---|---|
| Pytest: API, autenticação, escopo de clínica, revisão, PDFs, matemática, vídeo, fila, comparação, validação e armazenamento | 44 testes passaram em SQLite e PostgreSQL |
| Frontend TypeScript | Sem erros |
| Testes de contrato frontend | 2 testes passaram |
| Build de produção Next.js 16.3.4 | Passou |
| Navegador Chrome: login → cadastro → foto → inferência real → medidas → revisão → conclusão → PDF → histórico | Passou |
| Navegador Chrome: câmera de teste → inferência real → skeleton → captura → medidas persistidas | Passou |
| Navegador Chrome: MediaRecorder → WebM → worker real MediaPipe → PostgreSQL → timeline/skeleton → PDF/histórico | Passou |
| Total da suíte de navegador | 4 testes passaram |
| Verificação adicional de navegador: comparação compatível, imagens lado a lado e download de PDF de evolução | Passou |
| Login em viewport 390 × 844 | Passou, sem overflow horizontal |
| Tela de captura em viewport 768 × 1024 | Sem overflow horizontal |
| Resultados de vídeo em viewport 768 × 1024 | Sem overflow horizontal |
| PostgreSQL 18.4 isolado: upgrade/check/downgrade/upgrade/check em banco descartável | Passou |
| Alembic check no banco de demonstração | Sem divergência de esquema |
| npm audit | Nenhuma vulnerabilidade conhecida reportada |
| pip-audit das dependências declaradas | Nenhuma vulnerabilidade conhecida reportada |

O teste de navegador usa dados de identificação fictícios e a imagem pública de exemplo MediaPipe, fora do repositório. A câmera simulada fornece frames da imagem, mas **a detecção, os landmarks, o skeleton, os cálculos, a API, o PostgreSQL e a geração de PDF são reais**. Não há interceptação da resposta do modelo nem medidas fixadas para o teste de integração.

## Limites da verificação
- A webcam física do usuário não foi acionada. Seu dispositivo, iluminação e desempenho precisam ser verificados na tela de captura.
- Docker não está instalado neste ambiente. Dockerfiles e Compose foram escritos, mas a construção/subida dos containers não foi executada aqui. A stack foi executada nativamente com PostgreSQL.
- PostgreSQL 18.4 foi usado localmente; Compose declara PostgreSQL 17. Não foi feito teste em servidor 17 nesta sessão.
- Os testes Python apresentam dois avisos de depreciação nas bibliotecas de teste (adaptação httpx/Starlette e alias AnyIO), sem falhas.
- Auditorias de dependências consultam vulnerabilidades conhecidas no momento; não equivalem a auditoria completa de segurança.
- Sem validação clínica, regulatória, de performance em múltiplos dispositivos ou de operação com dados reais.
- Vídeo de integração usa pessoa imóvel da imagem pública, não movimento clínico real. Foi confirmado que produz zero ciclos completos. Fases e protocolos dinâmicos foram testados matematicamente com dados sintéticos; sua precisão em agachamentos/elevação de braço reais ainda não foi validada.

A migração aditiva `8b3675a1a316` foi aplicada e verificada. A série salva inclui índices originais, timestamps, qualidade, valores nulos, landmarks e versões. O modelo Python também foi executado diretamente sobre a imagem de referência e retornou 33 landmarks reais. `ruff check --select F` passou. OpenCV emite um aviso de tag VP80 ao escrever o vídeo sintético dos testes; o arquivo foi decodificado com timestamps verificados.

## Aceite manual recomendado
Com dados fictícios, autorize sua webcam, confira o skeleton, capture cada vista, compare os landmarks com a imagem e examine os motivos de medidas indisponíveis. Confirme ou descarte registros, salve observações, baixe o PDF e reabra a avaliação pelo histórico. Avalie a legibilidade em seu monitor/tablet e a performance em 2/5/10 FPS.
