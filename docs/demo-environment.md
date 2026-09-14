# KINUA 2.3 — Produção e demonstração

## Separação explícita

`Clinic.is_demo` é persistido no backend, não pode ser alterado pelos formulários de clínica e é a fonte da identificação visual e da exceção comercial. Todas as clínicas anteriores à migration `8d402b230000` recebem `false`. O bootstrap normal, inclusive `python -m app.seed --platform-admin --email administrador@exemplo.com`, cria somente a clínica administrativa, usuário e registros técnicos indispensáveis. Não cria pacientes, avaliações ou mídias.

`ENVIRONMENT=production` continua ativando as exigências de HTTPS, cookies seguros e PostgreSQL. `APP_MODE=production|demo|development` descreve a instalação; nunca autoriza acesso nem ativa seed. `ALLOW_DEMO_SEED=false` é o padrão em todos os modos. As autorizações de usuário e isolamento entre clínicas continuam no backend. Demo dispensa assinatura comercial, mas respeita usuário/clínica ativos e expiração individual de acesso. Usuário demo não acessa a administração global. Não é permitido criar/promover platform_admin dentro da clínica demo.

## Criar e resetar

No diretório `backend`, com dependências instaladas e `DATABASE_URL` apontando para o banco escolhido:

```powershell
python -m alembic upgrade head
$env:APP_MODE = 'demo'
$env:ALLOW_DEMO_SEED = 'true'
python -m app.demo_seed --email demo@kinua.app
```

A senha é solicitada sem eco (12–128 caracteres). Alternativamente, defina `DEMO_PASSWORD` por um gerenciador de segredos ou variável temporária; nunca a grave no repositório. Sem reset, reexecutar o comando preserva dados e senha existentes e tenta concluir eventuais exclusões de mídia pendentes.

Reset explícito, usando o mesmo e-mail:

```powershell
$env:ALLOW_DEMO_SEED = 'true'
python -m app.demo_seed --email demo@kinua.app --reset
Remove-Item Env:ALLOW_DEMO_SEED
Remove-Item Env:DEMO_PASSWORD -ErrorAction SilentlyContinue
```

Em Docker Compose, prefira a flag restrita ao comando: `docker compose exec -e ALLOW_DEMO_SEED=true backend python -m app.demo_seed --email demo@kinua.app`. Acrescente `--reset` apenas para reset. A senha continua sendo solicitada pelo terminal.

O e-mail de conta não demo é recusado sem converter a clínica. Use a conta originalmente provisionada para identificar a demo a resetar. Um e-mail inexistente cria uma nova clínica demo. Não execute comandos QA contra o banco clínico. O antigo `app.seed --demo` aborta com orientação para o novo comando.

## Conteúdo e apresentação

São criados três registros explicitamente sintéticos: Ana Demonstração, Carlos Exemplo e Marina Teste. Não há CPF, endereço, telefone, imagem, landmark ou medida inventada. Ana possui histórico concluído sem captura/medidas e acompanhamento pendente; Carlos possui avaliação pendente; Marina não tem avaliação. A conclusão informa que é um registro demonstrativo sem resultados clínicos. Para demonstrar medidas, realize captura/inferência real usando somente material autorizado para demonstração.

Após login, o banner permanente identifica todos os dados como fictícios. O cadastro de paciente mostra aviso e exige confirmação visual. Esses controles não identificam automaticamente dados reais: a equipe deve usar apenas identidades sintéticas e mídias autorizadas. Não importe cópias do banco clínico. Se alguém inserir dados indevidos, interrompa a apresentação e siga o procedimento de privacidade da instituição.

PDFs gerados para demo recebem `DEMONSTRAÇÃO — DADOS FICTÍCIOS` no início e no rodapé de cada página. PDFs de outras clínicas seguem o formato anterior. Administração global oferece badge DEMO e filtros Todas/Produção/Demonstração. Contadores de clientes ativos, vencimentos e usuários comerciais excluem demo. Os totais de clínicas distinguem produção e demo.

## Reset e armazenamento

O reset adquire lock na clínica, verifica `is_demo`, recusa platform_admin e jobs pendentes/em execução. Aguarde os jobs terminarem ou cancele pelo fluxo existente antes de resetar. Remove registros dependentes em ordem de FKs, incluindo sessões, usuários, pacientes, avaliações, protocolos, ROM, mídias, análises, frames, landmarks, medidas, achados, revisões, relatórios, jobs e auditoria daquela clínica. Recria a conta e o conteúdo inicial na mesma transação. Referências externas inconsistentes provocam abort e rollback. Catálogos globais e outras clínicas são preservados.

Novas mídias usam `demo/<clinic_id>/<uuid>.<ext>` ou `production/<uuid>.<ext>`, tanto no armazenamento local quanto S3. Chaves legadas continuam legíveis, sem renomeação de arquivos existentes. O reset recusa qualquer chave fora do prefixo exato da demo. Não há operação de exclusão recursiva por bucket/pasta.

A transação grava as exclusões em `demo_media_cleanup`. Somente após commit, os objetos são apagados individualmente. Falhas no storage preservam a fila para nova tentativa; o banco já pode ter sido resetado mesmo quando o CLI termina com erro de limpeza. Reexecute SEM `--reset` para retomar. Exclusões são idempotentes. Não se promete atomicidade distribuída entre PostgreSQL e S3. PostgreSQL é recomendado para concorrência; SQLite é adequado a desenvolvimento/QA, sem a mesma semântica de row locks.

## URLs e instalações separadas

A mesma aplicação aceita demo no PostgreSQL atual, isolada por tenant, ou em instalação independente com outro `DATABASE_URL`. Para `app.kinua...` e `demo.kinua...`, configure cada frontend para seu backend e cada backend/worker para o respectivo banco e storage. Use cookies seguros, HTTPS e `ALLOWED_ORIGINS` da URL correspondente, seguindo `privacy-security.md` e a documentação de implantação existente. `APP_MODE` não fixa domínio nem banco.

Uma instalação demo independente deve receber migrations, catálogos técnicos e seed explícito. API e worker compartilham banco, storage e configurações; nunca reutilize credenciais da produção. É possível usar bucket privado separado ou os prefixos isolados no mesmo bucket. Nenhuma implantação Railway ou alteração DNS foi executada nesta rodada.

## Verificação

`pytest -q` inclui os testes de seed, reset/rollback, tenant isolation, PDF, métricas, prefixos e flags. `frontend/e2e/demo.spec.ts` exige `E2E_ISOLATED=1`, banco QA e credenciais externas; nunca descobre ou usa automaticamente o banco clínico. Consulte `demo-release.md` para os resultados desta rodada. Os testes matemáticos, protocolos e ROM existentes permanecem como regressão; não houve alteração das fórmulas ou regras clínicas.


Para reproduzir o E2E, configure externamente: E2E_BASE_URL (frontend QA com proxy /api), E2E_ISOLATED=1, E2E_EMAIL e E2E_PASSWORD para o administrador clínico de QA; um platform_admin `platform@kinua.local` com a mesma senha temporária do laboratório; E2E_DEMO_DATABASE, E2E_DEMO_STORAGE, E2E_PYTHON e E2E_BACKEND apontando exclusivamente para QA. A demo criada pelo teste usa demo@qa.local. Execute `npx playwright test e2e/demo.spec.ts` no frontend. Para a suíte de câmera/vídeo, acrescente E2E_CAMERA_FILE e E2E_IMAGE apontando para fixtures autorizadas. Esses dados de laboratório não devem ser reutilizados em instalação pública.
