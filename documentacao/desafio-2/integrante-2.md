# Integrante 2 — Índice, RAG e provedor (RF17, RF18, RF19, RF21, RF24)

Implementado e validado com a API real em 01/11/2026, na branch
`feat/desafio2-integrante2-indice-rag`. Embeddings `text-embedding-3-small`
(1536 dimensões); geração `gpt-6.1-terra` (perfil `principal`) e
`gpt-6-luna` (perfil `alternativo`). Contratos de `src/schemas.py` mantidos na
versão 2.0; nenhuma assinatura de esqueleto mudou.

## Decisões

- **Id do trecho com o hash do arquivo** (`DOC:hash12:chunking:n`): reindexar
  o mesmo arquivo dá os mesmos ids (upsert, sem duplicata); arquivo alterado dá
  ids novos e `indexar` apaga os antigos do mesmo documento. Mesmo hash e mesma
  versão não chamam o provedor.
- **Uma coleção Chroma por chunking**, cosseno em `configuration` (no Chroma
  1.x, `hnsw:space` em `metadata` impede gravar a dimensão depois). Modelo e
  dimensão ficam nos metadados da coleção; abrir com outro modelo é
  `IndiceIncompativel`, que pede apagar `indice/` e reindexar.
- **`versao_indice`** é o hash de modelo, chunking e `{documento: versão, hash}`;
  vai para a auditoria (RF21) e não muda com a troca de perfil de geração.
- **Cabeçalho confiável, texto não confiável.** Id, documento, versão, vigência
  e `substitui` vêm do manifesto, fora do bloco delimitado; o texto do trecho
  vai em `prompts.delimitar`. É o cabeçalho que permite resolver o conflito do
  R08 por vigência sem confiar no texto do documento.
- **Conferência por código, não pelo modelo.** `rag._problemas` rejeita fonte
  fora dos trechos recuperados, status `fundamentada`/`conflito` sem fonte,
  afirmação sem fonte em `responder`, número ou data ausente das fontes citadas
  e formato de credencial. Uma tentativa de correção, recebendo só a regra
  violada; persistindo, `RespostaMalformada`.
- **Minuta:** fatos do caso só da `SolicitacaoEstruturada` (bloco `solicitacao`),
  orientação só do acervo. O texto original não vai ao modelo; serve só para
  aceitar número que a minuta repete do caso. Sem assunto nem pedido, ou sem
  trecho recuperado, a minuta é `sem_evidencia` sem chamar o modelo.
- **Fluxo** (`fluxo_rag`): guardrail de entrada → extração (RF14) → ficha
  (RF15) → minuta → guardrails de trechos e saída → registro. Estrutura, ficha ou
  minuta inválidas e qualquer `bloquear` gravam `bloqueada`; saída bloqueada não
  grava a resposta. `revisar` marca `necessita_revisao`. O registro guarda a
  entrada minimizada. Falha do provedor é auditada na etapa e levantada.
- **Exclusão** (RF24) remove trechos de todas as coleções, a entrada do
  manifesto e o arquivo; minutas já geradas ficam como histórico e o retorno diz
  quantas citam o documento. Documento que outro `substitui` não é excluído: o
  manifesto ficaria inválido e o conflito do T10 perderia a regra.
- **Inclusão** passa por `guardrails.verificar_arquivo`, nunca sobrescreve e é
  desfeita se o texto não se extrai (PDF digitalizado).

## RF18 — chunking (T07)

Unidade: caracteres, por página, com recuo até o espaço para não partir palavra.
Mesmo embedding e `top_k` = 4. Referência de cada pergunta: trechos do
documento indicado no gabarito que contêm o trecho literal (espaços
normalizados). Evidência: `evidencias/integrante-2-chunking.json`.

| Config | Tamanho / sobreposição | Trechos | Acerto | Posição da referência R01–R05 |
|---|---|---|---|---|
| A | 250 / 50 | 24 (4 por documento) | 5/5 = 1,0 | 1, 1, 1, 1, 2 |
| B | 500 / 100 | 12 (2 por documento) | 5/5 = 1,0 | 2, 1, 1, 1, 1 |

Os valores 800/1600 do início geravam o mesmo índice nas duas configurações (um
trecho por documento, documentos de ~700 caracteres); foram trocados por
estes antes de qualquer execução real.

