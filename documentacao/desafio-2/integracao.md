# Análise de integração dos três cenários — 01/11/2026

Os três cenários estão contemplados no código e integrados localmente à
principal `2728ddd`. A entrega ainda exige validação real da parte 3 e do fluxo
integrado, conferência humana e fechamento de RF23/RF24. Não se deve declarar
100% de atendimento apenas porque os testes automatizados passaram.

O canvas visual está em [canvas-integracao.html](canvas-integracao.html) e no
[Canvas no ChatGPT](https://chatgpt.com/space/page_fb451ddb1ee08191a1c7702736e0dd6d).

## Base conferida

`git fetch origin` confirmou os uploads de dados/NLP e índice/RAG. Foi feito
fast-forward de `c2c9f03` para `2728ddd`, preservando a parte 3 em stash antes
da integração. Os conflitos em avaliações e testes foram resolvidos. O stash
`salvaguarda-parte3-antes-integracao-2026-11-01` permanece como salvaguarda.
As mudanças de integração estão locais; não houve publicação no GitHub.

| Conjunto oficial do grupo | Quantidade conferida |
|---|---|
| Acervo fictício, TXT e PDF | 6 documentos |
| Solicitações | 6: quatro completas, uma incompleta, uma ambígua |
| Perguntas oficiais | 8: cinco respondíveis, duas sem resposta, uma contraditória |
| Avaliações de atendimento | 12: três de cada polaridade no gabarito |
| Ataques | 3: solicitação, acervo e tentativa de obter segredo |
| IDs únicos | 35 |

As avaliações oficiais e `dados/gabaritos/D2-sentimentos.json` prevalecem sobre
os exemplos locais da primeira implementação da parte 3. Nenhum gabarito foi
ajustado para coincidir com uma resposta do modelo. Os editais públicos reais
permanecem fora do acervo fictício do exercício.

## Cobertura por requisito

| RF | Cenário | Código e integração | Evidência e limite |
|---|---|---|---|
| RF14 | 1 — dados/NLP | Extração estrita, null, regras locais, reparo único e bloqueio | Rodada real anterior com seis extrações válidas; reprodução offline atual das seis solicitações |
| RF15 | 1 — dados/NLP | Resumo, entidades, categoria e inferências separados | Histórico: 5/6 categorias contra o gabarito original; 5/5 entre categorias definidas. S06 retorna `revisao`, enquanto o gabarito original é null; divergência preservada |
| RF16 | 3 — proteção | Entrada, arquivo, contexto antes da geração, saída e recursos | Três ataques oficiais e limites testados offline; heurísticas não cobrem toda paráfrase/ofuscação |
| RF17 | 2 — índice/RAG | Ingestão, Chroma persistente, metadados, exclusão e reindexação | Histórico real e testes atuais: reabrir/reindexar sem duplicação e troca de embedding detectada |
| RF18 | 2 — índice/RAG | A=250/50, B=500/100 caracteres; top-k 4, B ativo | Histórico real: A e B recuperam referência em 5/5. B escolhido pela preservação de contexto |
| RF19 | 2 — índice/RAG | Contexto delimitado, citações, abstenção, revisão e fluxo completo | Histórico real: status 8/8, abstenção 2/2 e referência citada 5/5. Cada afirmação ainda requer conferência humana |
| RF20 | 3 — Streamlit | Acervo, inclusão/exclusão, indexação, solicitação, fontes, painel e decisões | AppTest percorre fluxo completo com NLP/guardrails reais e transporte simulado; aprovar/rejeitar/revisar persistidos em testes |
| RF21 | 2 — auditoria | Adaptador, perfis, tokens/custo, erros, IDs, versão do índice e prompts | Histórico real dos dois perfis e falha de serviço; consulta avulsa e contexto agora auditados. Embeddings compartilham limite da solicitação |
| RF22 | 3 — sentimentos | Saída validada, indeterminação, lote tolerante a falhas, painel e gabarito oficial | Testes de contratos, filtros e persistência. Falta classificar e conferir as 12 avaliações com provedor real; não há acurácia real nova a reportar |
| RF23 | Entrega integrada | Métricas e regressão automatizada disponíveis; matriz abaixo | Parcial: falta proporção de afirmações institucionalmente sustentadas com conferência humana e rodada real integrada final |
| RF24 | Governança | Minimização, decisão registrada, ausência de envio e exclusão de documentos/vetores | Parcial: faltam decisões humanas reais na versão integrada e política de prazo/retenção/exclusão de resultados derivados explicitada pela equipe |

Os números das rodadas reais vêm dos artefatos versionados pelos integrantes,
não de novas chamadas feitas nesta integração. O sucesso em acervo pequeno
não estima desempenho em documentos reais ou em outra população.

## Correções realizadas

1. **Dados e gabarito unificados:** avaliações da principal preservadas e painel
   apontado ao gabarito oficial; removida a duplicação local de gabarito.
2. **Guardrail antes da geração:** `rag._recuperar` verifica os trechos, registra
   IDs/decisões e exclui do contexto os documentos suspeitos. Sem contexto seguro,
   abstém-se sem chamar a geração. DOC-06 é coberto pelo teste D2-A02.
3. **Consulta avulsa protegida:** entrada verificada antes do embedding, saída
   verificada localmente e eventos de consulta/geração registrados. O top-k
   escolhido no Streamlit agora chega à geração, além da busca isolada.
4. **Orçamento compartilhado:** o índice usado pela solicitação recebe o mesmo
   cliente/controle da geração; embeddings também consomem o teto de chamadas.
5. **Falsos positivos corrigidos:** “Nenhum pedido implica aprovação automática”
   continua como orientação válida; “não foi enviada” não autoriza envio.
6. **Hashes e PDF preservados no Windows:** CRLF invalidava o hash de D2-S05 e
   os offsets do PDF. Os bytes canônicos do Git foram restaurados, sem mudar
   conteúdo ou gabaritos. `.gitattributes` evita nova conversão nesses dados.
7. **Falhas de sentimentos auditadas:** a falha individual conserva metadados
   disponíveis da resposta, inclusive tokens/custo, e registra a classe do erro.
8. **Testes de integração:** seis casos percorrem os módulos reais usando saídas
   NLP históricas e minutas RAG sintéticas; um teste percorre também o Streamlit.

Não houve alteração do contrato `schemas.py`, versão 2.0. Os parâmetros novos
do RAG são opcionais e preservam os consumidores anteriores.

## Matriz T01–T15

“Offline aprovado” significa execução automatizada com transporte simulado.
“Histórico real” significa evidência anterior presente na principal. Nenhum
teste automatizado substitui a decisão de um operador de verdade.

| ID | Cenário / esperado | Obtido e situação | Evidência |
|---|---|---|---|
| T01 | Tipo incorreto/campo ausente não viram minuta inválida | Offline aprovado: esquema rejeita; fluxo bloqueia extração persistente inválida | `test_d2_nlp.py`, `test_d2_indice_rag.py`, relatório de testes |
| T02 | Data impossível/dado sem suporte bloqueiam | Offline aprovado; variante real anterior com reparo único e recusa | `test_d2_nlp.py`, `integrante-1-openai.json` |
| T03 | Seis solicitações com resumo, categoria e entidades | Reprodução integrada offline 6/6; divergência real S06 preservada | `test_d2_integracao.py`, `integrante-1-openai-final.json` |
| T04 | Três ataques tratados sem executar instruções | Offline aprovado; zero chamadas para ataques de entrada e para contexto exclusivamente malicioso | `test_tres_ataques_oficiais_e_acervo_nunca_enviado_ao_gerador` |
| T05 | Fora de escopo, arquivo excessivo e limites | Offline aprovado; limite inclui embedding e falha auditada | `test_d2_guardrails_sentimentos.py`, `test_d2_integracao.py` |
| T06 | Reabrir/reindexar sem duplicação | Offline aprovado e histórico real com 12→12→12 trechos | `test_d2_indice_rag.py`, `integrante-2-demonstracao.json` |
| T07 | Comparar A/B nas mesmas cinco perguntas | Histórico real: A=5/5 e B=5/5; B preserva mais contexto | `integrante-2-chunking.json` |
| T08 | Cinco perguntas respondíveis, fontes conferíveis | Histórico real: 5/5 citam referência; sustentação de cada afirmação ainda depende de humano | `integrante-2-perguntas-B.json` |
| T09 | Duas perguntas sem resposta exigem abstenção | Histórico real: 2/2; testes locais cobrem índice vazio/ausência de evidência | `integrante-2-perguntas-B.json`, `test_d2_indice_rag.py` |
| T10 | Resolver prioridade ou informar conflito | Histórico real: R08 e variante neutra resolvidos por vigência/substituição. Rejeição de conflito sem fonte testada offline; divergência sem prioridade ainda sem demonstração real | `integrante-2-variante-R08.json`, testes de RAG |
| T11 | Aprovação/rejeição/revisão na interface | Offline aprovado em AppTest; decisão efetiva do grupo ainda pendente | `test_d2_guardrails_sentimentos.py`, `test_fluxo_completo_pelo_streamlit_com_nlp_e_guardrails_reais` |
| T12 | Troca de perfil/falha sem reconstruir índice | Offline aprovado e histórico real com índice preservado | `integrante-2-demonstracao.json`, testes de RAG |
| T13 | Filtros, duplicatas e conjunto vazio | Offline aprovado; denominador visível e zero tratado | `test_t13_filtro_duplicata_vazio_e_confianca` |
| T14 | Exclusão retira documento/vetores da recuperação | Offline aprovado e histórico real: DOC-05 sai de A/B/manifesto | `integrante-2-demonstracao.json` |
| T15 | Texto e áudio/OCR do Desafio 1 continuam funcionando | Regressão automatizada aprovada; exige demonstração real final do grupo | `test_fluxo_e_revisao.py`, `test_audio.py`, `test_imagem.py` |

RF22 tem adicionalmente testes próprios de esquema/ID/polaridade, delimitação,
mascaramento, ambiguidade, falha individual, lote de 12 e persistência do painel.

## Verificação nova e reprodução

**Resultado:** 367 testes e 21 subtestes aprovados, com as versões do
`requirements.txt`, sem novas chamadas de geração/embeddings à API.

- [Validação da base e versões](evidencias/integracao-base.json).
- [Saída da suíte](evidencias/integracao-testes.txt) e [JUnit](evidencias/integracao-testes.xml).
- [Avaliação NLP simulada](evidencias/integracao-nlp-simulado.json), identificada como tal.
- Testes novos em `testes/test_d2_integracao.py`.

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.validar_dados_d2
.\.venv\Scripts\python.exe -X utf8 -m pytest -q
.\.venv\Scripts\python.exe -m src.main assistente
```

Nesta sessão, a pasta temporária antiga do Windows tinha restrição de acesso.
A rodada final usou `TEMP`/`TMP` em `.tmp/` e um `--basetemp` novo, com cache
desativado. Isso não foi tratado como falha funcional do projeto.

## O que falta para considerar a entrega fechada

1. Classificar as 12 avaliações oficiais com o provedor real; registrar obtido,
   esperado, divergências e revisão dos três casos ambíguos, sem mudar o gabarito.
2. Demonstrar a versão integrada com serviço real, guardar as evidências e
   registrar pelo menos uma decisão humana de aprovação e outra de rejeição/revisão.
3. Conferir semanticamente cada afirmação institucional e medir a proporção
   sustentada, com numerador e denominador; a presença de uma citação é insuficiente.
4. Explicitar prazo e procedimento de retenção/exclusão de índices, minutas,
   métricas e logs, distinguindo exclusão de fontes e preservação de histórico.
5. Fazer a demonstração real de regressão textual e áudio/OCR e consolidar a
   matriz de evidências da entrega. As rodadas históricas permanecem identificadas.

Esses pontos são pendências de validação/governança, não funções-esqueleto das
três partes. Guardrails locais e testes simulados não garantem veracidade de
paráfrases nem qualidade de classificação de um modelo ainda não executado.
