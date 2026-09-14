# KINUA 2.3 — Access, Commercial Administration & Demo Environment

Relatório de preparação local — 14/09/2026. Versão mantida em 2.3.0.

## Resultado

Produção e demonstração possuem identificação persistida, bootstrap separado, armazenamento segregado, controle de acesso, avisos visuais e relatórios distintos. Nenhuma fórmula biomecânica, regra clínica, protocolo ou ROM foi modificada. Não houve novo commit, push, publicação Railway ou alteração DNS nesta rodada. O commit anterior `80db24a` permanece como HEAD; as mudanças aqui descritas estão no working tree para revisão.

## 1. Migration adicional

`8d402b230000`, arquivo `backend/migrations/versions/8d402b_demo_isolation.py`, sucede `7c301a230000`. Adiciona `Clinic.is_demo` não nulo com default false e a tabela de limpeza recuperável `demo_media_cleanup`. Nenhum seed é executado pela migration.

Verificados upgrade/check/downgrade completo/upgrade/check em PostgreSQL descartável e upgrade/check no SQLite QA limpo. Aplicada também ao PostgreSQL local após backup, sem jobs ativos. As clínicas existentes permaneceram `is_demo=false`; zero clínicas demo foram criadas no banco clínico. Comparação por fingerprints de linhas confirmou preservação integral de 23 tabelas existentes, excluindo metadados de migration, sessões, tentativas de login e auditoria operacional. O backup continua privado na instância local, fora do Git/ZIP.

## 2. Arquivos alterados/adicionados

- `.env.example`
- `README.md`
- `backend/app/api_admin.py`
- `backend/app/api_video.py`
- `backend/app/core/access.py`
- `backend/app/core/config.py`
- `backend/app/core/security.py`
- `backend/app/demo_seed.py`
- `backend/app/main.py`
- `backend/app/models.py`
- `backend/app/reports.py`
- `backend/app/seed.py`
- `backend/app/storage.py`
- `backend/migrations/versions/8d402b_demo_isolation.py`
- `backend/requirements.txt`
- `backend/tests/test_demo.py`
- `compose.yaml`
- `docs/demo-environment.md`
- `docs/demo-release.md`
- `frontend/app/globals.css`
- `frontend/app/page.tsx`
- `frontend/components/AccessBlocked.tsx`
- `frontend/components/PatientForm.tsx`
- `frontend/components/PlatformAdmin.tsx`
- `frontend/e2e/demo.spec.ts`

## 3. Produção

O seed normal cria clínica administrativa, usuário e registros técnicos; não cria pacientes, avaliações ou mídias. O antigo `--demo` é recusado. As novas clínicas recebem is_demo=false. APP_MODE não muda permissões. As regras de segurança de ENVIRONMENT=production continuam exigindo PostgreSQL, HTTPS e cookies seguros. A instalação local continua restrita a localhost, sem certificação de uso clínico público decorrente desta rodada.

## 4. Demonstração

Clínica identificada no banco, usuário admin limitado ao próprio tenant, três pacientes sintéticos, três avaliações sem medidas automatizadas. Banner permanente, confirmação no cadastro e PDFs marcados no início e em cada rodapé. O histórico concluído declara explicitamente ausência de resultados clínicos. Sem CPF, telefone, endereço ou captura inventada. Demo não acessa plataforma global nem pode receber platform_admin. Acesso comercial dispensado por is_demo, respeitando suspensão e validade individual de usuários.

## 5. Comando exato para criar

No backend configurado para o banco escolhido:

```powershell
python -m alembic upgrade head
$env:APP_MODE = 'demo'
$env:ALLOW_DEMO_SEED = 'true'
python -m app.demo_seed --email demo@kinua.app
```

A senha é solicitada por prompt sem eco. Reexecução sem reset é idempotente e preserva a senha existente.

## 6. Comando exato para resetar

```powershell
$env:ALLOW_DEMO_SEED = 'true'
python -m app.demo_seed --email demo@kinua.app --reset
Remove-Item Env:ALLOW_DEMO_SEED
Remove-Item Env:DEMO_PASSWORD -ErrorAction SilentlyContinue
```

Use o e-mail do bootstrap original. Jobs demo pendentes/em andamento precisam terminar ou ser cancelados antes. O reset encerra sessões demo, substitui seus dados e mantém a clínica. Um e-mail inexistente cria outra demo, não seleciona a demo anterior.

## 7. Credenciais externas

