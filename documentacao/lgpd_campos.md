# LGPD, privacidade e minimização (RF12)

Todos os dados do desafio são fictícios. A tabela mostra o que cada campo seria num cenário real, para que serve no atendimento e como o protótipo trata.

## Campos

| Campo | Dado pessoal num cenário real? | Finalidade | Necessário para a resposta? | Risco | Tratamento no protótipo |
|---|---|---|---|---|---|
| Nome do solicitante | Sim, identifica a pessoa | Identificar o interessado | Sim | Médio | Vai ao provedor; aparece na minuta; conferido por humano em áudio e imagem |
| CPF | Sim, identificador único | Identificação civil | Não | Alto: fraude e cruzamento de bases | Mascarado antes do envio no texto; não entra na minuta |
| RG | Sim | Identificação civil | Não | Alto | Mascarado antes do envio no texto; não entra na minuta |
| E-mail | Sim | Canal de resposta | Só para enviar, o que o protótipo não faz | Médio | Mascarado antes do envio no texto |
| Telefone | Sim | Canal de resposta | Só para enviar | Médio | Mascarado antes do envio no texto |
| Data de nascimento | Sim; indica menoridade | Verificar idade | Não | Médio: com o nome, identifica e expõe menor de idade | **Não mascarado**: vai ao provedor; não entra na minuta |
| Nome da mãe e do pai | Sim; usado para validar identidade | Identificação civil | Não | Alto: usado em fraudes de identidade | **Não mascarado**: vai ao provedor; não entra na minuta |
| Naturalidade | Sim, quase-identificador | Cadastro | Não | Baixo | Não mascarado |
| Curso, eixo, turno, carga horária | Sim, quando ligados à pessoa | Objeto do pedido | Sim | Baixo | Vai ao provedor e à minuta |
| Datas de matrícula e de início | Sim, quando ligadas à pessoa | Contexto do pedido | Sim | Baixo | Vai ao provedor e à minuta |
| Protocolo | Indireto: aponta para a pessoa | Rastrear a demanda | Sim | Baixo | Vai ao provedor e à minuta |
| Assinatura manuscrita (imagem) | Sim | Validar o documento | Não | Médio | Vai ao provedor dentro da imagem; o OCR só marca `[assinatura]` |
| Voz (áudio) | Sim; pode identificar a pessoa | Transcrição | Sim, no canal de voz | Alto | Vai ao provedor dentro do áudio |

## Medidas aplicadas

- **Mascaramento antes do envio:** CPF, RG, e-mail e telefone viram `[CPF removido]` etc. (`privacidade.mascarar_antes_de_enviar` no `config.json`). Na transcrição, os dígitos ditados um a um são juntados antes, porque separados ("1 2 3 4 5 6 7 8 9 - 0 0") escapavam do padrão: na primeira rodada real do `audio-01`, só o e-mail tinha sido mascarado. Na rodada real, `texto-01` teve CPF, RG e e-mail mascarados, e `texto-injection`, CPF e telefone. O texto original fica só na máquina local, em `dados/processados/`.
- **Sem armazenamento no provedor:** todas as chamadas usam `store=False`.
- **Log sem conteúdo:** `resultados/logs/execucoes.jsonl` guarda caminhos, versões e hashes, não o texto.
- **Sem credenciais:** a chave fica só no `.env`, fora do git. A varredura do repositório, das saídas e do histórico de commits não encontrou a chave nem o `.env`.
- **Minuta mínima:** a minuta recebe só os campos do pedido; CPF, RG, filiação e contatos não chegam a ela.

## Riscos residuais

- Data de nascimento, filiação e naturalidade não são mascaradas: os padrões cobrem só formatos fixos (CPF, RG, e-mail, telefone). Num cenário real, a extração deveria receber só os trechos necessários ao pedido.
- Imagem e áudio não podem ser mascarados antes do envio: o documento e a voz vão inteiros ao provedor. Ver `visao_e_imagem.md` sobre quando o processamento local seria preferível.
- Na camada gratuita do Gemini, o conteúdo enviado é usado para melhorar os produtos do Google; na paga, não (fonte: docs oficiais Gemini API, pricing, out/2026). Em 18/10/2026, os casos de texto, a primeira leitura do `imagem-01` e o experimento de prompts rodaram na camada gratuita, só com dados fictícios; a partir das 16h10 (peça visual e execuções finais do `imagem-01`), o projeto já estava na camada paga. Com dados reais, a camada paga, ou outro arranjo contratual, seria obrigatória.
