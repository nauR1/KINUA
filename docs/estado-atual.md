# Estado atual — KINUA 2.3.0

**Consolidação:** 16/09/2026  
**SHA de aplicação verificado em produção:** `c21484f5ab07fdc9f9a8db61ba1e822d71f74e32`  
**Ambiente:** Railway `production`

Este documento é a referência atual do sistema. Auditorias e release notes mais antigas são evidências históricas e não devem ser usadas isoladamente para inferir o estado presente.

## Resumo executivo

KINUA é uma plataforma web para apoio à avaliação fisioterapêutica, com cadastro de pacientes, foto/câmera/vídeo, landmarks, medições geométricas, análise temporal, Protocolos, ROM, revisão profissional, histórico e PDF. A plataforma também possui administração comercial, planos, expiração/suspensão, ambiente demo isolado e auditoria.

A infraestrutura essencial de produção está operacional e foi ensaiada: frontend, backend, worker, PostgreSQL persistente e bucket S3 estão ativos; o banco sobreviveu a restart; backup real foi enviado ao S3; um PostgreSQL auxiliar descartável restaurou o backup do zero e recuperou 28 tabelas com Alembic `9e1609260000`.

**Isso não equivale a validação clínica ou liberação regulatória.** A precisão clínica, confiabilidade contra padrão de referência, enquadramento regulatório, governança LGPD e matriz física de dispositivos permanecem trabalhos separados.

## Produção verificada

| Componente | Estado em 16/09/2026 | Observação |
|---|---|---|
| Frontend | SUCCESS | Next.js standalone, healthcheck `/` |
| Backend | SUCCESS | FastAPI, healthcheck `/health` aprovado |
| Worker | SUCCESS | Python/MediaPipe/OpenCV, storage S3 |
| PostgreSQL persistente | SUCCESS | volume persistente validado após restart |
| PostgreSQL auxiliar | SUCCESS no drill | usado apenas como ambiente descartável de restauração |
| Bucket `kinua-media` | ativo | put/get/delete/cleanup reais aprovados |
| Backup | PASS | diário às 06:15 UTC + validação imediata |
| Restore drill | PASS | 28 tabelas, migration `9e1609260000` |
| GitHub Actions | SUCCESS | workflow normal da `main` |

Configuração de produção confirmada: `ENVIRONMENT=production`, `SECURE_COOKIES=true`, `ALLOW_DEMO_SEED=false`, `STORAGE_BACKEND=s3`. `DEMO_PASSWORD` não é usada como segredo de runtime para recriar conta automaticamente.

## Migration head

Head esperado: **`9e1609260000`** (`9e160926_user_access_start.py`).

A migration adiciona `users.access_starts_at` nullable. `NULL` significa herança da janela da clínica. Não há backfill destrutivo.

## Acesso comercial

- Papéis: `platform_admin`, `admin`, `physiotherapist`.
- Planos: trial, monthly, quarterly, annual, custom, lifetime.
- `platform_admin` não recebe acesso clínico por ser global.
- Usuário sem override herda a janela da clínica.
- Usuário com início explícito futuro recebe `access_not_started`.
- Lifetime não expira; `access_expires_at` da clínica fica `NULL`.
- Suspensão/expiração revogam ou bloqueiam acesso conforme política do backend.
- Timestamps são normalizados em UTC; o frontend envia `null` quando o campo individual está vazio.

## Funcionalidades e evidência atual

| Área | Estado | Limite principal |
|---|---|---|
| Login/sessão/logout | implementado/testado | sem MFA e sem self-service de senha |
| Isolamento por clínica | testado | não há isolamento por profissional dentro da mesma clínica |
| Pacientes/histórico | implementado | paginação ainda limitada |
| Foto/webcam | implementado | hardware físico não coberto por matriz ampla |
| Vídeo | implementado | MP4/WebM/MOV decodificáveis; HEVC físico de iPhone ainda exige ensaio |
| Worker | implementado/produção | carga concorrente ainda não caracterizada |
| Protocolos | implementado | validação clínica por protocolo pendente |
| ROM | implementado | não substitui goniometria/3D sem validação |
| Revisão/PDF | implementado | decisão final permanece profissional |
| Demo | isolado | não inserir dados reais |
| Administração comercial | implementada | sem gateway/billing automático |
| Backup/restore | ensaiado | ainda faltam metas formais de RPO/RTO e retenção |

## Visão computacional

Frontend: `@mediapipe/tasks-vision 0.10.32`.  
Backend: `mediapipe 0.10.35`.  
Modelo em ambos: `pose_landmarker_lite/float16/1`.  
SHA-256: `59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a`.

O modelo é o mesmo, mas as bibliotecas de runtime não têm a mesma versão. Manter matriz de compatibilidade e regressão antes de atualizar qualquer lado.

## Segurança e privacidade

Implementado: Argon2, sessão opaca hash no banco, cookies HttpOnly/Secure/SameSite Strict em produção, CORS/origin restritos, isolamento por clínica, storage privado, limites de upload, auditoria, containers sem root, API/banco sem exposição pública deliberada, `robots.txt` com `Disallow: /` e `X-Robots-Tag: noindex,nofollow,...`.

Pendências prioritárias: repositório GitHub ainda público, `main` sem branch protection, recuperação de senha, MFA, pentest externo, monitoramento/alertas, política formal de retenção/incident response e avaliação LGPD/transferência internacional.

## Testes

No SHA `c21484f5...`, GitHub Actions concluiu com sucesso. A suíte backend corrente tem **218 testes** e Alembic round-trip/check aprovados. Frontend passou `prepare:vision`, TypeScript, lint/Prettier, unit tests e build de produção. Há E2E separados para acesso, demo, workflow clínico, vídeo, protocolos/ROM, câmera simulada e autosave.

Resultados numéricos de documentos antigos devem ser lidos como históricos.

## O que foi comprovado desde auditorias anteriores

Itens antes listados como pendentes e hoje comprovados tecnicamente:

- deploy Railway real;
- S3 real com leitura/escrita/exclusão;
- worker usando `backend=s3`;
- persistência do PostgreSQL após restart;
- backup automático real;
- restauração completa em banco descartável;
- vídeo/worker novamente funcional em produção;
- compatibilidade MOV/QuickTime validada no pipeline real de testes;
- `robots/noindex` publicado;
- CI principal verde.

## Pendências reais

1. validação clínica quantitativa por medida/movimento/protocolo;
2. avaliação regulatória formal e finalidade de uso;
3. governança LGPD e contratos/processos operacionais;
4. tornar repositório privado e proteger `main`;
5. recuperação de senha e MFA;
6. teste físico estruturado em iPhone/Android, incluindo HEVC/H.265;
7. carga, concorrência, observabilidade e alertas;
8. pentest autorizado;
9. definir e medir RPO/RTO, retenção e política de backups;
10. manter documentação e matriz de versões sincronizadas com cada release.
