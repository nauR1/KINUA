# KINUA — auditoria de engenharia e estabilização 2.2.1

Regressão: 09/09/2026. Finalização: 14/09/2026. Base: b6c4238 (2.2.0). Escopo: funcionalidades existentes; nenhum novo módulo do roadmap. Ambiente: Windows, Python 3.12, Node 22, PostgreSQL 18.4, SQLite e Chrome.

## A. Resumo executivo

Antes: núcleo funcional com 91 testes backend e cinco cenários E2E, mas com lacunas em cancelamento/retry, matemática degenerada, edição de pacientes e concorrência de rascunhos. A instalação Docker perderia o catálogo da migration devido ao dockerignore. A edição existia na API sem acesso pela interface.

Depois: tentativas do worker isoladas, cálculos inválidos recusados, fluxo de edição ligado à API, proteção otimista de edição e salvamento de conclusão serializado. Mensagens de câmera, descarte de arquivo inválido, navegação com rascunho e consultas de revisão/histórico foram corrigidos. O código mantém Next/FastAPI/PostgreSQL, identidade KINUA, dados reais persistidos e resultados versionados.

Não há P0/P1 conhecido nos fluxos locais verificados ao encerrar esta auditoria. Isso não representa liberação clínica, certificação de segurança ou validação de operação pela internet. Os bloqueios de implantação de clinical-readiness.md permanecem aplicáveis.

## Mapa do sistema real

- Frontend: uma página de aplicação com seções de login, dashboard, pacientes, avaliações, análise, protocolos, ROM, relatórios e configurações. Não há roteamento por URL para cada avaliação; recarregar volta ao painel e os dados são retomados pelo histórico.
- API: auth, dashboard, pacientes, avaliações, mídia, análise de foto, jobs de vídeo, revisão, PDF, comparação, protocolos, ROM e administração/auditoria. Configurações de regras são informativas; não há editor de regras nem de versões de protocolos.
- Persistência: 26 tabelas relacionais, migrations Alembic, FKs e unicidade de mídia/análise, frames, sessão, versão e etapa; mídia privada fora do banco.
- Visão: MediaPipe em Worker no navegador para foto/prévia; MediaPipe/OpenCV em subprocesso para vídeo. Provider desacoplado da geometria. Landmarks de fotos chegam do cliente e ainda não têm verificação independente no servidor.
- Medição: BiomechanicsEngine, MotionEngine, ROMEngine; medidas em graus ou razões, série em ms, velocidades por segundo. Interpretação clínica separada, thresholds clínicos desativados e pendentes de validação.
- Protocolos: sete categorias, roteiro de joelho com 12 etapas. Mapa da dor/step-down indisponíveis; anamnese/testes manuais são texto profissional. Uma captura filha por etapa. Isso é limitação explícita, não simulação.
- ROM: sete movimentos, plano/lado confirmado, prévia, vídeo persistido, extremos/frame, série, revisão e histórico de valores confirmados. A câmera não comprova plano anatômico 3D.
- Administração: cadastro e listagem de profissionais e logs; não inclui revogação administrativa completa, redefinição de senha ou MFA.

Busca por TODO/FIXME/mock/fake/placeholder/random identificou fixtures E2E, seeds explícitos, placeholders de formulário, estados vazios e contratos Protocol com métodos abstratos. Não foram encontrados números aleatórios alimentando análises de produção. Identificadores internos Biometria permanecem para compatibilidade de cookie, CSRF, banco e diretórios; a interface é KINUA.

## B. Bugs relevantes

