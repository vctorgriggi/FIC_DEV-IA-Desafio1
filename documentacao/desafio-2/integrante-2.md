# Integrante 2 — Índice, RAG e provedor (RF17, RF18, RF19, RF21, RF24)

Validado com a API real em 01/11/2026. Embeddings `text-embedding-3-small`
(1536 dimensões); geração `gpt-6.1-terra` (perfil `principal`) e `gpt-6-luna`
(perfil `alternativo`). `src/schemas.py` continua na versão 2.0 e as
assinaturas dos esqueletos não mudaram; as funções novas são acréscimos.

## Decisões

- **Id do trecho com o hash do arquivo** (`DOC:hash12:chunking:n`): reindexar
  o mesmo arquivo dá os mesmos ids (upsert, sem duplicata); arquivo alterado dá
  ids novos e os antigos saem, mas só depois de os embeddings novos chegarem:
  falha do provedor deixa o documento com os trechos antigos, não sem nenhum.
- **Uma coleção Chroma por chunking**, cosseno em `configuration`. Os metadados
  da coleção guardam modelo, dimensão e parâmetros do chunking; abrir com outro
  modelo ou outros parâmetros é `IndiceIncompativel`, que pede apagar `indice/`
  e reindexar. Sem isso, mudar 500 para 520 manteria os mesmos ids e trechos
  velhos com `versao_indice` nova.
- **`versao_indice`** é o hash de modelo, chunking e `{documento: versão, hash}`;
  vai para a auditoria (RF21).
- **Cabeçalho confiável, texto não confiável.** Id, documento, versão, vigência
  e `substitui` vêm do manifesto, fora do bloco delimitado; o texto do trecho
  vai em `prompts.delimitar`. É o cabeçalho que resolve o conflito do R08 por
  vigência sem confiar no texto do documento.
- **Recuperação separada da geração** (`rag.recuperar`, `gerar_resposta`,
  `gerar_minuta`): o fluxo aplica `guardrails.verificar_trechos` entre as duas,
  e trecho bloqueado não chega ao modelo. Fica no registro como decisão e na
  auditoria (`ids_recuperados` × `ids_enviados_ao_modelo`).
- **Conferência por código** (`rag._problemas`), com uma tentativa de correção:
  fonte fora dos trechos, status `fundamentada`/`conflito` sem fonte, afirmação
  sem fonte na pergunta avulsa e formato de credencial. Número numa afirmação
  com fonte precisa estar nos trechos que ela cita; do caso, só data e
  protocolo. Número no texto da resposta precisa estar num trecho citado ou no
  caso (na pergunta, só data e protocolo; na minuta, qualquer fato da
  solicitação). O id do trecho não conta como fonte de números.
- **Minuta:** fatos do caso só da `SolicitacaoEstruturada` (bloco `solicitacao`),
  orientação só do acervo. O texto original não vai ao modelo.
- **Três portas, um registro** (`fluxo_rag`):
  - `processar_solicitacao`: texto digitado.
  - `processar_caso`: caso do Desafio 1. Áudio e imagem passam pela transcrição
    ou pelo OCR e seguem como solicitação (seção 1 do enunciado). Trecho
    incerto vira decisão `revisar`.
  - `consultar`: pergunta avulsa, com as mesmas camadas.
  As três gravam `RegistroMinutaRAG` pendente ou bloqueada, decidido pelo
  operador no mesmo formulário. Falha do provedor registra tokens, custo e
  prompt da etapa antes de subir.
- **Participação da IA** (RF24): a interface marca toda minuta como "Texto
  gerado por IA (modelo)", com o modelo lido da auditoria pelo `id_execucao`
  (`fluxo_rag.modelo_da_minuta`). O registro guarda o perfil, não o modelo;
  acrescentar o campo mudaria o contrato.
- **Inclusão** passa por `guardrails.verificar_arquivo`, nunca sobrescreve e é
  desfeita se o texto não se extrai (PDF digitalizado).

## Retenção e exclusão (RF24)

| Dado | Onde | Retenção |
|---|---|---|
| Documento do acervo | `dados/acervo/` e manifesto | Até a exclusão pelo assistente. |
| Vetores e trechos | `indice/`, fora do git | Derivados; recriam-se do acervo. A exclusão tira o documento de todas as coleções. |
| Minuta e decisão | `resultados/minutas_rag/` | Registro da decisão humana, mantido até o fim do exercício. Na exclusão de um documento, o texto dele sai das minutas (fica `[texto removido: …]`); id, versão e hash do trecho continuam, para rastrear a origem. |
| Log | `resultados/logs/execucoes.jsonl` | Só referências: consulta minimizada, ids, versões, tokens, erros; sem texto de trecho. |
| Provedor | OpenAI | `store=False`; entrada minimizada antes do envio. |

