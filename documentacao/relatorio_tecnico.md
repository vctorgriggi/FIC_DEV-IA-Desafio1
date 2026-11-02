# Relatório técnico — Central Inteligente de Atendimento e Comunicação Institucional

Protótipo local que recebe solicitações fictícias em texto, áudio e imagem, extrai os campos, gera uma minuta de resposta e a deixa aguardando a decisão de um servidor. Nenhuma resposta é enviada ao cidadão: o código não tem função de envio.

## Arquitetura

```
entrada ─► extração do texto ─► comparação ─► compreensão ─► confirmação ─► minuta ─► revisão humana
(validar)  (texto direto,      com gabarito  (JSON + campos  humana dos     (corpo pelo   (aprovar, corrigir,
           transcrição, OCR)   (áudio, img)  ausentes)       dados críticos  modelo)       rejeitar, gerar de novo)
                                                             (áudio, img)                      │
                                                                                               ├─► áudio da minuta aprovada
                                                                                               └─► peça visual + revisão própria
```

| Módulo | Papel |
|---|---|
| `llm_client.py` | Única porta para a OpenAI: um método por tarefa (texto, transcrição, voz, imagem), prazo de relógio, `store=False`, erros traduzidos, tokens e custo (RF04) |
| `prompts.py` + `prompts/` | Prompts versionados e delimitação do conteúdo externo (RF02, RF03) |
| `entradas.py` | Validação de extensão, tamanho e codificação; hash do original |
| `privacidade.py` | Mascaramento antes do envio e ocultação de segredos (RF12) |
| `extracao.py` | Campos estruturados com esquema JSON e "não localizado" (RF05) |
| `audio.py` | Transcrição e síntese de voz (RF06, RF07) |
| `vision.py` | OCR por visão multimodal (RF08) |
| `comparacao.py`, `avaliacao.py` | Esperado contra obtido (RF06, RF08, RF13) |
| `minuta.py` | Minuta institucional; cabeçalho e fontes por código (RF09) |
| `image_generation.py` | Peça visual com texto aplicado por código e selo de IA (RF10) |
| `revisao.py` | Decisões humanas, checklist da peça e taxa de aprovação (RF13) |
| `audit.py` | Um evento JSON por etapa, sem conteúdo nem segredos (RF11) |
| `fluxo.py`, `main.py` | Orquestração em duas fases (preparar, concluir após a confirmação humana) e linha de comando (RF01) |
| `web.py` + `interface/` | Interface local (FastAPI + Vite/React): original ao lado dos dados na confirmação e na revisão |

## Modelos e ferramentas

| Tarefa | Modelo | Por quê |
|---|---|---|
| Extração, minuta, OCR | `gpt-6.1-terra` | Texto e visão (PDF e imagem), saída JSON por esquema em modo estrito; preço intermediário da família (US$ 1 / 5 por milhão de tokens) |
| Transcrição | `gpt-transcribe` | Modelo de transcrição recomendado pela OpenAI; devolve o idioma detectado; cobrança por minuto |
| Síntese de voz | `gpt-4o-mini-tts` | Único modelo da Speech API com instrução de entonação; português suportado |
| Imagem | `gpt-image-2.5-flare` | Geração cotidiana rápida, mesmo preço por token do modelo maior |

Provedor único (OpenAI, SDK `openai` 3.41.0), para uma só chave e um só tratamento de erros. A dependência de fornecedor fica contida em `llm_client.py` e nos nomes de modelo do `config.json`. Fontes: docs oficiais OpenAI API, models e pricing, out/2026.

## Custos medidos

Custo estimado pela tabela padrão da OpenAI (`precos_usd_por_milhao_tokens` e `precos_usd_por_minuto_audio` no config). A API não tem camada gratuita para esses modelos. Rodada de 31/10/2026:

| Execução | Chamadas | Custo estimado (USD) |
|---|---|---|
| `texto-01` (extração + minuta) | 2 | 0,0044 |
| `texto-injection` (extração + minuta) | 2 | 0,0042 |
| `imagem-01`, três execuções (OCR + extração + minuta, cada) | 9 | 0,0453 |
| `audio-01` (transcrição + extração + minuta) | 3 | 0,0114 |
| `audio-01-ruido`, duas execuções (transcrição + extração, cada) | 4 | 0,0173 |
| Voz das minutas aprovadas do `audio-01` (80,6 s) e do `texto-01` (99,9 s) | 2 | sem estimativa: a Speech API não informa tokens |
| Prompt C gerado pelo metaprompt | 1 | 0,0048 |
| Experimento de prompts (A, B, C) | 3 | 0,0087 |
| Peça visual (1536x1152) | 1 | 0,0229 |
| Verificação dos dois áudios contra o texto aprovado (transcrição de cada WAV) | 2 | 0,0136 |
| **Total registrado no log** | 29 | **0,1326** |

