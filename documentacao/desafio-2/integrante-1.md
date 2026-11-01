# Integrante 1 — Dados, RF14 e RF15

Implementado em 31/10/2026 na branch `feat/desafio2-integrante1-dados-nlp`.
O acervo é inteiramente fictício, inspirado apenas nos temas de matrícula e
retificações dos editais fornecidos. Suas regras não são oficiais. Os originais
do Desafio 1 e os contratos compartilhados foram preservados.

## Arquitetura e integração

`nlp.extrair_solicitacao` → `SolicitacaoEstruturada` → `nlp.validar_regras` →
`nlp.compreender` → `FichaCompreensao`. O esquema permanece em versão 2.0.
Nenhuma destas funções gera ou envia uma minuta.

Todas as chamadas usam `ClienteLLM.gerar`, o perfil de `Config.perfil_geracao`,
`formato_json` e o prompt de sistema seguro existente. Assim permanecem no
adaptador único `store=False`, timeout, repetição transitória, contabilização de
tokens, custo e latência. Mascaramento e ocultação de formatos de chave são
aplicados antes do envio, inclusive à solicitação estruturada da compreensão.
Entradas e origem passam por `prompts.delimitar`, neutralizando tags falsas.

O `Resultado` guarda valor, respostas do provedor e prompt (identificador/hash).
Na falha definitiva de validação, `RespostaMalformada` também disponibiliza
`respostas` e `prompt` para auditoria. Seu detalhe traz apenas tipos/localização
de erros e mensagens de regras, sem reproduzir valores inválidos. Falhas do
provedor continuam como subclasses de `ErroLLM`, sem disparar reparo de JSON.

Prompts novos: `solicitacao_d2_v1.md` e `compreensao_d2_v1.md`. Nenhum prompt
anterior foi editado. Perfil alternativo não altera dados nem índice.

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
| D2-S06 | ambígua | null; intenção entre continuar e cancelar não definida |

Entradas estão em `dados/originais/desafio-2/D2-S*.txt`; gabaritos em
`dados/gabaritos/D2-S*.json`. Cada gabarito tem campos presentes/ausentes,
entidades, fatos essenciais, justificativa, resumo de referência e decisão
esperada. Áudio e OCR têm referência ao arquivo revisado e SHA-256 da origem;
a validação confere igualdade dos bytes. Não se completa o protocolo do OCR
com a transcrição do áudio. Pessoas e identificadores destes casos anteriores
são fictícios, conforme a documentação do Desafio 1.

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
protocolo fora de `aaaa-nnnnnn`, abreviado ou ausente do original; nome,
assunto, pedido e entidades sem suporte literal; datas inexistentes, inválidas
ou não sustentadas. Datas aceitam `dd/mm/aaaa`, ISO e mês por extenso em
português. A data rotulada da solicitação ou ligada ao protocolo prevalece
sobre nascimento e datas do curso. Não há validação por relógio: datas futuras
em documentos não são automaticamente erros.

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
A ficha só admite resumo e inferências. O resumo é extrativo: passagens
literais do texto mascarado, unidas por ` … `, no máximo 100 palavras.
O código verifica cada passagem e rejeita texto sem apoio. Isso reduz
invenções, mas seleção enganosa, perda de negação/contexto e omissão de fatos
ainda exigem conferência humana. Inferências têm campo, valor e justificativa
não vazios; não podem substituir campos da solicitação. Não há reparo adicional
na ficha: erro de compreensão bloqueia e pede revisão.

As cinco categorias existentes continuam: matrícula, informação, emissão de
documentos, reclamação e cancelamento (códigos em `config.json`). Limitação
formal: RF15 pede categoria “outros” ou “revisão”, mas o contrato configurado
não as inclui. Sem alterar contrato compartilhado, a alternativa implementada
é categoria null + ausência + revisão com motivo. A inclusão de um novo rótulo
continua sendo decisão do grupo. O caso ambíguo verifica esse fallback.

`metrics.acuracia_categorias` usa `proporcao`: numerador, denominador, valor,
percentual e divergências por ID. Todos os IDs com gabarito de categoria entram
no denominador; saída faltante ou null contra rótulo definido é erro. IDs sem
gabarito são excluídos. Denominador zero produz valor/percentual null.
A avaliação do conjunto separa o caso cujo rótulo esperado é null: cinco
categorias definidas e uma abstenção esperada, sem transformar revisão em
categoria inventada.

## Evidências e reprodução

```bash
source .venv/bin/activate
python -m scripts.validar_dados_d2
python -m pytest testes/test_d2_nlp.py -q
python -m scripts.avaliar_nlp_d2
python -m scripts.avaliar_nlp_d2 --real  # opcional; S01/S02 e comparação, para na primeira falha
python -m pytest
```

Os scripts não editam os gabaritos. Avaliação padrão usa SDK falso e grava
`resultados/metricas/integrante-1-simulado.json` (fora do git). Para escolher
outro caminho, use `--saida`. As evidências desta entrega foram gravadas em
`documentacao/desafio-2/evidencias/` para permanecerem versionadas.

- Base validada: seis documentos, seis solicitações, oito perguntas, doze
  avaliações, três ataques e 35 IDs únicos; citações e referências conferidas.
- Situação inicial: 193 testes aprovados, 21 subtestes aprovados, sem falhas.
- T01: schema rejeita tipos, ausências e extras; JSON inválido e reparo único
  também testados.
- T02: datas impossíveis, data de nascimento indevida, nome/entidade sem
  suporte, protocolo inconsistente e listas de ausência bloqueados.
- T03: seis extrações/fichas simuladas; resumos de 56, 9, 7, 13, 20 e 16 palavras;
  zero omissões dos fatos essenciais e zero entidades incorretas/omitidas nos
  cenários simulados. Acurácia simulada 5/5 = 100%, uma abstenção correta
  avaliada separadamente. Não são métricas de qualidade de um modelo real.
- API real: bloqueada por ausência de `OPENAI_API_KEY`; zero chamadas reais.
  O arquivo `integrante-1-real.json` registra exatamente esse bloqueio.
- A suíte completa inclui regressão dos fluxos anteriores com SDK falso.
  Total final: 261 testes aprovados, zero falhas; 69 testes específicos de NLP/dados. A saída do pytest está em `evidencias/testes.txt`.

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
implementadas funções reservadas aos demais integrantes. A falta de chave
impede medir qualidade, tokens/custos reais ou demonstrar ponta a ponta real.
A fidelidade semântica de resumo e justificativas inferidas exige revisão.
