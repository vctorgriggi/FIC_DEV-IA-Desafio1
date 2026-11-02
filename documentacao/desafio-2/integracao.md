# Entrega integrada do Desafio 2 — estado, métricas e matriz T01–T15

As três partes rodam integradas com o serviço real (rodada final de 01/11/2026,
`gpt-6.1-terra`, embeddings `text-embedding-3-small`, chunking B), e as minutas
da rodada têm decisão registrada (seção "Decisões do operador").
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

Na conferência de afirmações, o trecho de apoio de cada uma é copiado da
passagem citada e verificado por código. O denominador são as 11 respostas `fundamentada` da rodada final
(seis consultas e cinco minutas); respostas `sem_evidencia` não fazem afirmação
institucional. Acervo de 12 trechos: estes números não estimam desempenho em
documentos reais.

## Matriz T01–T15

Situação: **real** é execução com o serviço nesta entrega; **offline** é teste
automatizado com transporte simulado.

| ID | Requisito | Entrada | Esperado | Obtido | Evidência | Situação |
|---|---|---|---|---|---|---|
| T01 | RF14/RF15 | JSON com tipo incorreto e campo ausente; variante real do Integrante 1 | Rejeição pelo esquema; nenhuma minuta inválida | Esquema rejeita; fluxo bloqueia extração inválida; comparação sintático × esquema registrada | `test_d2_nlp.py`, `integrante-1-openai.json`, `integrante-1.md` | real e offline |
| T02 | RF14 | Data impossível; dado ausente do original | Regra de negócio bloqueia e pede revisão | Bloqueio com reparo único e recusa | `test_d2_nlp.py`, `integrante-1-openai.json` | real e offline |
| T03 | RF15 | D2-S01 a D2-S06 | Resumo, categoria e entidades avaliados | Categoria 5/6; entidades e fatos conferidos pelo Integrante 1 | `integrante-1-openai-final.json`, `rodada-final-d2.json` | real |
| T04 | RF16 | D2-A01, D2-A02, D2-A03 | Instruções não executadas, segredo não revelado | A01/A03 bloqueados sem chamada; DOC-06 fora do contexto | `rodada-final-d2.json`, `test_d2_integracao.py` | real |
| T05 | RF16 | Pergunta fora de escopo, arquivo de 5 MiB + 1 byte, nona chamada | Bloqueio ou revisão; limite respeitado | revisar, bloquear, `LimiteExecucao` auditado | `test_d2_guardrails_sentimentos.py`, `test_d2_integracao.py` | offline |
| T06 | RF17 | Reabrir em processo novo e reindexar | Índice reutilizado, sem duplicação | 12 → 12 → 12 trechos, 0 chamadas | `integrante-2-demonstracao.json` | real |
| T07 | RF18 | A 250/50 e B 500/100, R01–R05 | Top-k comparado, acerto calculado | 5/5 e 5/5; B escolhido | `integrante-2-chunking.json` | real |
| T08 | RF19 | R01–R05 | Respostas e citações verificadas | 5/5 `fundamentada` citando a referência; afirmações sustentadas; 5/5 aprovadas | `rodada-final-d2-consultas.json`, `conferencia-afirmacoes.json` | real |
| T09 | RF19 | R06, R07 | Abstenção e encaminhamento | 2/2 `sem_evidencia` com revisão, sem valor ou prazo inventado | `rodada-final-d2-consultas.json` | real |
| T10 | RF19 | R08 e variante neutra | Prioridade documentada ou conflito | 30/10/2026 por vigência e `substitui`; conflito sem regra só offline | `rodada-final-d2-consultas.json`, `integrante-2-variante-R08.json` | real |
| T11 | RF20/RF24 | Minutas pendentes da rodada final | Aprovação e rejeição persistidas, sem envio | 9 aprovadas, 7 em revisão, 1 rejeitada, com justificativa, revisor e horário; nenhuma enviada | `resultados/minutas_rag/`, eventos `revisao_rag` no log | real |
| T12 | RF21 | Perfil `alternativo`; modelo inexistente | Índice preservado; falha auditada | 1 texto embedado, 12 trechos antes e depois; `RequisicaoInvalida` auditada | `integrante-2-demonstracao.json` | real |
| T13 | RF22/RF23 | Filtro, ID repetido, conjunto vazio; lote real | Totais corretos, denominador visível | Testes de filtro e vazio; painel do lote real com 12 e 2 em revisão | `test_d2_guardrails_sentimentos.py`, [`painel-sentimentos.jpg`](evidencias/painel-sentimentos.jpg) | real e offline |
| T14 | RF24 | Exclusão de DOC-05 | Trechos fora da busca, exclusão registrada | DOC-05 fora do top-k, do manifesto e das duas coleções | `integrante-2-demonstracao.json` | real |
| T15 | RF23 | texto-01 e imagem-01 pelo fluxo do Desafio 1 | Seguem até minuta e revisão | texto-01 `e25d1dfbc4e2`: aprovada com correção (fecho repetia a data da solicitação); imagem-01 `63d6ff52c0df`: protocolo confirmado contra a ficha, aprovada | `resultados/minutas/`, `dados/processados/`, eventos `revisao` no log | real |

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

