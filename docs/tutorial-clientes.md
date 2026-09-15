# KINUA — tutorial para clientes

**Inteligência em movimento humano · Versão 2.3.0**

Guia para fisioterapeutas e administradores de clínica. Referência: auditoria de 14/09/2026. Os nomes de botões correspondem ao código desta versão; a publicação online pode apresentar diferenças.

> **Disponibilidade atual:** o fluxo de foto, revisão, histórico e PDF passou em testes online com dados fictícios. Vídeo e processamento ROM apresentaram falhas; Protocolos também possui pendências online. A liberação para atendimento com dados reais ainda está pendente. Use este tutorial para treinamento com dados fictícios até a comunicação formal de liberação.

## 1. Acessar sua conta

1. Abra o [KINUA](https://frontend-production-1acc.up.railway.app/) no navegador.
2. Preencha **E-mail** e **Senha** com o acesso individual fornecido pelo administrador.
3. Clique em **Entrar na plataforma**.
4. Confira se está na clínica e no ambiente corretos antes de cadastrar informações.

O administrador da clínica gerencia sua equipe. O fisioterapeuta usa os recursos de avaliação. O administrador global cuida de acessos e administração comercial: esse perfil não dá acesso automático a prontuários. Se aparecer somente o painel de gestão, solicite ao administrador um acesso clínico adequado.

Não há senha padrão neste guia. Não compartilhe sua conta. Em caso de esquecimento da senha ou acesso expirado, procure o administrador responsável. O guia não pressupõe uma opção de recuperação automática de senha.

Se houver identificação de **DEMO**, use exclusivamente informações fictícias. Dados inseridos no computador local não aparecem automaticamente na versão online.

## 2. Preparar a primeira avaliação

Use uma câmera estável, iluminação uniforme e espaço para enquadrar cabeça e pés. Evite contraluz e objetos cobrindo as articulações. Use roupas que permitam visualizar os segmentos avaliados.

O navegador precisa de autorização para abrir a câmera. Para acesso pela internet, use o endereço HTTPS. A interface se adapta a telas menores, mas a câmera física e cada dispositivo ainda precisam ser verificados antes do uso profissional.

Para aprender o fluxo, crie um cadastro claramente fictício, por exemplo **Paciente de treinamento**, com informações sintéticas. Não use prontuários reais para testar recursos.

## 3. Cadastrar um paciente

1. Abra **Pacientes** e escolha **Cadastrar paciente**.
2. Preencha **Nome completo** e **Data de nascimento**.
3. Complete, quando pertinente, dominância, contatos, profissão, prática esportiva, altura, peso, queixa e histórico.
4. Confira as informações e clique em **Cadastrar paciente**.
5. No perfil, use **Editar paciente** quando precisar corrigir o cadastro.

Informe apenas o necessário para a avaliação. Se o sistema avisar que outra pessoa alterou o registro, preserve suas anotações, reabra o cadastro atualizado e confira antes de reaplicar a mudança.

## 4. Criar uma avaliação

1. Abra o paciente correto e clique em **Avaliar paciente**.
2. Escolha o tipo e o modo de avaliação. Para o primeiro treinamento, use foto/câmera.
3. Clique em **Iniciar captura**.
4. Confira novamente a identificação do paciente antes de prosseguir.

O tipo organiza a avaliação; não representa um diagnóstico. Uma captura precisa de posição e enquadramento adequados ao que será medido.

## 5. Capturar ou enviar uma foto

1. Selecione a vista solicitada: anterior, posterior ou lateral correspondente.
2. Clique em **Abrir câmera** e autorize o navegador.
3. Aguarde os pontos e linhas sobre o corpo. Eles mostram a estimativa de posição corporal, não confirmam uma alteração clínica.
4. Ajuste o enquadramento e clique em **Capturar imagem**.
5. Para usar uma imagem existente, escolha **Enviar foto**. São aceitos JPEG, PNG e WebP.
6. Confira a imagem, o nivelamento e a vista. Marque as confirmações somente se estiverem corretas.
7. Clique em **Analisar e salvar captura** e aguarde o resultado.

Se a foto ficou inadequada, use **Refazer com câmera**. É possível acrescentar outras vistas antes de concluir a avaliação. Use **Desligar** para encerrar a câmera. Se a visualização ficar lenta, reduza a opção **Análise ao vivo**; isso não melhora, por si só, a precisão das medidas.

## 6. Entender e revisar os resultados

Confira a região, o lado, a unidade e a qualidade informada para cada medida. Um ângulo aparente em imagem 2D pode variar com a perspectiva e com o posicionamento da câmera.

- **Não mensurável:** não houve informação suficiente para apresentar aquela medida. Não interprete como zero ou normalidade.
- **Confiança/visibilidade:** indicador técnico da captura ou dos pontos detectados; não é probabilidade de diagnóstico nem garantia de precisão.
- **Registros para revisão:** pontos que precisam do julgamento do profissional. Use **Confirmar medida** ou **Descartar**, conforme sua análise.
- **Limitações e rastreabilidade:** explica restrições e identifica os métodos usados.

No mapa corporal, selecione uma região para consultar seus registros. Confirmar uma medida não confirma uma doença. Associe os resultados ao exame, histórico e testes pertinentes conduzidos pelo profissional.

## 7. Salvar e concluir

1. Em **Interpretação do fisioterapeuta**, registre **Observações** e **Conclusão profissional**.
2. Clique em **Salvar observações** e aguarde a confirmação.
3. Revise todos os registros antes de clicar em **Concluir avaliação**.

Concluir exige a revisão dos registros e uma conclusão preenchida. A avaliação concluída fica imutável. Para acompanhamento, crie outra avaliação; não tente substituir o resultado anterior.

## 8. Reabrir e baixar o relatório

1. Acesse **Histórico** e localize a avaliação do paciente.
2. Abra o registro e confira as capturas, medidas e observações salvas.
3. Clique em **Baixar relatório PDF**.
4. Confira paciente, data, conteúdo e conclusão antes de compartilhar pelo canal autorizado pela clínica.

O relatório utiliza informações salvas. Se houver alterações pendentes, salve-as antes de gerar o PDF. Arquivos baixados ficam no dispositivo: proteja-os e não os envie em canais públicos. O PDF é apoio à avaliação profissional, não um diagnóstico automático.

## 9. Protocolos de avaliação

**Recurso com pendências online.** O roteiro abaixo descreve o funcionamento implementado; não significa que todas as etapas estejam liberadas no ambiente público.

1. Abra **Protocolos** e escolha a **Categoria**.
2. Confira o **Paciente do protocolo** e clique em **Iniciar protocolo**.
3. Leia as instruções de cada etapa, registre observações e atualize o **Estado da etapa**.
4. Use **Salvar etapa** quando apresentado e aguarde a indicação de salvamento antes de sair.
5. Realize as capturas vinculadas e revise seus resultados. Só pule etapas quando o roteiro permitir, registrando a justificativa solicitada.
6. Preencha **Conclusão do protocolo** e conclua após atender aos requisitos das etapas.

O roteiro pode ser retomado pelo histórico. Se a seleção de paciente não estiver preenchida, confira-a manualmente antes de iniciar. Na versão online auditada, uma etapa que depende de ROM pode falhar; não marque uma etapa como realizada sem executá-la e revisá-la.

## 10. ROM — amplitude de movimento

**Processamento online pendente de correção e reteste.** Não use falhas ou resultados incompletos para fundamentar uma decisão clínica.

O módulo contempla flexão e abdução de ombro, flexão e extensão de cotovelo, flexão de quadril, flexão e extensão de joelho.

Quando liberado no seu ambiente:

1. Abra **ROM**, selecione **Paciente do ROM**, **Articulação e movimento** e **Lado do ROM**.
2. Clique em **Iniciar avaliação ROM**.
3. Siga as orientações de plano e vista; confirme o lado e o posicionamento antes da captura.
4. Realize o movimento conforme a orientação profissional, sem forçar amplitude para atender ao sistema.
5. Confira a série, o pico, a qualidade e a revisão antes de concluir.

Uma medida geométrica obtida pela câmera não substitui a avaliação de dor, capacidade funcional ou a comparação com um método de referência.

## 11. Vídeo e evolução

**Vídeo apresentou falha online na última auditoria.** A interface oferece **Gravar movimento** e **Enviar vídeo**, mas a presença desses controles não garante o processamento no ambiente atual. Em caso de falha, interrompa o teste e solicite suporte, sem repetir uploads indefinidamente.

Para acompanhar evolução, registre avaliações separadas e compare condições semelhantes: movimento, lado, vista e posicionamento. Uma diferença numérica não equivale automaticamente a melhora clínica. Compare também a qualidade das capturas e o contexto do exame. A evolução de vídeo/ROM online depende da resolução das pendências desses módulos.

## 12. Resolver dificuldades comuns

| Situação | Como proceder |
| --- | --- |
| Login recusado | Confira e-mail e senha. Evite tentativas repetidas; procure o administrador se persistir |
| Acesso expirado ou suspenso | Solicite ao administrador a revisão do acesso; não crie outra conta para contornar o bloqueio |
| Câmera não abre | Confira a permissão do navegador, o endereço HTTPS e se outro aplicativo está usando a câmera |
| Corpo não detectado | Melhore a iluminação, enquadre cabeça e pés e remova obstruções |
| Medida indisponível | Confira vista, lado e qualidade; repita a captura se necessário |
| Falha ao salvar | Mantenha suas anotações, confira a conexão e verifique no histórico se houve salvamento antes de duplicar o registro |
| Conflito de edição | Preserve seu texto e reabra a versão atual para conciliar as alterações |
| Vídeo/ROM falha ao processar | Registre horário e mensagem e encaminhe ao suporte; o ambiente possui pendência conhecida |
| PDF não reflete uma edição | Salve as observações e gere novamente |
| Paciente não aparece | Confira o ambiente e a conta da clínica; solicite ajuda sem tentar acessar outra clínica |

Ao solicitar suporte, informe a tela, a ação, o horário, o navegador e a mensagem de erro. Nunca envie sua senha. Remova nomes, imagens, documentos e demais informações de pacientes de qualquer captura de tela enviada.

## 13. Encerrar o uso

Confirme o salvamento e desligue a câmera. Clique em **Sair**, principalmente em computadores compartilhados. Proteja os relatórios baixados conforme as orientações da clínica.

Para responsáveis técnicos, o [estado atual do sistema](estado-atual.md) reúne arquitetura, verificação e pendências. Este tutorial orienta a operação; não substitui capacitação clínica nem autoriza o uso de recursos ainda não liberados.
