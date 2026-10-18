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
| `llm_client.py` | Única porta para o Gemini: prazo de relógio, `store=False`, erros traduzidos, tokens e custo (RF04) |
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
| `fluxo.py`, `main.py` | Orquestração e linha de comando (RF01) |

## Modelos e ferramentas

| Tarefa | Modelo | Por quê |
|---|---|---|
| Extração, minuta, OCR, transcrição | `gemini-3.8-flash` | Multimodal (texto, PDF, imagem, áudio), saída JSON por esquema, cota gratuita |
| Síntese de voz | `gemini-3.8-flash-tts` | Português suportado, cota gratuita |
| Imagem | `gemini-3.1-flash-lite-image` | Menor preço por imagem; sem cota gratuita |

Provedor único (Google Gemini, SDK `google-genai` 2.31.0, Interactions API), para uma só chave e um só tratamento de erros. A dependência de fornecedor fica contida em `llm_client.py` e nos nomes de modelo do `config.json`.

## Custos medidos

Custo estimado pela tabela da camada paga, válida até 31/12/2026 (fonte: docs oficiais Gemini API, pricing, out/2026). As rodadas de texto, OCR e experimento usaram a camada gratuita, sem custo efetivo; a peça visual foi gerada já na camada paga.

| Execução | Chamadas | Custo estimado (USD) |
|---|---|---|
| `texto-01` (extração + minuta) | 2 | 0,0121 |
| `texto-injection` (extração + minuta) | 2 | 0,0131 |
| `imagem-01` (OCR + extração) | 2 | 0,0178 |
| Experimento de prompts (A, B, C, rodada final) | 3 | 0,0265 |
| Peça visual (imagem 1K) | 1 | 0,0337 |

## Riscos e mitigações

| Risco | Mitigação | Evidência |
|---|---|---|
| Alucinação | Regra "não invente" e "não localizado" no prompt de sistema; dados de referência da minuta copiados dos campos por código; revisão humana | `avaliacao.md`: campos exatos conferem nos dois casos de texto |
| Prompt injection | Conteúdo externo delimitado, com a etiqueta de fechamento neutralizada; minuta sem `motivo_revisao`; conferência de `minuta_nao_pode_conter` | Caso `texto-injection`: nada do ataque na minuta, tentativa sinalizada |
| Erro de leitura (OCR, transcrição) | Texto bruto preservado, trechos incertos, comparação com gabarito, confirmação humana dos dados críticos | `visao_e_imagem.md`: protocolo rasurado lido errado sem aviso do modelo |
| Exposição de dados | Mascaramento, `store=False`, log sem conteúdo, chave só no `.env` | `lgpd_campos.md` |
| Dependência de fornecedor | Provedor isolado em um módulo; modelos no config | Trocar de provedor exige reescrever só `llm_client.py` |
| Serviço indisponível ou cota esgotada | Erros traduzidos em mensagens claras; prazo de relógio por chamada; sem repetição em 429 | Cota zero de imagem retornou "limite de requisições" em menos de 1 s |

## LGPD e avaliação

- Matriz de campos, finalidade, necessidade, risco e riscos residuais: [`lgpd_campos.md`](lgpd_campos.md).
- Protocolo de avaliação, gravidade, resultados por caso e taxa de aprovação: [`avaliacao.md`](avaliacao.md).
- Experimento de prompts: [`experimento_prompts.md`](experimento_prompts.md).
- Visão, OCR e peça visual: [`visao_e_imagem.md`](visao_e_imagem.md).

## Limitações

- Um caso por modalidade, mais o caso de injeção: os resultados mostram comportamento, não estatística.
- A peça visual exige faturamento ativo: geração de imagem não tem cota gratuita.
- Gemini 3.6 ou mais recente ignora `temperature`, então o experimento de prompts não controla amostragem (fonte: docs oficiais Gemini API, text-generation, out/2026).
- Imagem e áudio vão inteiros ao provedor, sem mascaramento possível.
