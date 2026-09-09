# Avaliação de prontidão para uso clínico pela internet

Data: 09/09/2026. Base inspecionada: commit `4cfd47c`, com correções desta auditoria na API 2.0.1. Responsável clínico indicado pelo solicitante: **Ruan Rocha**. Métodos disponíveis informados: análise de movimento e testes ortopédicos, ainda sem especificação quantitativa/instrumental. Indicação não equivale a aprovação, assinatura ou verificação de registro profissional.

## Decisão atual: NÃO LIBERADO PARA USO ASSISTENCIAL PELA INTERNET

Esta é uma avaliação técnica parcial, não um certificado, autorização sanitária, parecer jurídico ou validação clínica. O funcionamento de uma aplicação e a correção da geometria não demonstram que os landmarks correspondem aos pontos anatômicos pretendidos, nem que as medidas são suficientemente precisas para decisões clínicas. Não foram apresentados dados pareados com referência clínica, instrumentos, protocolo aprovado ou critérios clínicos de aceitação.

A aplicação continua local. Não foram publicados serviços nem alterados firewall, criptografia do Windows, contas ou permissões de pacientes. Os testes desta auditoria usam bancos/schemas e arquivos temporários; nenhum paciente fictício foi reinserido no banco da aplicação.

## Evidências de engenharia

| Verificação | Resultado e limite |
|---|---|
| Regressão SQLite | 51 testes passaram; API, acesso, geometria, revisão, arquivos, vídeo, fila, PDF e comparação |
| Regressão PostgreSQL 18.4 | Os mesmos 51 testes passaram em schemas temporários |
| Testes novos antes das correções | 3 falhas reproduzidas: perda de conteúdo em PATCH e aceitação de mídia substituída em visualização/PDF |
| Regressão de integridade | Inclui corrupção com tamanho diferente e com o mesmo tamanho |
| Referência matemática construída | Ângulos de 1° a 179°, três escalas e espelhamento, tolerância numérica de 1e-8°; não é tolerância clínica |
| Configuração de produção | Recusa cookie não Secure, origem HTTP e SQLite; não instala certificado nem valida infraestrutura |
| Análise estática | `ruff check app tests --select F`: passou |
| Esquema | `alembic check`: sem divergência; nenhuma nova migration necessária |
| Exposição observada | Portas 3000, 8000 e 55432 vinculadas a 127.0.0.1 |
| Verificação local após atualização | API 2.0.1 responde; acesso sem sessão negado; login/logout e Cache-Control no-store verificados; 0 pacientes e 0 avaliações |
| Disco local | `manage-bde -status C:`: 0% criptografado, proteção BitLocker desativada |
| Backup/restauração | Sem recuperação operacional comprovada; pacote PostgreSQL local não inclui pg_dump/pg_restore |
| Navegador | A entrega v2 tinha 4 testes E2E aprovados; eles não foram repetidos contra o banco limpo para evitar recriar dados de demonstração |
| Dependências | Auditorias da entrega v2, nesta mesma data, não apontaram vulnerabilidades conhecidas; dependências não mudaram nesta auditoria |

Resultados brutos desta sessão: `work/clinical-readiness-before.xml`, `work/clinical-readiness-after-sqlite.xml` e `work/clinical-readiness-after-postgres.xml`, fora do repositório. Todos contêm somente dados sintéticos de teste. Os testes reprodutíveis estão em `backend/tests/test_readiness.py` e na suíte existente.

## Correções implementadas

Um resumo por caso de teste, sem dados pessoais ou credenciais, acompanha o repositório em `validation/engineering-evidence.json`.

1. PATCH de avaliação preserva notas, conclusão e estado quando o campo não é enviado. Uma conclusão já salva pode ser usada ao concluir sem ser apagada por valores padrão.
2. Leitura de mídia, processamento e geração de PDF verificam tamanho e SHA-256. Divergência impede usar o arquivo com medidas antigas. O worker registra falha de integridade.
3. A análise de foto obtém bloqueio transacional da avaliação, alinhando-a à conclusão/revisão e evitando uma leitura de estado sem bloqueio nessa operação.
4. `ENVIRONMENT=production` exige PostgreSQL, `SECURE_COOKIES=true` e origens HTTPS explícitas. Esse rótulo é configuração técnica, **não um indicador de aprovação clínica**.