Fora do log ficaram oito sínteses curtas de teste da leitura do protocolo, cada uma com sua transcrição.

## Riscos e mitigações

| Risco | Mitigação | Evidência |
|---|---|---|
| Alucinação | Regra "não invente" e "não localizado" no prompt de sistema; dados de referência da minuta copiados dos campos por código; revisão humana | `avaliacao.md`: protocolo, data e solicitante conferem nos casos de texto; datas atribuídas no fecho foram pegas na revisão |
| Prompt injection | Conteúdo externo delimitado, com a etiqueta de fechamento neutralizada; minuta sem `motivo_revisao`; conferência de `minuta_nao_pode_conter` | Caso `texto-injection`: nada do ataque na minuta, tentativa sinalizada; a categoria extraída saiu errada, como o ataque pedia, sem efeito no texto |
| Erro de leitura (OCR, transcrição) | Texto bruto preservado, trechos incertos, comparação com gabarito, confirmação humana dos dados críticos | `visao_e_imagem.md`: protocolo rasurado marcado como ilegível e preenchido na confirmação |
| Erro da voz sintética | Áudio só de texto aprovado; verificação por transcrição; escuta humana antes do uso | `audio_e_acessibilidade.md`: voz omitiu um zero do protocolo no `audio-01`, pego na verificação e confirmado ouvindo |
| Exposição de dados | Mascaramento, `store=False`, log sem conteúdo, chave só no `.env` | `lgpd_campos.md` |
| Dependência de fornecedor | Provedor isolado em um módulo; modelos no config | Trocar de provedor exige reescrever só `llm_client.py` e os testes dele |
| Serviço indisponível ou cota esgotada | Erros traduzidos em mensagens claras; prazo de relógio por chamada; sem repetição automática do SDK | `testes/test_llm_client.py` |

## LGPD e avaliação

- Matriz de campos, finalidade, necessidade, risco e riscos residuais: [`lgpd_campos.md`](lgpd_campos.md).
- Protocolo de avaliação, gravidade, resultados por caso e taxa de aprovação: [`avaliacao.md`](avaliacao.md).
- Experimento de prompts: [`experimento_prompts.md`](experimento_prompts.md).
- Visão, OCR e peça visual: [`visao_e_imagem.md`](visao_e_imagem.md).
- Áudio e acessibilidade: [`audio_e_acessibilidade.md`](audio_e_acessibilidade.md).

## Limitações

- Um caso por modalidade, mais o caso de injeção e a versão com ruído do áudio: os resultados mostram comportamento, não estatística.
- `gpt-4o-mini-tts` e os demais modelos da Speech API serão desligados em 06/01/2027; o RF07 precisará migrar para a Realtime API.
- O `gpt-transcribe` não aponta trechos incertos na transcrição.
- A amostragem não é fixada no experimento de prompts: não verificamos se `gpt-6.1-terra` aceita `temperature`.
- Imagem e áudio vão inteiros ao provedor, sem mascaramento possível; leitura parcial de CPF pelo OCR escapa do mascaramento.
- Quando uma chamada falha, o evento do log registra o erro e a duração, mas não o modelo nem os tokens (`fluxo._etapa` só anota o modelo a partir de uma resposta).

# Desafio 2 — assistente de documentos

A mesma central passa a fundamentar a minuta num acervo fictício indexado. Estado da entrega, métricas com numerador e denominador, matriz T01–T15 e decisões do operador: [`desafio-2/integracao.md`](desafio-2/integracao.md). Decisões e resultados de cada parte: [`integrante-1.md`](desafio-2/integrante-1.md) (dados, RF14, RF15), [`integrante-2.md`](desafio-2/integrante-2.md) (índice, RAG, RF17–RF19, RF21, retenção) e [`guardrails-sentimentos.md`](desafio-2/guardrails-sentimentos.md) (RF16, RF20, RF22).

## Arquitetura

```
solicitação (texto, ou áudio/imagem do Desafio 1 via transcrição/OCR)
  → guardrails.verificar_entrada            permitir | revisar | bloquear
  → nlp: extração validada por esquema (RF14) e ficha de compreensão (RF15)
  → rag.recuperar: top-k no índice Chroma (embeddings, chunking B)
  → rag.separar_trechos: trecho com instrução embutida tira o documento do contexto
  → rag.gerar_minuta: fatos do caso e trechos delimitados em blocos separados
  → conferência por código (fontes, status, números) + guardrails.verificar_saida
  → RegistroMinutaRAG "pendente" ou "bloqueada" em resultados/minutas_rag/
  → decisão do operador no Streamlit (revisao.registrar_decisao_rag)
avaliações → sentiment.classificar_lote → metrics.agregar_sentimentos → painel
```