**Escolha: B** (`chunking_ativo`). Acerto e resultado das oito perguntas
empatam; o critério que decide é a preservação de contexto. Em A, o prazo de
DOC-02 e a regra "substitui integralmente DOC-01" ficam em trechos separados e
o R08 só se resolve porque três das quatro vagas do top-k foram para eles; em B,
os dois estão no mesmo trecho. A cita passagens mais curtas e custou menos
(US$ 0,0182 contra 0,0214 nas oito perguntas).

## RF19 — oito perguntas (T08, T09, T10)

Evidências: `evidencias/integrante-2-perguntas-{A,B,B-alternativo}.json`
(prompt `rag_d2_v1`, uma chamada por pergunta, nenhuma correção acionada).

| Medida | A, principal | B, principal | B, alternativo |
|---|---|---|---|
| Status igual ao gabarito | 8/8 | 8/8 | 8/8 |
| Abstenção correta (R06, R07) | 2/2 | 2/2 | 2/2 |
| Respondíveis `fundamentada` citando o trecho de referência | 5/5 | 5/5 | 5/5 |
| R08 (contraditória) | `fundamentada`, cita DOC-01, DOC-02 e a regra | idem | idem |
| Tokens entrada / saída | 11.791 / 1.284 | 13.593 / 1.562 | 13.593 / 2.615 |
| Custo estimado | US$ 0,0182 | US$ 0,0214 | US$ 0,0027 |

"Cita o trecho de referência" é verificação por código; a conferência de que
**cada afirmação** é sustentada pela passagem (RF23) é humana e está pendente.
No `alternativo`, R06 respondeu "os valores das bolsas não estão definidos",
que é o que DOC-02 diz; no `principal`, "o acervo não informa".

## T06, T12, T14 — demonstração real

`python -m scripts.demonstrar_indice_d2`, numa cópia temporária do projeto.
Evidência: `evidencias/integrante-2-demonstracao.json`.

- **T06:** 12 trechos antes, depois de reabrir em outro cliente e depois de
  reindexar os seis documentos; zero chamadas ao provedor (o cliente da
  reabertura falha se for chamado); `versao_indice` igual; nada desatualizado.
- **T12:** troca para `alternativo` mantém `versao_indice` `652bc7c9e779`.
  Perfil com modelo inexistente vira `RequisicaoInvalida`, registrada na
  auditoria com erro e duração; índice inalterado.
- **T14:** "horário de atendimento" tinha DOC-05 em 1º lugar; após a exclusão,
  DOC-05 sai do top-k, do manifesto e das coleções A e B (6 trechos removidos),
  com evento `acervo_exclusao` na auditoria, sem conteúdo.

## Testes

`testes/test_d2_indice_rag.py`, 35 testes sem rede (embedding falso por saco
de palavras); suíte completa 314 aprovados. Lista em
`evidencias/integrante-2-testes.txt`. Os testes não dependem dos valores de
chunking do `config.json`.

## Limites e riscos residuais

- O fluxo integrado (`processar_solicitacao`) e a tela "Solicitação" dependem
  de `guardrails.verificar_entrada`, `verificar_trechos` e `verificar_saida`
  (Integrante 3). Até lá, só foi testado com guardrails simulados; não houve
  execução real do fluxo de ponta a ponta.
- Acervo pequeno: com 12 trechos e top-k 4, um terço do índice volta em cada
  busca. O acerto de 5/5 não indica desempenho num acervo real.
- A checagem de números compara algarismos: "cinco dias úteis" por extenso não
  é conferido. Afirmação parafraseada sem número passa pela checagem; a
  fidelidade dela é da revisão humana.
- Nenhuma das oito perguntas recuperou DOC-06 (ataque no acervo); o tratamento
  desse trecho é a camada `verificar_trechos` (Integrante 3) e o cenário D2-A02.
- A resolução do R08 depende do `substitui` e da `vigencia_inicio` do
  manifesto; documento contraditório sem essa regra deve sair como `conflito`
  (testado só com o modelo, não com outro acervo).

## Reproduzir

```bash
python -m scripts.avaliar_rag_d2 chunking
python -m scripts.avaliar_rag_d2 perguntas --chunking A
python -m scripts.avaliar_rag_d2 perguntas --chunking B
python -m scripts.avaliar_rag_d2 perguntas --chunking B --perfil alternativo
python -m scripts.demonstrar_indice_d2
```

Saídas em `resultados/metricas/rag-d2-*.json` (fora do git); as cópias
versionadas estão em `evidencias/`. O índice (`indice/`) se recria indexando o
acervo pelo assistente ou por qualquer um dos comandos acima.
