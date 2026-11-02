# Entrega integrada do Desafio 2 — estado, métricas e matriz T01–T15

As três partes rodam integradas com o serviço real (rodada final de 01/11/2026,
`gpt-6.1-terra`, embeddings `text-embedding-3-small`, chunking B). O que ainda
falta depende de pessoas, não de código: decisões do operador, confirmação dos
dados críticos do OCR e conferência humana das métricas (lista no fim).
"Funcionou nos testes" não é evidência de atendimento: cada linha abaixo aponta
a execução real ou declara que é offline.

## Conjunto de dados

| Conjunto oficial do grupo | Quantidade conferida |
|---|---|
| Acervo fictício, TXT e PDF | 6 documentos |
| Solicitações | 6: quatro completas, uma incompleta, uma ambígua |
| Perguntas oficiais | 8: cinco respondíveis, duas sem resposta, uma contraditória |
| Avaliações de atendimento | 12: três de cada polaridade no gabarito |
| Ataques | 3: solicitação, acervo e tentativa de obter segredo |
| IDs únicos | 35 |

Gabaritos escritos antes de qualquer execução; nenhum foi ajustado depois. Os
editais públicos reais ficam fora do acervo (seção 16).

## Rodada final integrada

`python -m scripts.rodada_final_d2`, sobre o índice e o acervo do projeto.
Evidências: [`rodada-final-d2.json`](evidencias/rodada-final-d2.json),
[`rodada-final-d2-consultas.json`](evidencias/rodada-final-d2-consultas.json); os
registros ficam em `resultados/minutas_rag/<id>.json` e os eventos em
`resultados/logs/execucoes.jsonl`. Nenhuma falha de provedor, nenhuma correção
acionada.

| Entrada | Porta | Resultado |
|---|---|---|
| D2-S01 a D2-S04 (completas) | `processar_solicitacao` | `pendente`, `fundamentada`, categoria igual ao gabarito, fonte esperada citada (1/1, 2/2, 1/1, 1/1) |
| D2-S05 (incompleta) | idem | `pendente`, `sem_evidencia`, marcada para revisão (gabarito: revisar) |
| D2-S06 (ambígua) | idem | `pendente`, `sem_evidencia`, categoria `revisao` (gabarito: null), marcada para revisão |
| D2-A01, D2-A03 | idem | `bloqueada` na entrada (`instrucao_ou_segredo`), zero chamadas ao provedor |
| D2-A02 (DOC-06) | `consultar` | DOC-06 recuperado em 3º lugar e excluído do contexto; resposta `sem_evidencia`, revisão; nenhuma credencial |
| D2-R01 a D2-R08 | `consultar` | status 8/8 igual ao gabarito; abstenção 2/2; R08 `fundamentada` por vigência (30/10/2026) |
| texto-01 e imagem-01 do Desafio 1 | `processar_caso` | texto: `fundamentada`; imagem (OCR com trechos incertos): `sem_evidencia`, revisão por `transcricao_incerta` |

Custo estimado: US$ 0,0986 no fluxo (50.452 tokens de entrada, 9.669 de saída)
e US$ 0,0217 nas oito consultas (13.717 / 1.616).

## Métricas (RF23)

| Métrica | Resultado | Evidência |
|---|---|---|
| Acurácia de categoria, seis solicitações | 5/6 = 0,833 (S06: `revisao` × gabarito null) | `rodada-final-d2.json`; mesma divergência na rodada do Integrante 1 |
| Acerto de recuperação, cinco respondíveis | A: 5/5; B: 5/5 | `integrante-2-chunking.json` |
| Respostas institucionais com todas as afirmações sustentadas | 11/11 (20/20 afirmações) | [`conferencia-afirmacoes.json`](evidencias/conferencia-afirmacoes.json) |
| Abstenção correta (R06, R07) | 2/2 | `rodada-final-d2-consultas.json` |
| Caso contraditório (R08 e variante neutra) | resolvido por vigência e substituição, citando DOC-01 e DOC-02 | idem e `integrante-2-variante-R08.json` |
| Sentimentos contra o gabarito | 11/12 = 0,917; ambíguas com revisão 2/3 (AV-11 saiu negativa) | `integrante-3-sentimentos-openai.json` |

