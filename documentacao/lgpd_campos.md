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

- **Mascaramento antes do envio:** CPF, RG, e-mail e telefone viram `[CPF removido]` etc. (`privacidade.mascarar_antes_de_enviar` no `config.json`). Na transcrição, os dígitos ditados um a um são juntados antes, porque separados ("1 2 3 4 5 6 7 8 9 - 0 0") escapariam do padrão. O telefone do caso `texto-injection`, (65) 99888-7766, também é fictício. Na rodada de 31/10/2026, `texto-01` e `audio-01` tiveram CPF, RG e e-mail mascarados; `texto-injection`, CPF e telefone; `imagem-01`, CPF, RG e e-mail nas execuções em que o CPF foi lido inteiro. O texto original fica só na máquina local, em `dados/processados/`.
- **Sem armazenamento no provedor:** as chamadas de texto e visão (Responses API) usam `store=False`; transcrição, voz e imagem não têm esse parâmetro.
- **Log sem conteúdo:** `resultados/logs/execucoes.jsonl` guarda caminhos, versões e hashes, não o texto. Os trechos incertos e os dados críticos não encontrados, que vão para os extras do log, passam pelo mesmo mascaramento do envio. Na rodada de 31/10/2026, três eventos anteriores a esse ajuste (as confirmações e uma comparação do `imagem-01`) registraram o CPF fictício da ficha.
- **Sem credenciais:** a chave fica só no `.env`, fora do git. A varredura do repositório, das saídas e do histórico de commits, feita em 31/10/2026, não encontrou a chave nem o `.env`.
- **Minuta mínima:** a minuta recebe só os campos do pedido; CPF, RG, filiação e contatos não chegam a ela.

## Riscos residuais

- Data de nascimento, filiação e naturalidade não são mascaradas: os padrões cobrem só formatos fixos (CPF, RG, e-mail, telefone). Num cenário real, a extração deveria receber só os trechos necessários ao pedido.
- Imagem e áudio não podem ser mascarados antes do envio: o documento e a voz vão inteiros ao provedor. Ver `visao_e_imagem.md` sobre quando o processamento local seria preferível.
- O OCR pode ler um dado pessoal só em parte: na execução `5270cc7d02bb` do `imagem-01`, o CPF veio como `123.456.[ilegível]00`, forma que o padrão de CPF não reconhece, e foi ao provedor na etapa de extração sem máscara (dado fictício).
- Pela API, a OpenAI não usa os dados enviados para treinar modelos por padrão, mas guarda registros por até 30 dias para monitoramento de abuso (fonte: docs oficiais OpenAI API, your-data, out/2026). Com dados reais, seria preciso avaliar o contrato, a retenção e a residência de dados antes do uso.