| ID / gravidade | Problema e causa | Correção | Teste e status |
|---|---|---|---|
| B01 P1 | Docker ignorava migrations/data, exigido pela migration | Exceção explícita para catálogo versionado no dockerignore | Catálogo presente no pacote; migration limpa passou. Execução Docker PARTIAL por runtime ausente |
| B02 P1 | Worker antigo podia publicar após cancelar/recomeçar: só comparava estado running | run_token por tentativa; heartbeat/publicação/falha tardia condicionados ao token | Corrida reproduzida antes; testes de publicação e falha tardia PASS |
| B03 P2 | angle aceitava NaN/Infinity devido ao clamp do acos | Validação finita antes da geometria | Três casos falharam antes e passaram depois; API também rejeita não finitos |
| B04 P1 | Tronco com hip=shoulder produzia 0° válido | Geometria compartilhada recusa segmento nulo | Caso reproduzido e teste PASS |
| B05 P1 | Elevação válida do braço podia ser descartada com pernas ocultas: qualidade só considerava medidas estáticas | Validade do frame considera todas as medidas existentes do movimento | Teste falhou antes e passou depois |
| B06 P2 | Prévia ROM aceitava landmarks duplicados, sobrescrevendo pelo nome | Validação de unicidade | 200 reproduzido antes; 422 esperado agora PASS |
| B07 P1 | Edição de paciente sem entrada na interface, apesar do PATCH existente | Formulário reutilizado com dados existentes e ação Editar paciente | E2E criar/editar/reabrir, telefone/histórico preservados PASS |
| B08 P1 | Edições concorrentes podiam sobrescrever paciente/notas/conclusão | Revisão de conteúdo para paciente e valores esperados para observações; locks na transação | API recusa versão/valor antigo com 409; preserva primeira gravação PASS |
| B09 P1 | Autosave da conclusão enviava gravações simultâneas | Fila serial e base confirmada a cada gravação | E2E com primeira resposta atrasada mantém Latest draft e duas gravações PASS |
| B10 P2 | Notas locais podiam ser perdidas ao navegar ou omitidas do PDF sem aviso | Bloqueio de navegação pendente, aviso ao recarregar e recusa de PDF com rascunho | E2E de avaliação/revisão/conclusão e revisão de estados PASS |
| B11 P2 | Arquivo inválido mantinha mídia anterior pronta para envio | Limpa seleção anterior ao validar nova mídia | Revisão de fluxo e regressão foto/vídeo PASS |
| B12 P2 | Falhas de câmera exibiam mensagem nativa; abertura tardia podia manter stream após desmontar | Tradução de erros, evento ended e limpeza de stream ao desmontar | Unitários e E2E para recusa/ausência/ocupação PASS; desconexão física PARTIAL |
| B13 P2 | Consulta por finding/revisão e por medida ROM causava N+1 | Busca agrupada de revisões e joins de histórico ROM | Regressão de resultados/histórico/PDF PASS; carga externa não medida |
| B14 P3 | /health anunciava versão antiga | Usa a versão declarada da API | Startup/health PASS |
| B15 P2 | Resumo de movimento herdava status indisponível do primeiro frame apesar de amostras válidas | Resumo com amostras válidas marca measured | Regressão de movimentos/worker PASS |

Os primeiros casos matemáticos/worker/preview tiveram seis falhas reproduzidas antes da correção. O caso de braço válido com pernas ocultas foi reproduzido separadamente. Correções de integração/estado usam reprodução pelo código e regressão API/E2E. Erros de seletores da automação foram corrigidos sem retirar assertions nem desabilitar cenários.

## C. Arquivos alterados

A lista exata está em audit-files.txt. Grupos principais:

- backend/app/jobs.py, models.py e migration: isolamento de tentativas.
- backend/app/biomechanics: validação geométrica e qualidade dinâmica.
- backend/app/api_protocols.py, main.py, schemas.py, repositories.py, services: validação, concorrência, integração e consultas.
- frontend/components/PatientForm, Results, ProtocolWorkspace, Capture, VideoCapture; app/page; lib/api e camera: estados, integração e erros.
- backend/tests/test_stabilization.py e test_protocols_rom.py; frontend/tests/camera.test.ts; e2e/audit.spec.ts e autosave.spec.ts: regressão.
- .dockerignore, backend/ruff.toml, CI, README e docs: instalação, lint e documentação real.
- Outros arquivos Python receberam organização de imports/formatação; sem troca de bibliotecas nem arquitetura.

## D. Banco e migrations

Nova revisão 2a9c071bf630, filha de 6d49ba3c72e9: acrescenta processing_jobs.run_token, string nullable. Não modifica dados clínicos nem recalcula análises.

Upgrade/check/downgrade/upgrade/check passaram em PostgreSQL descartável. Instalação vazia via Alembic passou em SQLite, com catálogo de protocolos e sem ajustes manuais. No banco local, foi criada cópia PostgreSQL antes da aplicação e as contagens de pacientes/avaliações/análises permaneceram iguais durante a migration. Os testes usam banco separado; dados clínicos não foram usados como fixtures.

Parar workers antigos e aguardar jobs antes de atualizar. A cópia local do banco não substitui backup operacional criptografado e ensaio de recuperação de banco+mídia.

## E. Testes

Resultados finais estão em audit-results.json: **140 testes SQLite, 140 PostgreSQL, 6 unitários frontend e 11 E2E aprovados; zero falhas e zero skips nessas execuções**. As duas execuções backend cobrem a mesma suíte em bancos diferentes. Fixtures usam dados sintéticos e MediaPipe real para integração; não constituem população de validação clínica.

- Backend: geometria, ROM nos ângulos 0/45/90/135/180 e adicionais, escalas e espelhamento; autenticação/expiração, escopo, uploads, quatro vistas, protocolo, revisão, snapshots, worker/cancelamento, persistência e PDF.
- Frontend unitário: contrato canônico dos 33 landmarks e mensagens de câmera.
- E2E: login/cadastro/edição/histórico; protocolo completo com ROM e PDF; autosave atrasado; foto real; câmera/skeleton; vídeo real; recusa/ausência/ocupação; seis resoluções.
- Segurança de mídia: assinatura/decodificação, tamanho, normalização, EXIF, caminhos privados, acesso de outra clínica e hash de integridade.
- Dependências: npm audit e pip-audit sem vulnerabilidades conhecidas reportadas na data. Instalação fresca das versões existentes passou; nenhuma atualização crítica foi feita.

## F. Build e instalação

