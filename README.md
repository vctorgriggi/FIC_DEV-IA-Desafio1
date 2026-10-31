# Central Inteligente de Atendimento e Comunicação Institucional

Desafio Prático 1 — FIC_DEV, Inteligência Artificial Generativa. Os enunciados transcritos, com os PDFs originais, estão em [enunciado/](enunciado/README.md): o do Desafio 1 e o do Desafio 2, que evolui este mesmo projeto.

Protótipo local que recebe solicitações fictícias em texto, áudio e imagem, extrai os campos, gera uma minuta de resposta e a deixa aguardando revisão de um servidor. Nada é enviado ao cidadão.

## Instalação

Requer Python 3.11 ou mais recente (exigência do Pillow 13 e do Starlette; o SDK `openai` aceita 3.10). Testado com Python 3.14.8. Confira com `python3 --version`; o Python que vem com o macOS é 3.9 e não serve. Nesse caso, use o executável de uma versão nova no primeiro comando (por exemplo `python3.14 -m venv .venv`, com Python instalado pelo Homebrew ou por python.org).

O caso de áudio também precisa do FFmpeg (`ffprobe` no PATH): `brew install ffmpeg` no macOS, `sudo apt install ffmpeg` no Linux ou o instalador de ffmpeg.org no Windows. Confira com `ffprobe -version`.

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # Windows: copy .env.example .env; preencha OPENAI_API_KEY (chave da API da OpenAI)
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
3. **Revisar a minuta.** Leia a minuta ao lado do original, veja a conferência automática com o gabarito e escolha **Aprovar**, **Aprovar com correção** (abre um editor do texto; o cabeçalho não pode ser alterado, e a versão gerada pelo modelo fica guardada como `<id>_gerada.md`), **Rejeitar** ou **Pedir nova geração**, com justificativa e revisor. Nada é enviado ao cidadão.
4. **Áudio da minuta** (só minuta aprovada). Botão **Gerar áudio** na página da minuta (RF07). Depois, **Comparar áudio com o texto aprovado**, ouça o áudio inteiro, com atenção a protocolo e datas, e registre se ele confere.
5. **Peça visual.** **Gerar peça visual** no cartão do caso (cobrada por tokens; a estimativa fica no log); depois responda ao checklist e registre a decisão.
6. **Indicadores.** O painel mostra a taxa de aprovação; `python -m src.main avaliacao` grava o esperado contra obtido em `resultados/logs/avaliacao.json`.

O mesmo fluxo pelo terminal:

```bash
python -m src.main processar imagem-01        # lê, extrai, pergunta os dados críticos e gera a minuta
python -m src.main revisar <id_execucao>      # o id aparece no fim do comando anterior
python -m src.main audio-minuta <id_execucao>
python -m src.main verificar-audio <id_execucao>
python -m src.main revisar-audio <id_execucao>
python -m src.main avaliacao
```

Tudo o que é gerado fica em `resultados/` (minutas, áudios, imagens, logs) e em `dados/processados/<caso>/<id_execucao>/` (texto lido, campos extraídos, comparação com o gabarito).

## Referência de comandos

