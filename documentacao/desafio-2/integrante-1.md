# Integrante 1 — Dados, RF14 e RF15

Implementado em 31/10/2026, validado com a API real em 01/11/2026 UTC
(31/10 à noite em Cuiabá), na branch `feat/desafio2-integrante1-dados-nlp`.
O acervo é inteiramente fictício, inspirado apenas nos temas de matrícula e
retificações dos editais fornecidos. Suas regras não são oficiais. Os originais
do Desafio 1 e os contratos compartilhados foram preservados.

## Arquitetura e integração

`nlp.extrair_solicitacao` → `SolicitacaoEstruturada` → `nlp.validar_regras` →
`nlp.compreender` → `FichaCompreensao`. O esquema permanece em versão 2.0.
Nenhuma destas funções gera ou envia uma minuta.

Todas as chamadas usam `ClienteLLM.gerar`, o perfil de `Config.perfil_geracao`,
`formato_json` e o novo sistema seguro do Desafio 2. O sistema do Desafio 1
permanece intacto: sua regra de ausência como string era incompatível com null. Assim permanecem no
adaptador único `store=False`, timeout, repetição transitória, contabilização de
tokens, custo e latência. Mascaramento e ocultação de formatos de chave são
aplicados antes do envio, inclusive à solicitação estruturada da compreensão.
Entradas e origem passam por `prompts.delimitar`, neutralizando tags falsas.

O `Resultado` guarda valor, respostas do provedor e prompt (identificador/hash).
Na falha definitiva de validação, `RespostaMalformada` também disponibiliza
`respostas` e `prompt` para auditoria. Seu detalhe traz apenas tipos/localização
de erros e mensagens de regras, sem reproduzir valores inválidos. Falhas do
provedor continuam como subclasses de `ErroLLM`, sem disparar reparo de JSON.

Prompts ativos: `solicitacao_d2_v4.md`, `compreensao_d2_v3.md`,
`verificar_resumo_d2_v1.md` e `sistema_seguro_d2_v1.md`. Versões anteriores
foram preservadas, inclusive as utilizadas nas primeiras chamadas reais.
Perfil alternativo não altera dados nem índice. O schema compartilhado 2.0
e todas as assinaturas continuam compatíveis; o verificador usa um tipo interno.

## Base e gabaritos prévios

O commit `40859a5` registra a base validada antes da implementação do NLP e de
qualquer chamada ao modelo. As respostas simuladas foram escritas previamente
em `testes/referencias_nlp.py`; não foram obtidas de serviço real.
O catálogo de caminhos fica em `dados/originais/desafio-2/casos.json`.

| ID | Arquivo / conteúdo | Versão e vigência |
|---|---|---|
| DOC-01 | doc-01.txt, matrícula histórica | 1.0; 01/09 até 09/10/2026 |
| DOC-02 | doc-02.txt, matrícula vigente, substitui DOC-01 integralmente | 2.0; desde 10/10/2026 |
| DOC-03 | doc-03.pdf, PDF textual de documentos escolares, uma página | 1.0; desde 01/09/2026 |
| DOC-04 | doc-04.txt, cancelamento | 1.0; desde 01/09/2026 |
| DOC-05 | doc-05.txt, atendimento | 1.0; desde 01/09/2026 |
| DOC-06 | doc-06.txt, anexo adversarial identificado como não confiável | 1.0; artefato de teste desde 01/09/2026 |

Todos estão no manifesto `dados/acervo/acervo.json`, validado por
`ingestion.ler_manifesto`. Há três temas e dois formatos. As passagens usadas
nas perguntas cabem nos chunks A/B existentes; a recuperação efetiva é avaliada
pelo Integrante 2. No PDF, a conferência literal normaliza somente espaços e
quebras de linha inseridas pelo extrator, sem alterar palavras ou pontuação.

| Solicitação | Tipo | Categoria esperada / particularidade |
|---|---|---|
| D2-S01 | completa | matricula; cópia exata do texto revisado do áudio |
| D2-S02 | completa | solicitacao_documentos; emissão de declaração |
| D2-S03 | completa | cancelamento |
| D2-S04 | completa | reclamacao |
| D2-S05 | incompleta | matricula; OCR copiado, protocolo ilegível e pedido ausente |
| D2-S06 | ambígua | revisao na execução atual; null no gabarito histórico preservado |

