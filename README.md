# Central Inteligente de Atendimento e Comunicação Institucional

Desafio Prático 1 — FIC_DEV, Inteligência Artificial Generativa. O enunciado transcrito está em [enunciado/](enunciado/README.md); o PDF original fica na raiz.

Protótipo local que recebe solicitações fictícias em texto, áudio e imagem, extrai os campos, gera uma minuta de resposta e a deixa aguardando revisão de um servidor. Nada é enviado ao cidadão.

## Instalação

Requer Python 3.10 ou mais recente (exigência do SDK `google-genai`). Testado com Python 3.14.8. Confira com `python3 --version`; o Python que vem com o macOS é 3.9 e não serve. Nesse caso, use o executável de uma versão nova no primeiro comando (por exemplo `python3.14 -m venv .venv`, com Python instalado pelo Homebrew ou por python.org).

O caso de áudio também precisa do FFmpeg (`ffprobe` no PATH): `brew install ffmpeg` no macOS, `sudo apt install ffmpeg` no Linux ou o instalador de ffmpeg.org no Windows. Confira com `ffprobe -version`.

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # Windows: copy .env.example .env; preencha GEMINI_API_KEY (Google AI Studio)
python -m src.main verificar       # mostra e registra versões, chave e arquivos dos casos
python -m src.main verificar --chamar-api   # opcional: uma chamada curta para testar a chave
```

## Interface gráfica

```bash
python -m src.main interface        # abre em http://127.0.0.1:8000
```

Painel com casos, minutas, peças e taxa de aprovação. Processa um caso, mostra o **original ao lado** dos dados críticos para a confirmação humana, e registra a revisão da minuta e da peça visual. Usa as mesmas funções e o mesmo log da linha de comando, e só escuta em `127.0.0.1`. A interface compilada fica em `interface/dist`, então não precisa de Node para usar. Para alterar a tela: `cd interface && npm install && npm run dev` (Node 20 ou mais recente), com a API rodando em outro terminal, e `npm run build` antes de commitar.

## Como usar, passo a passo

Pela interface (`python -m src.main interface`, em http://127.0.0.1:8000):

1. **Processar um caso.** No painel, clique em **Processar** no cartão do caso. Leva cerca de 30 s.
2. **Conferir os dados críticos** (só áudio e imagem). Compare protocolo, data e solicitante com o original exibido ao lado, corrija o que estiver errado, informe quem conferiu e clique em **Confirmar e gerar minuta**. O modelo pode errar sem marcar dúvida: confira olhando o original.
3. **Revisar a minuta.** Leia a minuta ao lado do original, veja a conferência automática com o gabarito e escolha **Aprovar**, **Aprovar com correção** (abre um editor do texto), **Rejeitar** ou **Pedir nova geração**, com justificativa e revisor. Nada é enviado ao cidadão.
4. **Áudio da minuta** (só minuta aprovada). Botão **Gerar áudio** na página da minuta (RF07).
5. **Peça visual.** **Gerar peça visual** no cartão do caso (modelo pago, cerca de US$ 0,03); depois responda ao checklist e registre a decisão.
6. **Indicadores.** O painel mostra a taxa de aprovação; `python -m src.main avaliacao` grava o esperado contra obtido em `resultados/logs/avaliacao.json`.

O mesmo fluxo pelo terminal:

```bash
python -m src.main processar imagem-01        # lê, extrai, pergunta os dados críticos e gera a minuta
python -m src.main revisar <id_execucao>      # o id aparece no fim do comando anterior
python -m src.main audio-minuta <id_execucao>
python -m src.main avaliacao
```

Tudo o que é gerado fica em `resultados/` (minutas, áudios, imagens, logs) e em `dados/processados/<caso>/<id_execucao>/` (texto lido, campos extraídos, comparação com o gabarito).

## Referência de comandos

```bash
python -m src.main casos                      # lista os casos do config.json
python -m src.main processar texto-01         # entrada -> extração -> compreensão -> minuta
python -m src.main confirmar <id_execucao>    # retoma uma execução parada na confirmação dos dados críticos
python -m src.main revisar <id_execucao>      # aprovar, aprovar com correção, rejeitar ou pedir nova geração
python -m src.main audio-minuta <id_execucao>  # áudio da minuta aprovada (RF07)
python -m src.main avaliacao                  # esperado contra obtido por caso e taxa de aprovação (RF13)
python -m src.main gerar-prompt-c              # gera o Prompt C a partir do metaprompt (RF02), se ainda não existir
python -m src.main experimento-prompts --entrada dados/experimento_rf02/entrada_texto-01.json  # prompts A, B e C (RF02)
python -m src.main peca-visual imagem-01 --especificacao prompts/peca_visual_v1.json [--imagem-base <imagem>]  # RF10
python -m src.main revisar-peca <id_execucao>  # checklist e decisão sobre a peça (RF10)
python -m pytest                              # testes; não chamam a API
```

Códigos de saída: `0` sucesso, `1` erro de uso (caso, arquivo ou revisão inválidos), `2` erro do provedor (chave, cota, indisponibilidade, timeout), `3` parte ainda não implementada, `130` operação cancelada no terminal.

## Problemas comuns

| Sintoma | Causa e solução |
|---|---|
| `pip install` falha no `google-genai` | Python abaixo de 3.10 (o do macOS é 3.9). Crie o `.venv` com um Python novo, como em Instalação. |
| "Chave da API não configurada" | Falta o `.env`. Copie o `.env.example` e preencha `GEMINI_API_KEY` com uma chave criada em https://aistudio.google.com/api-keys. |
| "O provedor recusou a chave da API" | Chave errada ou revogada no `.env`. |
| "Limite de requisições ou cota do provedor atingido" ao gerar a peça visual | Geração de imagem não tem cota gratuita: no Google AI Studio, abra o projeto da chave e use **Set up billing**. Nas outras etapas, aguarde alguns minutos. |
| "A resposta do modelo foi cortada pelo limite de tokens" | Aumente `max_output_tokens` em `parametros_geracao` no `config.json`. |
| "Pendente: RF06 ainda não implementado" | Parte que ainda levanta `PendenteDeImplementacao` (código de saída 3). |
| "ffprobe não encontrado" ao processar áudio | Falta o FFmpeg: instale como em Instalação e confira com `ffprobe -version`. |
| A interface não abre porque a porta está em uso | `python -m src.main interface --porta 8001`. |
| O navegador mostra "Interface não compilada" | `interface/dist` foi apagado: rode `npm install && npm run build` em `interface/`. |

## Requisitos e onde estão

| Parte | Requisitos | Código | Situação |
|---|---|---|---|
| Base | RF01, RF03 (delimitação e prompt de sistema), RF04, RF11, RF12 (mascaramento), RF13 | `config.py`, `llm_client.py`, `prompts.py`, `audit.py`, `privacidade.py`, `entradas.py`, `revisao.py`, `avaliacao.py`, `fluxo.py`, `main.py`, `web.py` | pronta, com testes |
| Texto | RF02, RF03 (caso de prompt injection), RF05, RF09 | `extracao.py`, `minuta.py`, `experimento.py`, `prompts/` | pronta, com testes |
| Áudio | RF06, RF07 | `audio.py`, `prompts/transcricao_v1.md` | implementada, com testes simulados; aceite real pendente — [documentação](documentacao/audio_e_acessibilidade.md) |
| Imagem | RF08, RF10 | `vision.py`, `comparacao.py`, `image_generation.py`, `prompts/ocr_v1.md`, `prompts/peca_visual_v1.json` | pronta, com testes |

As três modalidades terminam na mesma extração de campos e na mesma minuta. O contrato entre elas é o formato de `TextoExtraido` (`tipos.py`) e o esquema de `extracao.py`.

## Documentação da entrega

Em [`documentacao/`](documentacao/README.md): relatório técnico, experimento de prompts (RF02), visão, OCR e peça visual (RF08, RF10), matriz LGPD (RF12), avaliação com as decisões humanas e a taxa de aprovação (RF13) e registro do uso de IA. As saídas da rodada final ficam em `resultados/` e `dados/processados/`.

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

Cada caso tem um resultado esperado escrito antes da execução (seção 6 do enunciado), em `dados/gabaritos/<caso>.json`. Para um caso novo, copie `dados/gabaritos/_modelo.json` com o nome que está em `config.json`.

## Decisões e limitações

- **Provedor:** Gemini (Google), via Interactions API do SDK `google-genai` 2.31.0. Modelos em `config.json`: `gemini-3.8-flash` para texto, transcrição e visão; `gemini-3.8-flash-tts` para voz; `gemini-3.1-flash-lite-image` para imagem.
- **Camada gratuita e LGPD:** na camada gratuita o Google usa o conteúdo enviado para melhorar seus produtos; na paga, não (fonte: docs oficiais Gemini API, pricing, out/2026). Os dados do desafio são fictícios. Mesmo assim, o texto é mascarado antes do envio: CPF, RG, e-mail e telefone viram marcadores; a lista fica em `privacidade.mascarar_antes_de_enviar`. Áudio e imagem seguem sem máscara, porque o conteúdo bruto é a própria entrada.
- **Timeout (RF04):** `timeout_segundos` é um prazo de relógio sobre a chamada inteira, aplicado pelo `llm_client.py`. O SDK 2.31.0 repete chamadas esperando o `Retry-After` do servidor sem teto, e `attempts=0` vira 1; num 429 de cota esgotada a CLI travava por minutos. Por isso o cliente só deixa o SDK repetir erros 5xx: o 429 volta na hora como "limite de requisições".
- **Sem armazenamento no provedor:** as chamadas usam `store=False` (`armazenar_no_provedor` no config).
- **Parâmetros do experimento (RF02):** os modelos Gemini 3.6 ou mais recentes ignoram `temperature`, `top_p` e `top_k` (fonte: docs oficiais Gemini API, text-generation, out/2026). O controle disponível é `max_output_tokens`, `seed` e `thinking_level`.
- **Custos estimados:** calculados com os preços da camada paga em `precos_usd_por_milhao_tokens`. Valores vigentes até 31/12/2026 (fonte: docs oficiais Gemini API, pricing, out/2026); a página anuncia preços em dobro para `gemini-3.8-flash` e para os TTS a partir de 01/01/2027. O custo de raciocínio entra como saída. Geração de imagem não tem cota gratuita: US$ 0,0336 por imagem 1K. Custos medidos de cada execução: `documentacao/relatorio_tecnico.md`.
- **Erros do provedor:** a Interactions API levanta exceções de um módulo privado do SDK. `llm_client.py` as classifica por atributo (`status_code`, nome da classe), e `testes/test_llm_client.py` importa as classes reais para avisar se o SDK mudar.
- **Chave inválida** chega como HTTP 400 com `API_KEY_INVALID`, não como 401.
- **Rastreabilidade:** `resultados/logs/execucoes.jsonl` guarda referências (arquivo de origem, versão e hash do prompt, parâmetros, caminho da saída), não o conteúdo. Prompt alterado é arquivo novo em `prompts/` (`<nome>_v<N>.md`).
- **Fluxo em duas fases:** `preparar_caso` vai até a extração dos campos e grava o estado; `concluir_caso` registra a confirmação humana e gera a minuta. Uma execução interrompida na confirmação pode ser retomada (`confirmar` ou interface).
- **Limite de tokens:** `max_output_tokens` é 8192 porque o raciocínio do modelo conta no limite; com 4096, o JSON do OCR chegou cortado. Resposta cortada gera um erro próprio, e não "fora do formato".
- **Revisão:** o áudio (RF07) só é gerado de minuta aprovada e com o mesmo hash registrado na aprovação. Dados críticos de áudio e imagem (protocolo, data, solicitante) passam por confirmação humana antes da minuta.
- **Minuta (RF09):** o modelo redige só o corpo. Cabeçalho com brasão, órgão e dados de referência e a seção de fontes entram por código, então não dependem do modelo e reaproveitam os dados já confirmados. Os campos vão ao modelo dentro de `<conteudo_externo>` (RF03), sem `motivo_revisao` nem confiança. O prompt de produção é `minuta_v2`: o Prompt B do experimento sem as partes que o código assumiu.
- **Peça visual (RF10):** o modelo gera só a ilustração; o texto e o selo de conteúdo sintético são aplicados com Pillow, para o texto sair exato. Cada peça em `resultados/imagens/` tem ao lado a ilustração original do modelo e um `.json` com prompt, especificação, modelo, data, nota de proveniência e revisão. A composição usa Arial ou DejaVu Sans; sem nenhuma das duas, a peça não é gerada (a fonte embutida do Pillow não tem acentos).
- **Comparação com gabarito (RF06, RF08):** para áudio e imagem, quando o gabarito do caso tem `texto_referencia`, o fluxo grava `comparacao_gabarito.json` com similaridade, acertos por palavra, erros e dados críticos não encontrados.
- **Resposta vazia (RF04):** a checagem vale para o tipo de saída pedido. TTS sem áudio ou geração sem imagem também é erro, mesmo que venha texto.

## Áudio — RF06 e RF07

RF06 requer **FFmpeg/ffprobe no PATH** (Aula 05); a aplicação não instala ferramentas
nem envia áudio se a inspeção falhar. Formatos: MP3, WAV, M4A, OGG e FLAC,
com limite configurado de 20 MiB e limite adicional da requisição inline completa.
Configure voz, estilo e timeout local em `config.json`, seção `audio`.

```bash
ffprobe -version
python -m unittest testes.test_audio -v   # testes simulados, sem API
python -m pytest                         # suíte completa, sem API
# Com chave, cota/custos autorizados e ffprobe disponível:
python -m src.main processar audio-01
python -m src.main revisar <id_execucao>
python -m src.main audio-minuta <id_execucao>
```

`dados/gabaritos/audio-01.json` é um modelo **não validado**. Ouça o original,
preencha referência independente, autoria, data e valores críticos literais;
marque `validado_por_humano: true` só depois da conferência. A ausência de
referência válida é registrada como comparação pendente e não impede processar.
Nomes, protocolos e datas continuam sujeitos à confirmação humana antes da minuta.

Minutas com “não localizado” precisam conter, **antes da aprovação**, o aviso:
“Os campos identificados como não localizado representam informações ausentes no documento.”
Se faltar, a síntese é bloqueada: edite a minuta enquanto aguarda revisão e então
aprove. Se já estiver aprovada, gere/revise outra execução; não edite os metadados
para contornar o hash. Nenhum aviso é acrescentado automaticamente ao áudio.

O TTS salva WAV PCM validado, não sobrescreve áudio anterior e mantém telemetria
nos metadados e log. Texto complexo (HTML, tabelas, código, comandos vocais)
precisa ser preparado como texto simples e revisto. Regras, limites, custos,
bloqueios do ambiente e resultados em [áudio e acessibilidade](documentacao/audio_e_acessibilidade.md)
e no [relatório de implementação](documentacao/RELATORIO_IMPLEMENTACAO_AUDIO.md).
