# API — KINUA 2.3.0

Documentação interativa local: `http://127.0.0.1:8000/docs`. OpenAPI: `/openapi.json`. Em produção a API é consumida pelo frontend via `/api/*` e não precisa de domínio público.

Recursos clínicos exigem cookie `biometria_session`. Mutações exigem `X-Requested-With: Biometria` e Origin permitido quando presente.

## Rotas principais

| Método | Rota | Função |
|---|---|---|
| POST | `/auth/login` | cria sessão opaca |
| GET | `/auth/me` | usuário/tenant atual |
| POST | `/auth/logout` | revoga sessão atual |
| GET | `/dashboard` | indicadores da clínica |
| GET, POST | `/patients` | busca/lista e cadastro |
| PATCH | `/patients/{id}` | edição com concorrência otimista |
| GET | `/patients/{id}/assessments` | histórico |
| POST | `/assessments` | cria avaliação |
| GET, PATCH | `/assessments/{id}` | snapshot/notas/conclusão |
| POST | `/assessments/{id}/media` | imagem + vista |
| POST | `/assessments/{id}/videos` | MP4/WebM/MOV validado + vista |
| POST | `/assessments/{id}/jobs` | cria/reenvia job |
| GET | `/assessments/{id}/jobs` | estado/progresso |
| POST | `/jobs/{id}/cancel` | cancela tentativa |
| GET | `/comparisons` | comparação compatível |
| GET | `/media/{id}` | mídia autenticada |
| POST | `/assessments/{id}/analyze` | landmarks → análise |
| POST | `/findings/{id}/review` | revisão profissional |
| GET | `/assessments/{id}/report` | PDF/snapshot |
| GET | `/settings/rules` | regras configuradas |
| GET | `/admin/audit` | auditoria do tenant |
| GET, POST | `/admin/users` | equipe da clínica |
| GET, POST | `/platform/users` | usuários globais/comerciais |
| GET, POST | `/platform/clinics` | clínicas/planos |
| PATCH | `/platform/users/{id}` | estado, papel e janela individual |
| PATCH | `/platform/clinics/{id}` | estado/plano/janela da clínica |
| POST | `/platform/clinics/{id}/extend` | trial/extensão |
| GET | `/health` | API + banco |

## Mídia

Fotos: JPEG/PNG/WebP, limite padrão 20 MB e validação de conteúdo/dimensões.  
Vídeos: MP4/WebM/MOV (QuickTime), até 100 MiB e 60 s, desde que assinatura/conteúdo/decoder sejam aceitos. A extensão sozinha não concede confiança.

MOV foi adicionado para compatibilidade com arquivos de biblioteca iOS. HEVC/H.265 continua dependente da capacidade do decoder e precisa de teste em dispositivos reais.

## Análise estática

Contrato inclui `media_id`, provider/versão, 33 landmarks canônicos, timestamp e confirmações de câmera/vista. Medidas prontas enviadas pelo cliente não são aceitas como fonte de verdade. Mídia/análise ficam vinculadas ao tenant.

## Vídeo

Jobs têm estados `pending`, `running`, `succeeded`, `failed`, `cancelled`. `run_token` identifica cada tentativa e impede que um worker/tentativa antiga publique resultado após cancelamento/retry.

## Protocolos e ROM

Rotas de protocolos e ROM reutilizam autenticação/tenant, mídia, jobs, análise, revisão e relatórios. Consulte `protocols.md` e `rom.md` para fórmulas/contratos detalhados.

## Administração e acesso

`User` possui `access_starts_at` e `access_expires_at` opcionais. `NULL` é ausência de override individual. Timestamps enviados devem ser timezone-aware. O frontend converte `datetime-local` explícito para UTC e envia `null` em campo vazio.

Planos incluem `trial`, `monthly`, `quarterly`, `annual`, `custom`, `lifetime`. Lifetime não deve expirar por datas comerciais herdadas; início individual explícito continua aplicável.

## Status HTTP relevantes

- `401`: sessão ausente/inválida/expirada;
- `403`: permissão, origem ou política de acesso comercial;
- `404`: recurso não visível ao tenant (inclusive cross-tenant);
- `409`: conflito/estado imutável/concorrência;
- `413`: payload acima do limite;
- `422`: validação;
- `429`: excesso de tentativas de login.

## Concorrência

Edição de paciente usa `expected_revision`; notas/conclusão usam valores esperados. Etapas de protocolo possuem revisão. Divergência retorna 409 e preserva o estado persistido.