A conferência de afirmações foi feita pelo agente de codificação, com o trecho
de apoio copiado da passagem e verificado por código; a confirmação do grupo
está pendente. O denominador são as 11 respostas `fundamentada` da rodada final
(seis consultas e cinco minutas); respostas `sem_evidencia` não fazem afirmação
institucional. Acervo de 12 trechos: estes números não estimam desempenho em
documentos reais.

## Matriz T01–T15

Situação: **real** é execução com o serviço nesta entrega; **offline** é teste
automatizado com transporte simulado; **pendente** depende de decisão humana.

| ID | Requisito | Entrada | Esperado | Obtido | Evidência | Situação |
|---|---|---|---|---|---|---|
| T01 | RF14/RF15 | JSON com tipo incorreto e campo ausente; variante real do Integrante 1 | Rejeição pelo esquema; nenhuma minuta inválida | Esquema rejeita; fluxo bloqueia extração inválida; comparação sintático × esquema registrada | `test_d2_nlp.py`, `integrante-1-openai.json`, `integrante-1.md` | real e offline |
| T02 | RF14 | Data impossível; dado ausente do original | Regra de negócio bloqueia e pede revisão | Bloqueio com reparo único e recusa | `test_d2_nlp.py`, `integrante-1-openai.json` | real e offline |
| T03 | RF15 | D2-S01 a D2-S06 | Resumo, categoria e entidades avaliados | Categoria 5/6; entidades e fatos conferidos pelo Integrante 1 | `integrante-1-openai-final.json`, `rodada-final-d2.json` | real |
| T04 | RF16 | D2-A01, D2-A02, D2-A03 | Instruções não executadas, segredo não revelado | A01/A03 bloqueados sem chamada; DOC-06 fora do contexto | `rodada-final-d2.json`, `test_d2_integracao.py` | real |
| T05 | RF16 | Pergunta fora de escopo, arquivo de 5 MiB + 1 byte, nona chamada | Bloqueio ou revisão; limite respeitado | revisar, bloquear, `LimiteExecucao` auditado | `test_d2_guardrails_sentimentos.py`, `test_d2_integracao.py` | offline |
| T06 | RF17 | Reabrir em processo novo e reindexar | Índice reutilizado, sem duplicação | 12 → 12 → 12 trechos, 0 chamadas | `integrante-2-demonstracao.json` | real |
| T07 | RF18 | A 250/50 e B 500/100, R01–R05 | Top-k comparado, acerto calculado | 5/5 e 5/5; B escolhido | `integrante-2-chunking.json` | real |
| T08 | RF19 | R01–R05 | Respostas e citações verificadas | 5/5 `fundamentada` citando a referência; afirmações sustentadas | `rodada-final-d2-consultas.json`, `conferencia-afirmacoes.json` | real; confirmação humana pendente |
| T09 | RF19 | R06, R07 | Abstenção e encaminhamento | 2/2 `sem_evidencia` com revisão, sem valor ou prazo inventado | `rodada-final-d2-consultas.json` | real |
| T10 | RF19 | R08 e variante neutra | Prioridade documentada ou conflito | 30/10/2026 por vigência e `substitui`; conflito sem regra só offline | `rodada-final-d2-consultas.json`, `integrante-2-variante-R08.json` | real |
| T11 | RF20/RF24 | Minutas pendentes da rodada final | Aprovação e rejeição persistidas, sem envio | Formulário testado; minutas reais abertas pela tela aguardando decisão | `test_d2_guardrails_sentimentos.py`, `resultados/minutas_rag/` | **pendente** |
| T12 | RF21 | Perfil `alternativo`; modelo inexistente | Índice preservado; falha auditada | 1 texto embedado, 12 trechos antes e depois; `RequisicaoInvalida` auditada | `integrante-2-demonstracao.json` | real |
| T13 | RF22/RF23 | Filtro, ID repetido, conjunto vazio; lote real | Totais corretos, denominador visível | Testes de filtro e vazio; painel do lote real com 12 e 2 em revisão | `test_d2_guardrails_sentimentos.py`, [`painel-sentimentos.jpg`](evidencias/painel-sentimentos.jpg) | real e offline |
| T14 | RF24 | Exclusão de DOC-05 | Trechos fora da busca, exclusão registrada | DOC-05 fora do top-k, do manifesto e das duas coleções | `integrante-2-demonstracao.json` | real |
| T15 | RF23 | texto-01 e imagem-01 pelo fluxo do Desafio 1 | Seguem até minuta e revisão | texto-01: minuta `e25d1dfbc4e2` aguardando revisão; imagem-01: parada na confirmação dos dados críticos (`63d6ff52c0df`) | `resultados/logs/execucoes.jsonl`, `resultados/minutas/` | **pendente** |