Documento que outro `substitui` não é excluído: o manifesto ficaria inválido e
o conflito do T10 perderia a regra. Minuta ilegível não interrompe a exclusão:
o arquivo é lido antes de apagar qualquer coisa e listado no retorno.

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
os dois estão no mesmo trecho. A cita passagens mais curtas e custa menos.

## RF19 — oito perguntas (T08, T09, T10)

Evidências: `evidencias/integrante-2-perguntas-{A,B,B-alternativo}.json`, prompt
`rag_d2_v1`, com a conferência de números atual. Uma chamada por pergunta;
nenhuma correção acionada. Cada pergunta tem `id_execucao` e horário e virou um
evento `d2_consulta` (`evidencias/integrante-2-auditoria-consultas.json`).

| Medida | A, principal | B, principal | B, alternativo |
|---|---|---|---|
| Status igual ao gabarito | 8/8 | 8/8 | 8/8 |
| Abstenção correta (R06, R07) | 2/2 | 2/2 | 2/2 |
| Respondíveis `fundamentada` citando o trecho de referência | 5/5 | 5/5 | 5/5 |
| R08: `fundamentada`, 30/10/2026, citando DOC-01 e DOC-02 | sim | sim | sim |
| Textos de documento embedados ao abrir o índice | 0 | 0 | 0 |
| Tokens entrada / saída | 11.791 / 1.124 | 13.593 / 1.255 | 13.593 / 2.277 |
| Custo estimado | US$ 0,0174 | US$ 0,0199 | US$ 0,0025 |

**T10 sem pistas na pergunta.** O D2-R08 cita os dois documentos e as duas
datas. A variante `D2-R08-neutra` ("Qual é o prazo de matrícula para quem se
matricula em 15/10/2026?"), com gabarito commitado antes da execução, também
sai `fundamentada` no índice B: 30/10/2026, citando o prazo do DOC-02 e a regra
de substituição (`evidencias/integrante-2-variante-R08.json`). Ela fica fora da
lista oficial de oito perguntas do `casos.json`.

As respostas obtidas antes do aperto da conferência de números também passam
na regra atual. "Cita o trecho de referência" é verificação por código; a
conferência de que **cada afirmação** é sustentada pela passagem, e a decisão
do operador sobre cada uma das oito (seção 13), são humanas e estão pendentes.
Para registrá-las, cada pergunta feita em "Consulta ao acervo" vira um registro
pendente com formulário de decisão.

## T06, T12, T14 — demonstração real

`python -m scripts.demonstrar_indice_d2`, numa cópia temporária do projeto.
Evidência: `evidencias/integrante-2-demonstracao.json`.

- **T06:** um **processo novo** abre o índice e reindexa os seis documentos:
  12 trechos antes, ao reabrir e depois de reindexar; 0 chamadas ao provedor,
  contadas por um cliente que registra e recusa qualquer uso; `versao_indice`
  igual; nada desatualizado.
- **T12, troca:** o perfil `alternativo` (`gpt-6-luna`) responde sobre o mesmo
  índice; só 1 texto (a consulta) passou pelo embedding e o índice ficou com 12
  trechos antes e depois.
- **T12, falha:** perfil com modelo inexistente vira `RequisicaoInvalida`,
  registrada na auditoria com erro e duração; índice inalterado.
- **T14:** "horário de atendimento" tinha DOC-05 em 1º lugar; após a exclusão,
  DOC-05 sai do top-k, do manifesto e das coleções A e B (6 trechos removidos),
  com evento `acervo_exclusao` na auditoria, sem conteúdo.

## Testes

`testes/test_d2_indice_rag.py`, 49 testes sem rede (embedding falso por saco
de palavras), um deles abrindo o índice em outro processo; suíte completa 329
aprovados. Os testes não dependem dos valores de chunking do `config.json`.

## Limites e riscos residuais

- O fluxo completo (solicitação, caso do Desafio 1, consulta pela interface)
  depende de `guardrails.verificar_entrada`, `verificar_trechos` e
  `verificar_saida` (Integrante 3). Até lá, só foi testado com guardrails
  simulados; não houve execução real de ponta a ponta. As oito perguntas foram
  avaliadas direto no `rag`, sem guardrails.
- Acervo pequeno: com 12 trechos e top-k 4, um terço do índice volta em cada
  busca. O acerto de 5/5 não indica desempenho num acervo real.
- A conferência compara algarismos: "cinco dias úteis" por extenso não é
  conferido, e afirmação sem número passa. Paráfrase errada sem número fica
  para a revisão humana.
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
python -m scripts.avaliar_rag_d2 variante
python -m scripts.demonstrar_indice_d2
```

Saídas em `resultados/metricas/rag-d2-*.json` (fora do git); as cópias
versionadas estão em `evidencias/`. O índice (`indice/`) se recria indexando o
acervo pelo assistente ou por qualquer um dos comandos acima; depois de mudar
modelo de embedding ou chunking no `config.json`, apague `indice/` antes.