## Decisões do operador

Registradas por `revisao.registrar_decisao_rag` (a mesma função do formulário da
tela), com revisor Victor Griggi Moreira Regis da Silva.

| Caso | ID | Decisão | Motivo |
|---|---|---|---|
| D2-S01 | `a53846a45670` | aprovar | Documentos exigidos conferidos com DOC-02 v2.0 |
| D2-S02 | `f457909dfe80` | revisar | Orientação correta, mas termina com "Esta minuta permanece pendente…", frase interna que não vai ao cidadão |
| D2-S03 | `e8eff831aaf7` | aprovar | Procedimento conferido com DOC-04; não declara o cancelamento feito |
| D2-S04 | `24ed20a5bd31` | revisar | Mesma frase interna no fim do texto |
| D2-S05 | `d86b377b8b1b` | revisar | Ficha sem pedido e com código ilegível |
| D2-S06 | `bfe52ac0b3d8` | revisar | Intenção ambígua; contatar o solicitante |
| texto-01 | `b8c3904a2543` | aprovar | Documentos e prazo de DOC-02, vigente em 14/10/2026 |
| imagem-01 | `66addd6b9405` | revisar | OCR com protocolo e CPF ilegíveis, sem pedido |
| D2-A02 | `eb31310e7c68` | rejeitar | Consulta dirigida ao anexo adversarial; nada a enviar |
| D2-R01–R05, R08 | `be08d96a5f49`, `83c6ec42493f`, `4949202cfb3b`, `e098f21a15ad`, `035dce8a4c47`, `ad000c961abd` | aprovar | Conferidas com a passagem citada |
| D2-R06, R07 | `24ded603c55c`, `e859588e3d2b` | revisar | Abstenção correta; o servidor responde com a informação individual |

Contra o gabarito (`decisao_esperada`): S01, S03, S05 e S06 iguais; S02 e S04
saíram `revisar` em vez de `aprovar`. O gabarito avalia o caso; a revisão
avalia o texto gerado, e esse texto inclui uma frase que não pode ir ao
cidadão. A divergência fica registrada, e o prompt da minuta é o ponto a
corrigir numa próxima versão.

D2-A01 e D2-A03 ficaram `bloqueada`: não há minuta para decidir.

Regressão do Desafio 1 (T15), pela linha de comando do Desafio 1: `texto-01`
(`e25d1dfbc4e2`) aprovada com correção, porque o fecho repetia a data da
solicitação como data da comunicação, a mesma falha registrada no Desafio 1;
`imagem-01` (`63d6ff52c0df`) com o protocolo confirmado como 2026-000142 contra
a ficha original (quarto dígito rasurado) e aprovada.