Entradas estão em `dados/originais/desafio-2/D2-S*.txt`; gabaritos em
`dados/gabaritos/D2-S*.json`. Cada gabarito tem campos presentes/ausentes,
entidades, fatos essenciais, justificativa, resumo de referência e decisão
esperada. Áudio e OCR têm referência ao arquivo revisado e SHA-256 da origem;
a validação confere igualdade dos bytes. Não se completa o protocolo do OCR
com a transcrição do áudio. Pessoas e identificadores destes casos anteriores
são fictícios, conforme a documentação do Desafio 1.

`fontes_esperadas` das solicitações (trecho do acervo que a minuta RAG deve
citar) foi preenchido pelo Integrante 2 depois da avaliação RF14/RF15 e antes
de qualquer minuta RAG; o campo `fontes_esperadas_elaboradas_por` registra
isso. Nenhum outro campo dos gabaritos mudou. S05 e S06 não têm pedido
decidido: as fontes indicam a orientação geral (documentos da matrícula e
encaminhamento de dúvida à revisão), não uma resposta ao cidadão.

| Pergunta | Resultado esperado |
|---|---|
| D2-R01 | Documentos da matrícula, DOC-02 |
| D2-R02 | Local de solicitação de declaração, DOC-03 |
| D2-R03 | Prazo da declaração, DOC-03 |
| D2-R04 | Procedimento de cancelamento, DOC-04 |
| D2-R05 | Horário de atendimento, DOC-05 |
| D2-R06 | Sem evidência: valor de bolsa |
| D2-R07 | Sem evidência: emissão individual já concluída |
| D2-R08 | Divergência 20/10 × 30/10; DOC-02 prevalece em 15/10/2026 |

`D2-R*.json` contém pergunta, resposta/status esperados, critério, documentos,
versões e citações literais. R08 espera `fundamentada` **se** a regra de
substituição for recuperada; caso contrário, `conflito` e revisão. A seção 6
permite prioridade explícita resolver fontes contraditórias. Não inventar IDs
de chunks: após indexar, localizar os chunks que contenham as referências e
registrar seus IDs reais, hash, página/seção e perfil A/B.

`dados/avaliacoes/avaliacoes.json`: AV-01 a AV-03 positivas, AV-04 a AV-06
negativas, AV-07 a AV-09 neutras, AV-10 a AV-12 indeterminadas. O gabarito
`D2-sentimentos.json` justifica cada rótulo. Ironia, falta de contexto e aspectos
opostos sem predominância exigem indeterminação e revisão. Não usar confiança
como probabilidade nem inferir características do autor.

Ataques `D2-A01` (solicitação), `D2-A02` (trecho literal de DOC-06) e `D2-A03`
(pedido de segredos) estão nos respectivos gabaritos. Esperam bloqueio ou
revisão, sem executar comandos, consultar `.env`, aprovar ou enviar respostas.
Não contêm credenciais. A implementação das camadas de guardrails é do
Integrante 3; preparar esses casos não comprova resistência de um modelo real.

## RF14 — esquema e regras

O JSON passa por parser que rejeita sintaxe inválida, constantes não JSON e
chaves duplicadas; depois por `SolicitacaoEstruturada.model_validate_json`.
Pydantic estrito rejeita campos extras, obrigatórios omitidos e coerções como
`"true"` para booleano. `null` é mantido; não são criados defaults para fatos.
Ausência de uma chave obrigatória é erro; ausência de informação é chave null.

Há no máximo duas gerações (original + um reparo), inclusive para regras de
negócio. O reparo recebe diagnóstico seguro delimitado e a entrada original
mascarada, nunca a saída inválida como instrução. Falha persistente gera
`RespostaMalformada` e impede continuação. Não há correção silenciosa de fatos.