O hash não protege contra um administrador de host que altere simultaneamente banco e arquivo, nem elimina a possibilidade de troca entre verificação e uso por alguém com acesso ao sistema de arquivos. A conferência integral adiciona leitura de disco, especialmente em vídeos e requisições Range; desempenho sob carga externa permanece a testar.

## Bloqueios de liberação

| ID | Bloqueio observado ou evidência ausente | Condição para encerrar |
|---|---|---|
| CL-01 | Sem validação das medidas e fases na população pretendida | Ruan aprovar protocolo, referência, critérios prévios e resultados por medida/protocolo; ver documento de protocolo |
| CL-02 | Perspectiva e nivelamento não medidos automaticamente; visibility não é erro/precisão | Caracterizar erro e falhas por vista, câmera, posicionamento, oclusão e população; definir quando recusar resultado |
| SEC-01 | Hospedagem/domínio/TLS de produção não definidos ou testados | Ambiente de homologação com HTTPS real, cookies seguros, origem restrita, portas internas protegidas e teste externo autorizado |
| SEC-02 | Ausência de MFA, desativação de usuário, revogação administrativa e troca/recuperação de senha completas | Gestão de ciclo de acesso, contas individuais, segundo fator ou controles equivalentes justificados e testes de revogação |
| SEC-03 | Dados/segredos locais sem proteção de disco confirmada; C: sem BitLocker | Política de chaves, armazenamento e backups criptografados, permissões mínimas e teste de recuperação no ambiente escolhido |
| OPS-01 | Sem backups automáticos, restauração ensaiada ou metas de recuperação | Restaurar banco e mídias consistentes em ambiente separado, verificar hashes/relações e medir perda/tempo conforme metas acordadas |
| OPS-02 | Sem carga, quota global de arquivos/jobs ou monitoração de produção validadas | Definir usuários simultâneos, limites/alertas de disco/fila e testar saturação, indisponibilidade e recuperação |
| DATA-01 | Landmarks de foto são informados pelo cliente; não há prova independente de correspondência à imagem | Avaliar processamento/verificação confiável no servidor e validar associação imagem–landmarks; manter proveniência auditável |
| GOV-01 | Finalidade, base legal, retenção, operadores, atendimento a titulares e incidentes ainda não definidos para a clínica | Inventário de dados, responsabilidades, políticas e procedimentos implementados e revisados |
| REG-01 | Enquadramento sanitário e obrigações aplicáveis ainda não determinados | Avaliação formal da finalidade e distribuição, documentação exigível e regularização/justificativa aplicável |

As prioridades acima são critérios de liberação deste projeto. Não significam que toda tecnologia citada seja uma obrigação legal isolada ou suficiente para conformidade.

## Observações clínicas e regulatórias

A finalidade declarada inclui medidas para avaliação/reabilitação e apoio à decisão. Minha inferência é que o enquadramento como SaMD precisa ser avaliado; o aviso “não fornece diagnóstico” não resolve sozinho essa questão. Não atribuí classe de risco, dispensa in house ou aprovação. Consultar a documentação oficial da [Anvisa sobre SaMD](https://www.gov.br/anvisa/pt-br/centraisdeconteudo/publicacoes/produtos-para-a-saude/manuais/software-como-dispositivo-medico-perguntas-e-respostas) e a [página regulatória de dispositivos médicos](https://www.gov.br/anvisa/en/regulation-of-products/medical-devices).

Imagens, vídeos e informações de saúde identificáveis exigem governança de dados e controles técnicos e administrativos. Usar um código no lugar do nome não anonimiza automaticamente rosto, corpo ou vídeo. A [orientação da ANPD sobre segurança da informação](https://www.gov.br/anpd/pt-br/centrais-de-conteudo/materiais-educativos-e-publicacoes/guia-orientativo-sobre-seguranca-da-informacao-para-agentes-de-tratamento-de-pequeno-porte) oferece guia, checklist e modelo de registro de operações. Nenhuma política ou base legal foi presumida como aprovada pela clínica.

## Próxima decisão verificável

Separar a homologação técnica pela internet do estudo de precisão clínica. Primeiro fechar ambiente, acesso, proteção/recuperação e governança. Em paralelo, Ruan precisa definir método/instrumento de referência, medidas prioritárias, população e tolerâncias antes de coletar resultados. A aprovação futura deverá registrar versão, ambiente, evidências, limites de uso, responsáveis e data; não é obtida apenas alterando uma variável de ambiente.
