# Central Inteligente de Atendimento e Comunicação Institucional

Desafio Prático 1 — FIC_DEV, Inteligência Artificial Generativa. O enunciado transcrito está em [enunciado/](enunciado/README.md); o PDF original fica na raiz.

Protótipo local que recebe solicitações fictícias em texto, áudio e imagem, extrai os campos, gera uma minuta de resposta e a deixa aguardando revisão de um servidor. Nada é enviado ao cidadão.

## Instalação

Requer Python 3.10 ou mais recente (exigência do SDK `google-genai`). Testado com Python 3.14.8. Confira com `python3 --version`; o Python que vem com o macOS é 3.9 e não serve. Nesse caso, use o executável de uma versão nova no primeiro comando (por exemplo `python3.14 -m venv .venv`, com Python instalado pelo Homebrew ou por python.org).

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # preencha GEMINI_API_KEY com a chave do Google AI Studio
python -m src.main verificar       # mostra e registra versões, chave e arquivos dos casos
python -m src.main verificar --chamar-api   # opcional: uma chamada curta para testar a chave
```

## Interface gráfica

```bash
python -m src.main interface        # abre em http://127.0.0.1:8000
```

Painel com casos, minutas, peças e taxa de aprovação. Processa um caso, mostra o **original ao lado** dos dados críticos para a confirmação humana, e registra a revisão da minuta e da peça visual. Usa as mesmas funções e o mesmo log da linha de comando, e só escuta em `127.0.0.1`. A interface compilada fica em `interface/dist`, então não precisa de Node para usar. Para alterar a tela: `cd interface && npm install && npm run dev` (Node 20 ou mais recente), com a API rodando em outro terminal, e `npm run build` antes de commitar.

## Execução

```bash
python -m src.main casos                      # lista os casos do config.json
python -m src.main processar texto-01         # entrada -> extração -> compreensão -> minuta
python -m src.main confirmar <id_execucao>    # retoma uma execução parada na confirmação dos dados críticos
python -m src.main revisar <id_execucao>      # aprovar, aprovar com correção, rejeitar ou pedir nova geração
python -m src.main audio-minuta <id_execucao>  # áudio da minuta aprovada (RF07)
python -m src.main avaliacao                  # contagem por status e taxa de aprovação (RF13)
python -m src.main experimento-prompts --entrada dados/experimento_rf02/entrada_texto-01.json  # prompts A, B e C (RF02)
python -m src.main peca-visual imagem-01 --especificacao prompts/peca_visual_v1.json [--imagem-base <imagem>]  # RF10
python -m src.main revisar-peca <id_execucao>  # checklist e decisão sobre a peça (RF10)
python -m pytest                              # testes; não chamam a API
```

Códigos de saída: `0` sucesso, `1` erro de uso (caso, arquivo ou revisão inválidos), `2` erro do provedor (chave, cota, indisponibilidade, timeout), `3` parte ainda não implementada, `130` operação cancelada no terminal.

## Divisão do trabalho

Cada integrante implementa uma modalidade. As funções pendentes levantam `PendenteDeImplementacao` e trazem, na docstring, o que o requisito pede e o formato da chamada ao Gemini.

| Parte | Requisitos | Onde | Situação |
|---|---|---|---|
| Base compartilhada | RF01, RF03 (delimitação e prompt de sistema), RF04, RF11, RF12 (mascaramento), RF13 (revisão e taxa de aprovação) | `config.py`, `llm_client.py`, `prompts.py`, `audit.py`, `privacidade.py`, `entradas.py`, `revisao.py`, `fluxo.py`, `main.py` | pronta, com testes |
| Texto | RF02, RF03 (caso de teste com prompt injection), RF05, RF09 | `extracao.py`, `minuta.py`, `experimento.py`, `prompts/`, `documentacao/experimento_prompts.md` | pronta, com testes |
| Áudio | RF06, RF07 | `audio.py` (`transcrever`, `sintetizar`) | pendente |
| Imagem | RF08, RF10 | `vision.py`, `comparacao.py`, `image_generation.py`, `prompts/ocr_v1.md`, `prompts/peca_visual_v1.json` | pronta, com testes; decisões em `documentacao/visao_e_imagem.md` |
| Todos | RF12 (matriz de dados pessoais), RF13, entregáveis | `documentacao/`, `dados/gabaritos/` | pendente |

Áudio e imagem desembocam em `extrair_campos` e `gerar_minuta`: enquanto a parte de texto não estiver pronta, o fluxo dessas modalidades para na etapa de compreensão. Cada parte pode ser testada isoladamente substituindo as outras, como em `testes/test_fluxo_e_revisao.py`.

O contrato entre as partes é o formato de `TextoExtraido` (`tipos.py`) e o esquema de `extracao.py`. Mudança neles afeta as três modalidades: combinem antes.

## Categorias (RF05)

A extração classifica cada solicitação em uma destas categorias (`categorias` no `config.json`); fora delas, `não localizado`.

| Categoria | Quando usar |
|---|---|
| `matricula` | Efetivação, situação ou regras da matrícula, incluindo os documentos exigidos para ela. |
| `informacao` | Pedido de informação geral que não pede providência. |
| `solicitacao_documentos` | Pedido de emissão de documento, como declaração, histórico ou certificado. |
| `reclamacao` | Manifestação de insatisfação com um serviço ou atendimento. |
| `cancelamento` | Pedido de cancelamento ou trancamento, ou informação sobre como fazer isso. |

## Gabaritos

Cada caso precisa de um resultado esperado escrito antes da execução (seção 6 do enunciado). Copie `dados/gabaritos/_modelo.json` para `dados/gabaritos/<caso>.json`, com o nome que está em `config.json`.

## Decisões e limitações

- **Provedor:** Gemini (Google), via Interactions API do SDK `google-genai` 2.31.0. Modelos em `config.json`: `gemini-3.8-flash` para texto, transcrição e visão; `gemini-3.8-flash-tts` para voz; `gemini-3.1-flash-lite-image` para imagem.
- **Camada gratuita e LGPD:** na camada gratuita o Google usa o conteúdo enviado para melhorar seus produtos; na paga, não (fonte: docs oficiais Gemini API, pricing, out/2026). Os dados do desafio são fictícios. Mesmo assim, o texto é mascarado antes do envio: CPF, RG, e-mail e telefone viram marcadores; a lista fica em `privacidade.mascarar_antes_de_enviar`. Áudio e imagem seguem sem máscara, porque o conteúdo bruto é a própria entrada.
- **Timeout (RF04):** `timeout_segundos` é um prazo de relógio sobre a chamada inteira, aplicado pelo `llm_client.py`. O SDK 2.31.0 repete chamadas esperando o `Retry-After` do servidor sem teto, e `attempts=0` vira 1; num 429 de cota esgotada a CLI travava por minutos. Por isso o cliente só deixa o SDK repetir erros 5xx: o 429 volta na hora como "limite de requisições".
- **Sem armazenamento no provedor:** as chamadas usam `store=False` (`armazenar_no_provedor` no config).
- **Parâmetros do experimento (RF02):** os modelos Gemini 3.6 ou mais recentes ignoram `temperature`, `top_p` e `top_k` (fonte: docs oficiais Gemini API, text-generation, out/2026). O controle disponível é `max_output_tokens`, `seed` e `thinking_level`.
- **Custos estimados:** calculados com os preços da camada paga em `precos_usd_por_milhao_tokens`. Valores vigentes até 31/12/2026 (fonte: docs oficiais Gemini API, pricing, out/2026); a página anuncia preços em dobro para `gemini-3.8-flash` e para os TTS a partir de 01/01/2027. O custo de raciocínio entra como saída. Geração de imagem não tem cota gratuita: US$ 0,0336 por imagem 1K.
- **Erros do provedor:** a Interactions API levanta exceções de um módulo privado do SDK. `llm_client.py` as classifica por atributo (`status_code`, nome da classe), e `testes/test_llm_client.py` importa as classes reais para avisar se o SDK mudar.
- **Chave inválida** chega como HTTP 400 com `API_KEY_INVALID`, não como 401.
- **Rastreabilidade:** `resultados/logs/execucoes.jsonl` guarda referências (arquivo de origem, versão e hash do prompt, parâmetros, caminho da saída), não o conteúdo. Prompt alterado é arquivo novo em `prompts/` (`<nome>_v<N>.md`).
- **Revisão:** o áudio (RF07) só é gerado de minuta aprovada e com o mesmo hash registrado na aprovação. Dados críticos de áudio e imagem (protocolo, data, solicitante) passam por confirmação humana antes da minuta.
- **Minuta (RF09):** o modelo redige só o corpo. Cabeçalho com brasão, órgão e dados de referência e a seção de fontes entram por código, então não dependem do modelo e reaproveitam os dados já confirmados. Os campos vão ao modelo dentro de `<conteudo_externo>` (RF03), sem `motivo_revisao` nem confiança. O prompt de produção é `minuta_v2`: o Prompt B do experimento sem as partes que o código assumiu.
- **Peça visual (RF10):** o modelo gera só a ilustração; o texto e o selo de conteúdo sintético são aplicados com Pillow, para o texto sair exato. Cada peça em `resultados/imagens/` tem ao lado a ilustração original do modelo e um `.json` com prompt, especificação, modelo, data, nota de proveniência e revisão. A composição usa Arial ou DejaVu Sans; sem nenhuma das duas, a peça não é gerada (a fonte embutida do Pillow não tem acentos).
- **Comparação com gabarito (RF06, RF08):** para áudio e imagem, quando o gabarito do caso tem `texto_referencia`, o fluxo grava `comparacao_gabarito.json` com similaridade, acertos por palavra, erros e dados críticos não encontrados.
- **Resposta vazia (RF04):** a checagem vale para o tipo de saída pedido. TTS sem áudio ou geração sem imagem também é erro, mesmo que venha texto.