```bash
python -m src.main casos                      # lista os casos do config.json
python -m src.main processar texto-01         # entrada -> extração -> compreensão -> minuta
python -m src.main confirmar <id_execucao>    # retoma uma execução parada na confirmação dos dados críticos
python -m src.main descartar <id_execucao> --justificativa "..." --revisor "..."  # tira da fila uma execução parada, com registro no log
python -m src.main revisar <id_execucao>      # aprovar, aprovar com correção (texto corrigido lido de um arquivo), rejeitar ou pedir nova geração
python -m src.main audio-minuta <id_execucao>  # áudio da minuta aprovada (RF07)
python -m src.main verificar-audio <id_execucao>  # transcreve o áudio e compara com o texto aprovado (RF07)
python -m src.main revisar-audio <id_execucao>    # registra se o áudio ouvido confere (RF07)
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
| `pip install` falha no `pillow` ou no `openai` | Python abaixo de 3.11 (o do macOS é 3.9). Crie o `.venv` com um Python novo, como em Instalação. |
| "Chave da API não configurada" | Falta o `.env`. Copie o `.env.example` e preencha `OPENAI_API_KEY` com uma chave da API da OpenAI. |
| "O provedor recusou a chave da API" | Chave errada ou revogada no `.env`, ou sem acesso ao modelo configurado. |
| "Limite de requisições ou cota do provedor atingido" | A API não tem camada gratuita: confira o faturamento do projeto da chave. Com faturamento ativo, é limite de taxa: aguarde alguns minutos. |
| "A resposta do modelo foi cortada pelo limite de tokens" | Aumente `max_output_tokens` em `parametros_geracao` no `config.json`. |
| "ffprobe não encontrado" ao processar áudio | Falta o FFmpeg: instale como em Instalação e confira com `ffprobe -version`. |
| A interface não abre porque a porta está em uso | `python -m src.main interface --porta 8001`. |
| O navegador mostra "Interface não compilada" | `interface/dist` foi apagado: rode `npm install && npm run build` em `interface/`. |

## Requisitos e onde estão

| Parte | Requisitos | Código | Situação |
|---|---|---|---|
| Base | RF01, RF03 (delimitação e prompt de sistema), RF04, RF11, RF12 (mascaramento), RF13 | `config.py`, `llm_client.py`, `prompts.py`, `audit.py`, `privacidade.py`, `entradas.py`, `revisao.py`, `avaliacao.py`, `fluxo.py`, `main.py`, `web.py` | pronta, com testes |
| Texto | RF02, RF03 (caso de prompt injection), RF05, RF09 | `extracao.py`, `minuta.py`, `experimento.py`, `prompts/` | pronta, com testes |
| Áudio | RF06, RF07 | `audio.py` | pronta, com testes |
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

- **Provedor:** OpenAI, via SDK `openai` 3.41.0. Modelos em `config.json`: `gpt-6.1-terra` para texto e visão (Responses API); `gpt-transcribe` para transcrição; `gpt-4o-mini-tts` para voz; `gpt-image-2.5-flare` para imagem.
- **Rodada final:** 31/10/2026, com a OpenAI. Saídas em `resultados/` e `dados/processados/`, decisões humanas no log e resultados em `documentacao/`. Os testes automatizados usam um SDK falso e não chamam a API.
- **Dados enviados e LGPD:** por padrão, a OpenAI não usa dados enviados pela API para treinar modelos, e guarda registros por até 30 dias para monitoramento de abuso (fonte: docs oficiais OpenAI API, your-data, out/2026). Os dados do desafio são fictícios. Mesmo assim, o texto é mascarado antes do envio: CPF, RG, e-mail e telefone viram marcadores; a lista fica em `privacidade.mascarar_antes_de_enviar`. Áudio e imagem seguem sem máscara, porque o conteúdo bruto é a própria entrada.
- **Timeout (RF04):** `timeout_segundos` é um prazo de relógio sobre a chamada inteira, aplicado pelo `llm_client.py`. O cliente é criado com `max_retries=0`: por padrão o SDK repete 408, 409, 429 e 5xx, e num 429 de cota esgotada isso só atrasa a mesma recusa. O 429 volta na hora como "limite de requisições".
- **Sem armazenamento no provedor:** a Responses API recebe `store=False` (`armazenar_no_provedor` no config). Transcrição, voz e imagem não têm esse parâmetro.
- **Parâmetros do experimento (RF02):** os três prompts usam o mesmo modelo, o mesmo prompt de sistema e o mesmo `max_output_tokens`. Não verificamos se `gpt-6.1-terra` aceita `temperature`; o raciocínio é controlado por `reasoning.effort`, que fica no padrão do modelo.
- **Custos estimados:** calculados com os preços padrão em `precos_usd_por_milhao_tokens` (texto e imagem, por token) e `precos_usd_por_minuto_audio` (transcrição), conforme a tabela de preços consultada em out/2026 (fonte: docs oficiais OpenAI API, pricing, out/2026). A API não tem camada gratuita para esses modelos. O raciocínio já vem contado em `output_tokens` e é cobrado como saída. A voz (Speech API) não informa tokens, então fica sem estimativa; a imagem só tem estimativa quando a resposta traz `usage`.
- **Erros do provedor:** `llm_client.py` classifica as exceções do SDK por atributo (`status_code`, nome da classe), e `testes/test_llm_client.py` usa as classes reais do SDK.
- **Saída JSON (RF05, RF08):** Structured Outputs em modo estrito. `formato_json` acrescenta `additionalProperties: false` a todo objeto do esquema, exigência do modo estrito.
- **Rastreabilidade:** `resultados/logs/execucoes.jsonl` guarda referências (arquivo de origem, versão e hash do prompt, parâmetros, caminho da saída), não o conteúdo. Prompt alterado é arquivo novo em `prompts/` (`<nome>_v<N>.md`).
- **Fluxo em duas fases:** `preparar_caso` vai até a extração dos campos e grava o estado; `concluir_caso` registra a confirmação humana e gera a minuta. Uma execução interrompida na confirmação pode ser retomada (`confirmar` ou interface).
- **Limite de tokens:** `max_output_tokens` é 25000, a reserva que a documentação recomenda para raciocínio e saída, porque o raciocínio conta no limite (fonte: docs oficiais OpenAI API, reasoning, out/2026). Resposta cortada gera um erro próprio, e não "fora do formato".
- **Revisão:** o áudio (RF07) só é gerado de minuta aprovada e com o mesmo hash registrado na aprovação. Dados críticos de áudio e imagem (protocolo, data, solicitante) passam por confirmação humana antes da minuta.
- **Minuta (RF09):** o modelo redige só o corpo. Cabeçalho com brasão, órgão e dados de referência e a seção de fontes entram por código, então não dependem do modelo e reaproveitam os dados já confirmados. Os campos vão ao modelo dentro de `<conteudo_externo>` (RF03), sem `motivo_revisao` nem confiança. O prompt de produção é `minuta_v3`: o Prompt B do experimento sem as partes que o código assumiu e com a proibição de afirmar ações que não constam dos dados, como encaminhamento ou análise.
- **Peça visual (RF10):** o modelo gera só a ilustração; o texto e o selo de conteúdo sintético são aplicados com Pillow, para o texto sair exato. Cada peça em `resultados/imagens/` tem ao lado a ilustração original do modelo e um `.json` com prompt, especificação, modelo, data, nota de proveniência e revisão. A composição usa Arial ou DejaVu Sans; sem nenhuma das duas, a peça não é gerada (a fonte embutida do Pillow não tem acentos). A API recebe tamanho em pixels, não proporção: `image_generation.TAMANHOS` converte a proporção da especificação.
- **Comparação com gabarito (RF06, RF08):** para áudio e imagem, quando o gabarito do caso tem `texto_referencia`, o fluxo grava `comparacao_gabarito.json` com similaridade, acertos por palavra, erros e dados críticos não encontrados.
- **Resposta vazia (RF04):** a checagem vale para o tipo de saída pedido. TTS sem áudio ou geração sem imagem também é erro, mesmo que venha texto.

## Áudio (RF06 e RF07)

Requer o FFmpeg (`ffprobe`), como em Instalação. O arquivo é inspecionado inteiro pelo `ffprobe` antes de qualquer envio; a duração registrada vem dele. A versão revisada da transcrição só ajusta espaços, inclusive juntando dígitos ditados um a um, para que CPF, RG e protocolo sejam mascarados e comparados.

`gpt-transcribe` devolve o texto e os idiomas detectados, mas não aponta trechos incertos: `trechos_incertos` fica vazio no áudio, e a conferência humana dos dados críticos e a comparação com o gabarito cobrem essa lacuna. Os idiomas esperados vão ao modelo como dica (`audio.idiomas` no config).

A voz sai só de minuta aprovada e inalterada. Se a minuta tem "não localizado", ela já é gerada com o aviso de lacunas, que é revisado e aprovado junto com o texto; sem o aviso, a síntese é bloqueada. Imagens não são lidas. A locução aceita até 4096 caracteres, limite da Speech API. A saída é um WAV validado que nunca sobrescreve áudio anterior.

`gpt-4o-mini-tts` e os demais modelos da Speech API estão descontinuados e serão desligados em 06/01/2027; o substituto indicado (`gpt-realtime-2.1-mini`) só funciona pela Realtime API (fonte: docs oficiais OpenAI API, text-to-speech, out/2026). Depois dessa data, o RF07 precisa de outra rota.

O gabarito `dados/gabaritos/audio-01.json` foi validado por quem ouviu o original (`validado_por_humano: true`); sem essa marca, a comparação fica registrada como pendente. Regras, resultados reais e limites em [`documentacao/audio_e_acessibilidade.md`](documentacao/audio_e_acessibilidade.md).