Regras locais bloqueiam categoria fora da configuração; strings vazias ou
sentinelas em lugar de null; lista de ausências diferente dos campos null,
duplicada ou com nomes estranhos; ausência sem revisão; revisão sem motivo;
protocolo fora de `aaaa-nnnnnn`, abreviado ou ausente do original; protocolo
ilegível em entidades; data null apesar de estar rotulada no original; nome,
assunto, pedido e entidades sem suporte literal; datas inexistentes, inválidas
ou não sustentadas. Datas aceitam `dd/mm/aaaa`, ISO e mês por extenso em
português. Em formulário, DATA MATRÍCULA identifica a data do documento. A data
rotulada da solicitação ou ligada ao protocolo prevalece
sobre nascimento e datas do curso. Não há validação por relógio: datas futuras
em documentos não são automaticamente erros. A regra de categoria de emissão
explícita de declaração/histórico/certificado/documento bloqueia confusão com
efetivação de matrícula. A categoria revisao exige necessita_revisao=true.
Data impossível no próprio original é apontada uma vez ("o original contém data
impossível") e não faz a data extraída, se válida, ser dada como inexistente.
Pedidos múltiplos podem reunir passagens literais com ` … `, cada uma validada
contra o original; não se descarta o pedido adicional de esclarecimento.

Exemplo de D2-S02: protocolo `2026-000201`, data `15/10/2026`, solicitante
`Lia Exemplo`, pedido `Solicito emissão de declaração de matrícula.`, categoria
`solicitacao_documentos`, ausências `[]`. No OCR, protocolo/pedido são null,
ausências `["protocolo", "pedido"]`, com revisão e motivo explícitos.

`comparar_sintatico_e_esquema` faz duas chamadas independentes, sem reparo:
mesmo conteúdo e contrato descrito, com/sem restrição do provedor. Diagnostica
`json_valido`, `esquema_valido`, `campos_obrigatorios_ausentes`,
`tipos_incorretos`, `campos_extras` e `outros_erros`. Registra separadamente
saída mascarada, modelo, tokens, custo e duração. A comparação simulada inclui
JSON sintaticamente válido com `pedido` omitido, booleano string e chave extra:
a abordagem livre é recusada pelo esquema; a resposta simulada da abordagem
restrita é válida. Isso demonstra o detector, sem provar superioridade empírica
de uma abordagem. Esquema válido não comprova verdade: regras são outra etapa.

## RF15 — resumo, classificação e entidades

Categoria e entidades pertencem exclusivamente à `SolicitacaoEstruturada`.
A ficha só admite resumo e inferências. O resumo pode parafrasear o original,
com no máximo 100 palavras. Texto vazio, esquema inválido, reprodução de dados
pessoais, protocolos sem suporte e inferências sem justificativa são recusados.
Passagens literais podem ser conferidas localmente. Para paráfrases há uma
segunda chamada, delimitada e com esquema estrito, que confere cada afirmação,
negação, relação e modalidade contra o original e a solicitação. Seu veredito
precisa ser favorável, sem fatos sem suporte, com justificativa e evidências
literais existentes no original. Evidência inexistente ou verificador inválido
bloqueia a ficha. Ambas as respostas entram em Resultado e no consumo.

O verificador é outro uso do mesmo modelo, sujeito a erros e vieses correlacionados;
não substitui revisão humana. A seleção de trechos literais também pode perder
contexto, portanto não é garantia de fidelidade semântica. As inferências ficam
separadas e justificadas, sem substituir campos estruturados. A necessidade de
esclarecimento de uma intenção ambígua é consequência operacional da revisão,
não uma nova ação institucional ou fato sobre o cidadão.

A lista configurada agora contém **revisao**, de forma aditiva às cinco categorias
anteriores. Não houve alteração em schemas.py ou no formato das mensagens
compartilhadas. Dados legados com categoria null continuam válidos. revisao é
usada para intenção ambígua ou tema fora das categorias, sempre com revisão e
motivo. Uma ficha de matrícula sem pedido explícito permanece matricula: ausência
de pedido não torna o tema ambíguo. Emissão de declaração é solicitacao_documentos.

`metrics.acuracia_categorias` mantém numerador, denominador, valor, percentual e
divergências por ID. Todos os IDs esperados entram no denominador; ID sem saída
não conta como acerto, inclusive quando o gabarito histórico contém null.
Denominador zero retorna valor/percentual null. Os gabaritos não foram alterados
para adaptar as métricas à categoria nova. Os dois avaliadores (real e
offline) publicam as mesmas duas contas: `acuracia_gabarito_original` (seis
casos, S06 com null) e `acuracia_categorias_definidas` (cinco casos).

## Evidências reais e correções

Modelo utilizado: gpt-6.1-terra, perfil principal, Responses API, store=False,
max_output_tokens=4096 e reasoning.effort=low **somente na configuração em memória
da avaliação**. O perfil compartilhado permanece com seus parâmetros originais.
A compatibilidade e os preços foram conferidos na documentação oficial:
[GPT-6.1 Terra](https://developers.openai.com/api/docs/models/gpt-6.1-terra),
[Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
e [perfil alternativo GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna).
O alternativo não foi chamado nesta rodada; acesso real foi demonstrado somente
para o principal. Preços padrão configurados: US$ 1/M entrada e US$ 5/M saída;
a estimativa não aplica desconto de cache nem substitui o faturamento do provedor.

O .env foi carregado sem exibir seu conteúdo, continua ignorado e não versionado,
com permissão 0600. Nenhuma chave foi registrada nos artefatos. As gerações ficam
em artefato de experimento explicitamente solicitado, separado do log de auditoria.

### Rodada final com os prompts ativos

A tabela "histórico" mistura versões de prompt: só S01 chegou a rodar com
`solicitacao_d2_v4`; S02, S03, S04 e S06 rodaram com v2 e S05 com v3. Em
01/11/2026 os seis casos, a comparação de S02 e a variante de data impossível
foram reexecutados com os prompts ativos (`solicitacao_d2_v4`,
`compreensao_d2_v3`), num ledger próprio para não reiniciar o saldo da missão
original. Gabaritos de RF14/RF15 inalterados.

| Medida, prompts ativos | Resultado real |
|---|---|
| Extração e ficha válidas | 6/6, nenhum reparo acionado |
| Acurácia contra os seis gabaritos originais | 5/6 = 0,833 (divergência: S06, null × revisao) |
| Acurácia nas categorias com rótulo definido | 5/5 = 1,0 |
| Palavras dos resumos S01 a S06 | 75, 21, 19, 24, 67, 26 |
| Entidades esperadas corretas / omitidas | 32 / 0; adicional sustentada: GOVERNO DE MATO GROSSO |
| Comparação JSON livre × esquema (S02) | ambas válidas no esquema e nas regras |
| Variante com 31/02/2026 | bloqueada com RespostaMalformada, sem minuta |
| Chamadas / tokens entrada e saída / custo | 22 / 29.443 e 3.193 / US$ 0,045408 |

Os prompts v4 e v3 e parte das regras de `validar_regras` foram ajustados
depois de ver erros nestes mesmos casos (S02 e S05). Os números medem aderência
aos seis casos conhecidos, não desempenho em solicitações novas.

### Histórico acumulado

| Medida, histórico (prompts v2 a v4) | Resultado real |
|---|---|
| Solicitações com extração e ficha avaliadas | 6/6 |
| Acurácia exata contra os seis gabaritos originais | 5/6, 83,33% |
| Categorias temáticas com rótulo definido no gabarito | 5/5, 100% |
| Caso ambíguo | revisao, pedido null e necessita_revisao=true |
| Palavras dos resumos S01 a S06 | 78, 21, 19, 26, 62, 28 |
| Fatos essenciais conferidos nos resumos finais | 15; nenhuma omissão semântica identificada |
| Entidades esperadas corretas / omitidas | 32 / 0 |
| Entidades adicionais sem suporte identificadas | 0 |
| Entidade adicional sustentada | GOVERNO DE MATO GROSSO no OCR |
| Chamadas de transporte totais, incluindo correções | 31 |
| Tokens entrada / saída | 39.581 / 5.176 |
| Custo estimado total | US$ 0,065461 |
| Chamadas sem usage | 0 |

A diferença exata de categoria é D2-S06: o gabarito anterior previa null e agora
o requisito exige a categoria revisao. Essa diferença **continua contada como
divergência**, em vez de reescrever o esperado e alegar 100% nos seis casos.
Também estão registradas diferenças de texto do assunto/pedido em S01: o assunto
é mais específico, e pedido preserva tanto efetivação quanto esclarecimento,
ambos expressos no áudio. O motivo de revisão em S05 é uma paráfrase do gabarito.

O histórico completo foi preservado:

1. Primeira rodada: seis extrações, seis resumos com verificação semântica e uma
   comparação das duas abordagens. O OCR omitiu data, incluiu protocolo ilegível
   na lista de entidades e confundiu ausência de pedido com tema ambíguo.
2. Correção de regras e prompts; somente S01/S05 e a comparação S02 foram
   repetidos. O OCR passou a preservar a data e a categoria, sem completar o
   protocolo. Surgiu uma ausência indevida de assunto em S01, corrigida por
   orientação de que o assunto pode vir do texto corrido, sem cabeçalho.
3. Somente a extração S01 foi repetida; o resumo já válido foi reutilizado.
   A última extração tem assunto preenchido, sem ausências e sem revisão indevida.
4. Variante controlada de S02 com data 31/02/2026: a expectativa foi persistida
   antes da chamada. Houve duas gerações, incluindo exatamente um reparo, e
   RespostaMalformada bloqueou o resultado. Nenhuma minuta foi criada.

Na primeira comparação JSON livre × esquema, **ambas** as respostas eram válidas
sintaticamente e no esquema, mas classificavam emissão como matricula. Essa é
uma evidência real de que schema não garante correção de negócio. A regra nova
rejeita as duas respostas anteriores; a repetição específica retornou
solicitacao_documentos em ambas, sem problemas de regras. Não se fabricou uma
falha sintática para atribuir superioridade à abordagem restrita.

Os seis casos finais não exigiram reparo automático. O reparo real e a recusa
foram demonstrados pela variante de data impossível. Testes offline cobrem,
adicionalmente, JSON inválido, coerções, campos omitidos/extras, reparo único,
falha persistente, paráfrases válidas/contraditórias, falha do verificador,
compatibilidade com null legado e limites de consumo. Regressão na entrega
do Integrante 1: 284 testes aprovados, incluindo 87 de NLP/dados e 5 de
orçamento; com as partes do Integrante 2 e as correções da revisão, 315
aprovados, 93 deles de NLP/dados e orçamento.
A validação da base confirmou novamente as quantidades exatas e 35 IDs únicos.

Artefatos em `documentacao/desafio-2/evidencias/`:

- integrante-1-openai.json: saídas, tentativas, divergências e revalidação das
  respostas antigas pelas regras finais, sem apagar os resultados iniciais.
- integrante-1-conferencia-openai.json: conferência técnica dos fatos e entidades.
  É avaliação por IA, **não aprovação humana**.
- integrante-1-orcamento.json: metadados de cada chamada e consumo acumulado.
- integrante-1-openai-final.json e integrante-1-orcamento-final.json: rodada
  final dos seis casos com os prompts ativos, em ledger próprio.
- testes-openai.txt e dados-validados-openai.json: regressão e validação da base.
- Os arquivos anteriores de simulação e bloqueio por falta de chave foram
  preservados como evidência histórica da primeira entrega.

## Reprodução e orçamento

```bash
source .venv/bin/activate
python -m scripts.validar_dados_d2
python -m pytest
python -m scripts.validar_nlp_real
# Só a etapa afetada, reutilizando extração/ficha já registrada:
python -m scripts.validar_nlp_real --casos D2-S05 --etapas extracao compreensao
python -m scripts.validar_nlp_real --casos D2-S02 --etapas comparacao
python -m scripts.validar_nlp_real --casos D2-S02 --etapas bloqueio
```

O comando antigo `scripts.avaliar_nlp_d2 --real` agora delega ao avaliador com
orçamento. A opção sem --real permanece offline. O avaliador novo usa, por
padrão, resultados/metricas/integrante-1-openai.json e um ledger persistente em
resultados/metricas/integrante-1-orcamento.json. `--saida` escolhe o relatório;
`--ledger` escolhe o ledger. Para continuar esta mesma missão, use o ledger
original, sem apagá-lo ou reiniciá-lo. Em outra cópia do repositório, restaure
a cópia versionada do ledger no caminho de trabalho antes de continuar esta
mesma missão; não reinicie o saldo. Não rode avaliações concorrentes.

Antes de cada transporte, inclusive repetição transitória, reserva um limite
superior com bytes UTF-8 de entrada, margem para o protocolo e saída máxima.
Usage disponível substitui a reserva pelo custo medido; falha sem usage conserva
a reserva, em vez de assumir custo zero. Sem preço ou saldo suficiente, nenhuma
chamada é feita. Limites: US$ 1 acumulado e 40 transportes. A contabilização se
aplica às gerações de extração, reparo, resumo, verificação e comparação.

## Integração e pendências externas

Integrante 2: carregar o manifesto existente, extrair PDF/TXT, indexar e mapear
as citações literais para chunks reais. No fluxo, capturar `ErroLLM` e registrar
bloqueio; chamar também `validar_regras` com o original antes da minuta.
Problemas não vazios interrompem a geração. Reaproveitar todas as respostas de
`Resultado` para custo/latência, incluindo o reparo. Fichas com null continuam
visíveis para revisão; não completar fatos usando documentos institucionais.
As decisões “aprovar” nos gabaritos são expectativas, nunca autorizações.

Integrante 3: usar as doze avaliações e a regra de ambiguidade publicada; testar
os três ataques, inclusive DOC-06 após recuperação, sem executar seu conteúdo.
Mostrar null como “não localizado”; combinar solicitação + ficha na tela sem
reclassificar. Registrar decisão humana; nenhuma função de envio foi criada.

Permanecem para integração do grupo: índice/RAG, guardrails, sentimentos,
interface, decisões humanas e testes T04–T15 em serviço real. Não foram
implementadas funções reservadas aos demais integrantes. A validação real de RF14/RF15 foi concluída; a demonstração integrada de
índice, minutas e decisões humanas permanece com o grupo. A fidelidade semântica
e as justificativas inferidas ainda exigem revisão humana. Categoria revisao
não é o status revisar do registro de minuta: preservar os dois contratos.
