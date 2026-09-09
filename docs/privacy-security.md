# Privacidade e segurança

## Implementado
- Argon2 para senhas; não há senha padrão no código. Bootstrap explícito exige 12 caracteres.
- Sessões aleatórias de 48 bytes, hash SHA-256 no banco, validade de 8 horas, cookie HttpOnly/SameSite=Strict, revogação no logout.
- Origin permitido e cabeçalho customizado em operações mutáveis; CORS restrito. Nenhum token de autenticação em localStorage.
- Cinco tentativas inválidas por conta em 15 minutos acionam bloqueio temporário. E-mails de tentativa são armazenados como hash; a resposta de erro é genérica.
- Autorização por clínica em pacientes, avaliações, mídia, revisão e relatório. Administração exige papel admin. Pacientes ainda não possuem portal.
- Upload limitado, decodificação real de imagem, dimensões máximas e reencodificação JPEG. EXIF e localização são removidos. Nome de arquivo enviado não vira caminho do servidor.
- Arquivos fora da área pública, nome aleatório e download autenticado. SHA-256 da mídia normalizada e do PDF registrado.
- Pydantic rejeita campos extras, NaN, infinitos, landmarks duplicados e valores fora dos limites técnicos.
- Auditoria sem queixas, notas, senhas ou imagem: ator, clínica, ação, recurso e data. Logs de acesso do Uvicorn desabilitados na configuração de implantação.
- Usuários de container sem privilégios; PostgreSQL sem porta pública; frontend exposto somente em loopback por padrão.

## Limites explícitos antes de dados reais
Esta entrega não afirma conformidade LGPD nem autorização regulatória. A operação com dados de saúde exige definição pelo responsável de finalidade/base legal, retenção, descarte, direitos dos titulares, controle de acesso, contratos, resposta a incidentes e adequação regulatória. São decisões organizacionais e jurídicas, não garantias dadas pelo código.

TLS, criptografia de disco/volumes, backup cifrado, restauração testada, gestão de segredos, revisão de permissões, monitoramento e atualização de dependências pertencem à implantação. `SECURE_COOKIES=true` deve ser usado com HTTPS. SQLite e cookies sem Secure são apenas para desenvolvimento em localhost.

O MVP não tem MFA, recuperação de senha por e-mail, expurgo automático, antivírus de upload, exportação de dados para titulares, anonimização para treinamento ou log à prova de adulteração. O administrador de banco ainda pode modificar registros. Não há isolamento entre profissionais dentro da mesma clínica: todos os fisioterapeutas autorizados da clínica acessam seus pacientes.

Em fotos/webcam, landmarks são produzidos no navegador e validados estruturalmente no backend. Isso não autentica a origem visual de um cliente modificado. Em vídeo, a inferência é executada pelo servidor sobre o arquivo persistido. Treinamento futuro deve usar consentimento/finalidade apropriados, revisão da qualidade, separação de bases e controles adicionais; salvar revisões não autoriza reutilizar dados para treinamento.

Vídeos têm limite de 100 MiB, 60 segundos e 4K, assinatura de contêiner e validação em subprocesso com limite de 90 segundos. Inferência usa outro subprocesso, limitado a quatro minutos; cancelamento bloqueia publicação. Não existe sandbox de codec além do usuário sem privilégios no container. Vídeos enviados preservam conteúdo/metadados originais, inclusive áudio quando presente; a gravação da aplicação não solicita microfone. O armazenamento permanece privado. Backup e política de retenção devem incluir vídeo e séries temporais.

O detector é executado no dispositivo, com modelo e WASM servidos localmente após instalação. Imagens não são enviadas ao Google. Ao clicar em analisar, a captura é transmitida ao backend da instalação e armazenada para o prontuário.
