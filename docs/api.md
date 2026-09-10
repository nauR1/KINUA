# API

Documentação interativa: `http://127.0.0.1:8000/docs` na execução local. OpenAPI: `/openapi.json`. No Docker a API é interna, acessível pelo frontend em `/api/*`.

Todos os recursos clínicos exigem cookie `biometria_session`. Requisições POST/PATCH/DELETE precisam de `X-Requested-With: Biometria` e Origin permitido quando presente. Nunca enviar senha ou cookie em URL.

| Método | Rota | Função |
|---|---|---|
| POST | /auth/login | Cria sessão opaca |
| GET | /auth/me | Usuário e clínica |
| POST | /auth/logout | Revoga sessão atual |
| GET | /dashboard | Indicadores reais da clínica |
| GET, POST | /patients | Lista/busca e cadastro |
| PATCH | /patients/{id} | Atualiza paciente com auditoria |
| GET | /patients/{id}/assessments | Histórico |
| POST | /assessments | Cria avaliação |
| GET, PATCH | /assessments/{id} | Snapshot e notas/conclusão |
| POST | /assessments/{id}/media | Multipart file + view |
| POST | /assessments/{id}/videos | MP4/WebM + view; validação antes de enfileirar |
| POST | /assessments/{id}/jobs | Cria/reenvia job de vídeo |
| GET | /assessments/{id}/jobs | Estado e progresso persistidos |
| POST | /jobs/{id}/cancel | Cancela fila/processamento, sem publicar parcialmente |
| GET | /comparisons?a={analysis_id}&b={analysis_id} | Diferenças B − A quando compatíveis |
| GET | /media/{id} | Imagem autenticada |
| POST | /assessments/{id}/analyze | Landmarks, versão e confirmações → medidas |
| POST | /findings/{id}/review | Confirma, descarta ou reabre revisão |
| GET | /assessments/{id}/report | Gera PDF e registra snapshot/auditoria |
| GET | /settings/rules | Definições das regras |
| GET | /admin/audit | Últimas 200 ações da clínica |
| GET, POST | /admin/users | Lista/cria profissionais da clínica |
| GET | /health | Conectividade com banco |

## Contrato da análise
`media_id`, `provider`, `provider_version`, `landmarks: [{name,x,y,z,visibility}]`, `timestamp_ms`, `camera_level_confirmed`, `view_confirmed`.

As dimensões e a vista vêm da mídia persistida; valores de medida enviados pelo cliente são rejeitados. Cada mídia recebe uma única análise. Repetição retorna 409. Por padrão os parâmetros não confirmados bloqueiam medidas, com motivos registrados. View: `anterior`, `posterior`, `lateral_right`, `lateral_left`.

Respostas: 401 sem sessão; 403 permissão/origem; 404 recurso não acessível (incluindo outra clínica); 409 estado imutável/conflito; 413 tamanho; 422 validação; 429 tentativas de login.

Fotos até 20 MB e 20 megapixels; formato real JPEG, PNG ou WebP. Na interface fotos são redimensionadas para até 1920 px antes do envio. Vídeos até 100 MiB e 60 segundos, MP4/WebM decodificável e timestamps monotônicos.

## Vídeo e evolução

Criação: `mode: video`, `protocol: bilateral_squat | single_leg_squat | arm_raise`, `side: bilateral | left | right`. Unipodal exige left/right. Foto/câmera estática usa `protocol: static`.

Job: `{media_id, fps: 2 | 5 | 10, camera_level_confirmed: true, view_confirmed: true}`. Resposta 202; estados pending/running/succeeded/failed/cancelled. Jobs concluídos não aceitam reprocessamento. Falhas e cancelamentos aceitam nova tentativa. O endpoint de landmarks estáticos recusa vídeo.

Snapshot: `jobs`, `analyses[].motion` e `frames[].measurements/phase/quality`, além dos landmarks. Séries preservam null; `frame_index` é o índice original decodificado, `timestamp_ms` o tempo original e `sample_index` a posição na lista amostrada.

PDF de evolução: `/assessments/{id}/report?compare_to={analysis_a}&analysis_id={analysis_b}`. B deve pertencer à avaliação da rota, A a outra avaliação do mesmo paciente. Requisitos de compatibilidade também são aplicados. O relatório preserva ambos os IDs, datas e diferenças.

## Assessment Protocols e ROM

Todos exigem sessão, autorização por clínica e proteção CSRF nas mutações.

- GET /protocols: categorias e definições.
- GET /protocols/pending: protocolos pendentes.
- POST /assessment-protocols: patient_id, version_id.
- GET /assessment-protocols/{id}: snapshot e etapas.
- PATCH /assessment-protocols/{id}/steps/{key}: revision, state, result, note; conflito retorna 409.
- POST /assessment-protocols/{id}/steps/{key}/capture: movement e side quando ROM; cria ou retorna avaliação filha.
- POST /assessment-protocols/{id}/complete: conclusion; verifica etapas e filhas.
- GET /rom/movements: fórmulas, planos, instruções e limitações.
- POST /rom/assessments: patient_id, movement, side.
- POST /rom/preview: movement, side, view, landmarks, width, height, brightness, plane_confirmed=true. Não persiste a prévia.
- GET /patients/{id}/rom: histórico e revisão.

ROM reutiliza upload, jobs, resultados, revisão e relatório existentes. PDF do protocolo agrega snapshots das avaliações filhas autorizadas.