Instalação nova a partir do pacote 2.2, seguida das correções desta rodada em checkout isolado: venv novo, pip install, npm ci, migrations, seed de conta QA, download/hash do modelo, prepare:vision, build e startup de API/worker/frontend PASS. A versão final gera build de produção e typecheck; lint frontend e backend PASS.

Docker: arquivos revisados e bug do catálogo corrigido; build/start do Compose não executados porque Docker não está instalado nesta máquina. Nenhum resultado de execução de container é presumido.

## G. Matriz funcional

| Área | Estado | Evidência / limite |
|---|---|---|
| Login/logout/sessão expirada/endpoint protegido | PASS | API e navegador |
| Isolamento por clínica/admin | PASS | Testes de acesso e recursos privados |
| Pacientes: cadastrar/editar/reabrir | PASS | API + E2E, campos opcionais preservados |
| Dashboard/listagens/histórico | PASS | Dados persistidos e navegação |
| Avaliação foto/webcam | PASS | MediaPipe real, skeleton, upload, revisão e retorno |
| Vistas anterior/posterior/laterais | PASS | Persistência de metadados na API; confirmação humana obrigatória |
| PNG/JPEG/WebP/EXIF/arquivo inválido/limites | PASS | Testes de normalização e validação |
| Vídeo/worker/timeline/revisão | PASS | Fixtures reais, timestamps, cancelamento/retry e PDF |
| Protocolos/versionamento/retomada | PASS | Snapshot e fluxo de joelho completo |
| Etapas de módulos futuros | PARTIAL | Indisponíveis e justificáveis, conforme escopo anterior |
| ROM: sete movimentos, matemática, pico e histórico | PASS | Geometria conhecida, worker/API/E2E |
| Comparação e mapa corporal existentes | PASS | Testes de compatibilidade e resultados ligados a regiões |
| Relatórios | PASS | Geração, conteúdo, snapshots e inspeção visual |
| Configurações/equipe/auditoria | PASS | API/admin e navegação; não é gestão completa de identidade |
| Seis resoluções solicitadas | PASS | Sem overflow global/erro JS nas seções testadas |
| Acessibilidade | PARTIAL | Labels, foco e navegação revisados; sem auditoria WCAG formal/leitor de tela |
| Câmera física/múltiplos dispositivos/mobile | PARTIAL | Preferência environment; erros simulados e câmera de fixture; sem matriz física de dispositivos |
| Docker | PARTIAL | Runtime indisponível; revisão estática e migration fora do container |
| Performance sob carga | PARTIAL | N+1 reduzido; sem carga concorrente de produção nem metas de latência definidas |
| Uso clínico pela internet | PARTIAL / NÃO LIBERADO | Validação clínica e bloqueios operacionais existentes |

## H. Limitações restantes

- Não há comprovação quantitativa da acurácia dos landmarks, planos, lateralidade física e ROM contra instrumentos de referência. Visibilidade não é confiança diagnóstica. Perspectiva/rotação podem produzir erro mesmo com plano confirmado.
- Hip/shoulder ROM são aproximações entre segmentos; não isolam orientação pélvica/glenoumeral. Ângulos não orientados não identificam hiperextensão. Picos entre amostras podem ser perdidos.
- Não houve laboratório de codecs e orientação mobile em múltiplos navegadores/dispositivos. Vídeos com timestamps inválidos são recusados.
- Proteção otimista de pacientes e observações depende dos campos expected enviados pelo cliente; a UI usa o contrato. Clientes antigos sem esses campos mantêm comportamento compatível. Etapas de protocolo exigem revisão numérica.
- Não há edição de protocolos/regras na UI, portal do paciente, novos testes funcionais ou módulos Sport/Rehab/Copilot/Gait/3D. Nada disso foi apresentado como entregue.
- Não foi realizado pentest externo, teste de recuperação operacional, implantação HTTPS, revisão regulatória ou validação assistencial. Consulte clinical-readiness.md.

## I. Débitos técnicos

1. Paginação server-side além do limite atual de 500 pacientes; avaliar volume e busca remota antes de escala maior.
2. Requisições de relatório ainda usam GET e criam snapshot; normalizar esse contrato em mudança compatível futura.
3. Exigir precondições de concorrência também de todos os clientes externos quando houver API pública versionada.
4. Medir custos de leitura/hash por requisição de mídia, payload de séries e armazenamento sob carga; preservar integridade.
5. Resolver avisos de depreciação FastAPI/Starlette com atualização compatível planejada, sem atualização crítica oportunista. OpenCV avisa sobre tag VP80, mas os vídeos de teste foram decodificados.
6. CI executa testes, migrations e build; os E2E ainda requerem ambiente/modelo/fixtures explicitamente preparados.
7. Validar Docker, acessibilidade formal e dispositivos físicos em ambiente apropriado.

Na retomada de 14/09, os serviços estavam desligados. O build local inicialmente encontrou um lock inacessível no diretório gerado; o diretório foi preservado fora do repositório e um build limpo passou. As quatro páginas do PDF de QA foram renderizadas e inspecionadas sem cortes.

A rodada termina na estabilização. O roadmap não foi avançado.