Toda chamada ao provedor passa por `ClienteLLM` (timeout, uma repetição em falha transitória, teto de chamadas e tokens por execução via `guardrails.ControleRecursos`). Cada etapa vira evento em `resultados/logs/execucoes.jsonl` com o `id_execucao`, versão do esquema e do prompt, consulta minimizada, ids recuperados e enviados ao modelo, versão do índice, tokens, custo, duração, erro e decisão humana.

## Provedor configurável

Provedor, modelos e parâmetros ficam em `config.json`; a geração tem perfis (`principal`: `gpt-6.1-terra`; `alternativo`: `gpt-6-luna`) e o embedding tem modelo próprio (`text-embedding-3-small`, 1536 dimensões). Trocar o perfil não toca o índice: demonstrado com o `alternativo` sobre o mesmo índice, 1 texto embedado (a consulta) e 12 trechos antes e depois. Os dois perfis são do mesmo provedor; não há alegação de qualidade equivalente entre eles. Mudar o modelo de embedding exige reindexar, e o índice recusa abrir com outro modelo ou chunking.

## Métricas e custos medidos

Resumo das rodadas reais; detalhes e evidências em `desafio-2/integracao.md`.

| Rodada | Resultado | Custo estimado |
|---|---|---|
| NLP, seis solicitações (Integrante 1) | categoria 5/6 contra o gabarito original | US$ 0,0454 |
| Chunking A × B, cinco perguntas | acerto 5/5 e 5/5 | não registrado (só embeddings) |
| Oito perguntas, B, `principal` | status 8/8, abstenção 2/2 | US$ 0,0199 |
| Oito perguntas, B, `alternativo` | status 8/8, abstenção 2/2 | US$ 0,0025 |
| Sentimentos, 12 avaliações | 11/12; ambíguas com revisão 2/3 | US$ 0,0107 |
| Fluxo integrado: seis solicitações, três ataques, dois casos do Desafio 1 | S01–S04 fundamentadas com a fonte esperada; S05/S06 em revisão; A01/A03 bloqueados; DOC-06 fora do contexto | US$ 0,0986 |
| Oito perguntas pelo fluxo, com registro para decisão | status 8/8; 11/11 respostas com todas as afirmações sustentadas | US$ 0,0217 |
| Regressão do Desafio 1 (texto-01, imagem-01) | texto aprovado com correção do fecho; imagem com protocolo confirmado e aprovada | US$ 0,0205 |

Preços e fonte como no Desafio 1 (`precos_usd_por_milhao_tokens`). Embeddings entram no custo quando a resposta traz `usage`.

## Privacidade e retenção

Só dados fictícios; os editais reais de `enunciado/desafio-2/arquivos/` não são indexados. Todo texto enviado ao provedor passa por `rag.minimizar` (mascaramento de CPF, RG, e-mail e telefone e ocultação de formato de credencial), e a Responses API recebe `store=False`. O log guarda referências e a consulta minimizada, nunca o texto dos trechos. Retenção e exclusão de documentos, vetores, minutas e logs: tabela em [`integrante-2.md`](desafio-2/integrante-2.md#retenção-e-exclusão-rf24); a exclusão de DOC-05 foi demonstrada (sai da busca, do manifesto e das duas coleções, com evento de auditoria). A minuta é sempre marcada como texto gerado por IA, com o modelo lido da auditoria.

## Limitações do Desafio 2

- Acervo de 12 trechos: os acertos não estimam desempenho em documentos reais.
- Guardrails por regras locais: ataque parafraseado ou ofuscado pode passar; pedido legítimo pode cair em revisão.
- A conferência automática da resposta compara fontes e algarismos; paráfrase errada sem número fica para a revisão humana. As 20 afirmações institucionais da rodada final foram conferidas uma a uma contra a passagem citada.
- AV-11 (avaliação mista) saiu negativa sem revisão; mantido o `sentimento_v1` e registrado o limite.
- Decisões do operador na rodada final: 9 aprovadas, 7 em revisão, 1 rejeitada (`desafio-2/integracao.md`).
- Duas minutas (S02, S04) terminam com uma frase interna ("Esta minuta permanece pendente…") e voltaram para revisão: o prompt `minuta_rag_d2_v1` não proíbe isso.

## Uso de IA no desenvolvimento

Registro em [`uso_de_ia.md`](uso_de_ia.md).
