# KINUA — tutorial para clientes

**Inteligência em movimento humano · Versão 2.3.0**  
**Atualizado:** 16/09/2026

Guia operacional para fisioterapeutas e administradores de clínica. O estado técnico atual está em [`estado-atual.md`](estado-atual.md). Testes de engenharia não substituem capacitação profissional nem validação clínica.

## 1. Acessar sua conta

1. Abra o KINUA pelo endereço HTTPS fornecido pela clínica.
2. Preencha **E-mail** e **Senha** individuais.
3. Clique em **Entrar na plataforma**.
4. Confira se está na clínica e no ambiente corretos.

O administrador da clínica gerencia sua equipe. O fisioterapeuta utiliza os recursos clínicos. O administrador global cuida de acesso/comercial e não recebe acesso automático aos prontuários.

Ainda não existe recuperação automática de senha. Em caso de esquecimento, procure o administrador responsável. Não compartilhe credenciais.

Se houver identificação de **DEMO**, use exclusivamente informações fictícias.

## 2. Preparar a avaliação

Use câmera estável, iluminação uniforme e espaço para enquadrar os segmentos necessários. Evite contraluz e oclusões. Câmera no navegador exige HTTPS ou localhost e permissão do dispositivo.

A interface é responsiva e o fluxo foi testado com câmera virtual/fixtures. Antes de uso profissional em um dispositivo específico, confira câmera, orientação, desempenho e formato de vídeo nesse aparelho.

## 3. Cadastrar paciente

1. Abra **Pacientes** → **Cadastrar paciente**.
2. Preencha nome e data de nascimento.
3. Complete apenas as informações pertinentes.
4. Salve e confira o perfil.
5. Use **Editar paciente** para correções futuras.

Se houver conflito de edição, preserve suas anotações, recarregue a versão atual e concilie antes de reenviar.

## 4. Criar uma avaliação

1. Abra o paciente.
2. Clique em **Avaliar paciente**.
3. Escolha tipo/modo apropriado.
4. Inicie a captura.

O tipo organiza o registro; não representa diagnóstico.

## 5. Foto ou câmera

1. Selecione a vista correta.
2. Para câmera, clique em **Abrir câmera** e autorize o navegador.
3. Ajuste corpo/enquadramento e observe o skeleton como guia técnico.
4. Capture ou use **Enviar foto** (JPEG, PNG ou WebP).
5. Confirme nivelamento e vista somente quando corretos.
6. Clique em **Analisar e salvar captura**.

Os landmarks são estimativas do modelo e não confirmam alteração clínica.

## 6. Revisar resultados

- **Não mensurável:** informação insuficiente; não significa zero/normalidade.
- **Visibilidade/qualidade:** indicador técnico do landmark/captura, não probabilidade diagnóstica.
- **Revisão profissional:** confirme ou descarte cada registro conforme avaliação clínica.
- **Limitações:** considere perspectiva, posicionamento, roupa e oclusão.

O mapa corporal é navegação/agrupamento; não marca estruturas “doentes”.

## 7. Salvar e concluir

1. Registre observações e conclusão profissional.
2. Salve e aguarde confirmação.
3. Revise registros pendentes.
4. Clique em **Concluir avaliação**.

Avaliação concluída é preservada como histórico. Para evolução, crie nova avaliação.

## 8. PDF e histórico

1. Abra **Histórico**.
2. Reabra a avaliação desejada.
3. Confira capturas, medidas, revisões e conclusão.
4. Baixe o PDF.

Proteja o arquivo baixado como dado de saúde. Não use canais públicos/não autorizados para compartilhamento.

## 9. Protocolos

Assessment Protocols estão implementados e integrados ao fluxo atual.

1. Abra **Protocolos** e escolha categoria/paciente.
2. Inicie o protocolo.
3. Preencha cada etapa, observação e estado.
4. Salve antes de avançar quando solicitado.
5. Execute as capturas/ROM vinculadas e revise as avaliações filhas.
6. Pule apenas etapas que permitam isso e registre justificativa.
7. Preencha a conclusão e finalize quando os requisitos forem atendidos.

Algumas etapas do catálogo podem ser deliberadamente textuais ou indisponíveis (por exemplo, recursos ainda não implementados); isso deve aparecer como limitação explícita, não como resultado simulado.

## 10. ROM

KINUA ROM contempla sete movimentos: flexão/abdução de ombro, flexão/extensão de cotovelo, flexão de quadril e flexão/extensão de joelho.

1. Abra **ROM** ou entre por uma etapa ROM do protocolo.
2. Selecione paciente, movimento e lado.
3. Siga a orientação de plano/vista.
4. Grave o movimento ou envie vídeo compatível.
5. Confira série, pico, qualidade e revisão.
6. Conclua somente após revisão profissional.

ROM do KINUA é geometria 2D baseada em landmarks e ainda requer validação contra referência clínica/instrumental antes de afirmações de equivalência à goniometria.

## 11. Vídeo e evolução

Vídeo e worker estão operacionais no estado atual verificado. A plataforma aceita:

- MP4;
- WebM;
- MOV/QuickTime quando conteúdo/codec são decodificáveis;
- máximo padrão de 100 MiB e 60 s.

A gravação pelo navegador não solicita microfone. Vídeos enviados da biblioteca podem conter áudio/metadados originais; eles permanecem privados e não são usados na inferência.

Arquivos MOV foram validados tecnicamente. **HEVC/H.265 de iPhone ainda depende do dispositivo/decoder e não deve ser presumido universalmente compatível.** Se um vídeo falhar, registre formato, aparelho, navegador, horário e mensagem para suporte; evite uploads repetidos sem diagnóstico.

Para evolução, compare condições equivalentes de protocolo, lado, vista, câmera e posicionamento. Diferença numérica não significa automaticamente melhora clínica.

## 12. Problemas comuns

| Situação | Como proceder |
|---|---|
| Login recusado | confira credenciais; não faça tentativas repetidas; procure o administrador |
| Acesso ainda não iniciou | confirme a data individual/comercial com o administrador |
| Acesso expirado/suspenso | solicite regularização; não crie conta paralela |
| Câmera não abre | confira HTTPS, permissão e uso por outro app |
| Corpo não detectado | melhore iluminação/enquadramento e reduza oclusões |
| Medida indisponível | confira vista, lado, plano e qualidade; recapture se necessário |
| Conflito de edição | preserve o texto e reabra a versão atual |
| Vídeo incompatível | tente MP4/WebM ou MOV decodificável; informe codec/dispositivo ao suporte |
| Job demora/falha | não duplique avaliação; reabra o histórico e confira estado do job |
| PDF não reflete edição | confirme que observações foram salvas antes de gerar novamente |
| Paciente não aparece | confira clínica/ambiente; não tente acessar outro tenant |

Ao pedir suporte, envie IDs/tela/horário/navegador e mensagem sanitizada. Nunca envie senha, cookie, dump de prontuário ou mídia clínica sem canal autorizado.

## 13. Encerrar

Confirme salvamento, desligue a câmera e clique em **Sair**, principalmente em computador compartilhado. Proteja relatórios e downloads conforme a política da clínica.

## Nota de prontidão

Infraestrutura, vídeo/worker, S3 e restore já possuem evidência técnica atual. **Validação clínica, governança LGPD e avaliação regulatória permanecem separadas e pendentes.** Consulte [`clinical-readiness.md`](clinical-readiness.md).
