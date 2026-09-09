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

Fotos até 20 MB e 20 megapixels; formato real JPEG, PNG ou WebP. Na interface fotos são redimensionadas para até 1920 px antes do envio. Vídeo contínuo não é aceito no MVP.
