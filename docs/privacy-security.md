# Privacidade e segurança — KINUA 2.3.0

## Controles implementados

- Argon2 para senhas; sem senha padrão no código.
- Sessões opacas, hash SHA-256 no banco, cookies HttpOnly/Secure/SameSite Strict em produção.
- CORS/origens explícitas e proteção adicional em mutações por `X-Requested-With`.
- Rate limit de login por conta/janela.
- Isolamento por `clinic_id` em recursos clínicos.
- `platform_admin` sem acesso clínico automático.
- Uploads com limite, validação/decodificação e nomes de storage controlados pelo servidor.
- Imagens normalizadas removem EXIF/localização; storage não é diretório público.
- S3 privado em produção; teste real de put/get/delete aprovado.
- Auditoria de ações sem registrar senha/hash/imagem/prontuário completo.
- Containers de aplicação executam como usuário não-root.
- Backend e PostgreSQL não precisam de domínio público.
- `ENVIRONMENT=production` exige PostgreSQL, origens HTTPS e cookies Secure.
- Frontend publica `robots.txt` com `Disallow: /` e `X-Robots-Tag: noindex, nofollow, noarchive, nosnippet, noimageindex`.
- `Permissions-Policy` restringe câmera ao próprio site e desativa microfone.

## Persistência e recuperação

Em 16/09/2026 o banco persistente sobreviveu a restart e o bucket foi exercitado. Backup PostgreSQL real é enviado diariamente ao S3 e um restore drill em banco descartável recuperou 28 tabelas no head `9e1609260000`.

Isso resolve a ausência de evidência operacional que constava em auditorias antigas; não resolve sozinho continuidade de negócio. Ainda faltam RPO/RTO, retenção formal, alertas e estratégia de recuperação/versionamento da mídia S3.

## Vídeo

Limite padrão: 100 MiB e 60 s. O backend aceita MP4/WebM/MOV quando o contêiner e o conteúdo são válidos e decodificáveis. Arquivos enviados podem conter áudio/metadados originais; a gravação da aplicação não solicita microfone. Inferência usa subprocesso/worker, com controles de duração e estado.

MOV/QuickTime foi validado em pipeline de engenharia. Isso **não** garante compatibilidade com todo codec de iPhone; HEVC/H.265 precisa de matriz física de dispositivos.

## Visão no navegador

Fotos/webcam usam MediaPipe no browser. A imagem só é enviada ao backend KINUA quando o usuário salva/análise a captura; não é enviada ao Google para inferência. O backend valida landmarks estruturalmente, mas um cliente modificado ainda pode tentar fornecer landmarks não correspondentes à imagem. Avaliar verificação server-side adicional antes de elevar confiança/proveniência.

## Pendências prioritárias

1. repositório `nauR1/KINUA` está **público**; migrar para privado após revisar integrações/deploy;
2. branch `main` está sem proteção obrigatória; exigir PR + CI verde + revisão;
3. MFA não implementado;
4. recuperação de senha por fluxo seguro não implementada;
5. pentest externo/autorizado não realizado;
6. observabilidade/alertas ainda insuficientes;
7. política de retenção/expurgo e resposta a incidentes precisa ser formalizada;
8. revisar segredos/rotação periodicamente;
9. definir governança LGPD, bases legais, direitos do titular, operadores e transferência internacional;
10. não existe isolamento por profissional dentro da mesma clínica.

## LGPD e uso clínico

Dados de saúde, imagens e vídeos corporais são sensíveis. Controles técnicos do código não equivalem a conformidade LGPD. A organização responsável precisa definir finalidade, base legal, transparência, retenção, descarte, atendimento a titulares, incident response e contratos com operadores/suboperadores.

A infraestrutura atual usa região `ams`; portanto, a avaliação de privacidade deve considerar transferência internacional e os termos/garantias dos provedores aplicáveis.

## Princípio de logs

Nunca registrar em logs de aplicação/suporte:

- senha ou hash;
- cookie/session token;
- URL com credencial de banco/S3;
- dump completo de paciente;
- imagem/vídeo clínico;
- conteúdo desnecessário de prontuário.

Evidências de suporte devem preferir IDs técnicos, timestamps, status, versões e mensagens sanitizadas.