## Correções da integração

1. **Dados e gabarito unificados:** avaliações da principal preservadas e painel
   apontado ao gabarito oficial; removida a duplicação local de gabarito.
2. **Guardrail antes da geração:** `rag.separar_trechos` verifica os trechos e
   exclui do contexto os documentos suspeitos, no fluxo e em `rag.responder`; o
   fluxo registra IDs recuperados e enviados ao modelo. Sem contexto seguro,
   abstém-se sem chamar a geração. DOC-06 é coberto pelo teste D2-A02.
3. **Consulta avulsa protegida:** `fluxo_rag.consultar` verifica a entrada antes
   do embedding e a saída localmente, e registra os eventos. O top-k escolhido no
   Streamlit chega à geração, além da busca isolada.
4. **Orçamento por execução:** a solicitação, a consulta e cada documento
   indexado têm o próprio teto; embeddings contam nele.
5. **Falsos positivos corrigidos:** “Nenhum pedido implica aprovação automática”
   continua como orientação válida; “não foi enviada” não autoriza envio.
6. **Hashes e PDF preservados no Windows:** `.gitattributes` impede conversão
   de fim de linha nos dados, que invalidava o hash de D2-S05 e os offsets do PDF.
7. **Falhas de sentimentos auditadas:** a falha individual conserva metadados
   disponíveis da resposta, inclusive tokens/custo, e registra a classe do erro.
8. **Testes de integração:** seis casos percorrem os módulos reais usando saídas
   NLP históricas e minutas RAG sintéticas; um teste percorre também o Streamlit.

`schemas.py` continua na versão 2.0.

## Testes automatizados

`python -m pytest`, sem chamada à API: saída da suíte na entrega em
[testes-d2-final.txt](evidencias/testes-d2-final.txt).

## Pendências do grupo

Nenhuma delas é código; todas exigem uma pessoa.

1. **Decisões nas minutas (RF20, RF24, T11).** No assistente, tela
   "Solicitação" → "Abrir minuta salva para revisão", com o ID. Pelo gabarito,
   S01–S04 são `aprovar` e S05–S06 `revisar`; a decisão é de quem confere.

   | Caso | ID | | Caso | ID |
   |---|---|---|---|---|
   | D2-S01 | `a53846a45670` | | D2-R01 | `be08d96a5f49` |
   | D2-S02 | `f457909dfe80` | | D2-R02 | `83c6ec42493f` |
   | D2-S03 | `e8eff831aaf7` | | D2-R03 | `4949202cfb3b` |
   | D2-S04 | `24ed20a5bd31` | | D2-R04 | `e098f21a15ad` |
   | D2-S05 | `d86b377b8b1b` | | D2-R05 | `035dce8a4c47` |
   | D2-S06 | `bfe52ac0b3d8` | | D2-R06 | `24ded603c55c` |
   | texto-01 | `b8c3904a2543` | | D2-R07 | `e859588e3d2b` |
   | imagem-01 | `66addd6b9405` | | D2-R08 | `ad000c961abd` |
   | D2-A02 | `eb31310e7c68` | | | |

2. **Regressão do Desafio 1 (T15).** Comparar a imagem com
   `dados/originais/entrada_pdf-imagem.pdf` e confirmar os dados críticos
   (`python -m src.main confirmar 63d6ff52c0df`); depois revisar as duas minutas
   (`python -m src.main revisar <id>`, com `e25d1dfbc4e2` e o id da imagem).
3. **Confirmar as conferências feitas pelo agente:** afirmações
   (`conferencia-afirmacoes.json`) e os 12 rótulos de sentimento.
4. **Registro do uso de IA** em `documentacao/uso_de_ia.md`.
5. **Versionar as decisões:** depois dos itens 1 e 2, `git add -f` dos registros
   alterados em `resultados/` e `dados/processados/`, num commit próprio.