Definir DATABASE_URL/POSTGRES_PASSWORD, senha do administrador via prompt ou BOOTSTRAP_PASSWORD, senha demo via prompt ou DEMO_PASSWORD e, para S3, S3_ACCESS_KEY_ID/S3_SECRET_ACCESS_KEY. Nenhum valor operacional está incluído no código/pacote. ALLOW_DEMO_SEED deve ser temporário e explícito.

Acesso local normal em http://127.0.0.1:3000. Demo de apresentação QA em http://127.0.0.1:8081, em banco SQLite separado; credenciais em `outputs/ACESSO-DEMO.md`, privado e fora deste repositório. Os serviços QA são locais e dependem dos processos iniciados nesta sessão. Para uso permanente ou duas URLs públicas, seguir demo-environment.md e as instruções de implantação existentes.

## 8. Testes finais

- Backend SQLite: 200 testes (178 anteriores + 22 novos).
- Backend PostgreSQL: 200 testes (178 anteriores + 22 novos).
- Frontend unitário: 6 testes.
- E2E: 13 fluxos (12 anteriores + demo); inferência real de webcam, foto e vídeo mantida.
- Ruff, imports/compileall, TypeScript, Prettier e build Next.js de produção verificados.
- PDF e tela demo inspecionados visualmente, além da extração da marca em todas as páginas.

O E2E demo foi iniciado em QA preparado de banco limpo: bootstrap global, clínica de controle, paciente controlado, seed demo, login, banner, dashboard, pacientes, início de avaliação, PDF, logout, badge/filtro global, exclusão comercial, reset e comparação dos pacientes da outra clínica. A confirmação de cadastro também é verificada com cancelamento sem criação de paciente.

## 9. Provas de isolamento

Testes comparam cada linha preexistente fora da demo após reset, inclusive storage de produção. Exercitam rollback após falha injetada, recusa de referência externa ao tenant, e-mail de conta real, platform_admin, chaves production/ e de outra demo, e travessia de diretórios. Reset S3 usa cliente controlado: falha na exclusão preserva fila, nova tentativa conclui limpeza e o objeto de produção permanece idêntico. APP_MODE nos três valores não concede administração global. Alterar is_demo via endpoint é recusado. PDFs de produção não recebem a marca.

## 10. Inspeção de arquivos sensíveis

Inspecionados arquivos rastreados e não ignorados candidatos ao Git, o ZIP anterior e o pacote de revisão. Busca por credenciais locais conhecidas e padrões de chaves; verificação de artefatos proibidos. Nenhuma correspondência de segredo operacional nos arquivos incluídos.

Encontrados somente fora da seleção de release: backend/.env, dados/mídias locais, bancos QA em work/, credenciais work/*credentials*.json, relatórios/screenshots E2E ignorados e arquivos privados outputs/ACESSO-LOCAL.md, outputs/ACESSO-PLATAFORMA.md e outputs/ACESSO-DEMO.md. Permanecem fora do Git e do ZIP. Backups do PostgreSQL também permanecem locais. Os nomes sintéticos são intencionais no seed explícito, testes e documentação; senhas de testes não são credenciais operacionais. Assets nativos de marca e catálogos versionados são preservados. Não foram apagados dados clínicos ou backups para “limpar” o release.

## 11. Limitações

- Validação técnica local não constitui validação clínica/regulatória, nem implantação de internet.
- Não houve teste em serviço S3 remoto: contrato e isolamento foram exercitados com cliente controlado; credenciais/bucket reais precisam de smoke test na implantação.
- Reset do banco é transacional; exclusão de objetos ocorre após commit com fila durável. Falha pode deixar mídia pendente: reexecutar SEM --reset.
- PostgreSQL oferece lock por clínica; SQLite de QA não tem a mesma garantia de concorrência. Não apresentar reset concorrente em SQLite como garantia de produção.
- Aviso e confirmação não detectam automaticamente dados reais. Usar somente material sintético/autorizado na demo.
- Demo não inclui medidas ou resultados biomecânicos pré-preenchidos.
- Avisos de depreciação de Starlette/httpx/AnyIO permanecem; não causaram falha nos testes. O build inicial encontrou pasta ocupada pelo servidor, resolvido encerrando o servidor local e reconstruindo.
- As verificações de segredos têm escopo explícito; não são uma certificação universal de ausência de dados sensíveis.

A rodada encerra na validação local e entrega para revisão. Nenhuma operação remota foi executada.
