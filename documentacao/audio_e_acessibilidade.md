# Áudio e acessibilidade (RF06 e RF07)

Transcrição da mensagem de voz (RF06) e versão falada da minuta aprovada (RF07), em `src/audio.py`. As duas chamadas passam pelo `ClienteLLM` (timeout, erros traduzidos, custo), como todo o projeto.

## Base nas aulas

- Aula 05: STT e TTS, revisão humana, pronúncia, entonação, FFmpeg e `ffprobe`.
- Aulas 03 e 04: prompt seguro, configuração, timeout e cliente centralizado.
- Sem biblioteca Python nova além do SDK `openai`: `subprocess`, `wave` e `hashlib` da biblioteca padrão, mais o `ffprobe` como ferramenta de sistema.

## Configuração

Requer FFmpeg com `ffprobe` no PATH (ver Instalação no README). Em `config.json`:

- `modelos.transcricao`: `gpt-transcribe`; `modelos.tts`: `gpt-4o-mini-tts`;
- `audio.idiomas`: `["pt"]`, enviado ao modelo de transcrição como dica de idioma;
- `audio.voz`: `marin` (voz predefinida); `audio.estilo`: português do Brasil, tom institucional, claro e pausado, protocolo lido algarismo por algarismo, sem acréscimos, enviado como instrução de entonação;
- `audio.timeout_inspecao_s`: 30 s para o `ffprobe`; o timeout da API é o `timeout_segundos` geral.

Formatos aceitos: MP3, WAV, M4A, OGG e FLAC, até 20 MB (`entradas.audio` no config; o limite da API é 25 MB).

## RF06 — Transcrição

1. **Validação:** extensão, tamanho e hash (`entradas.py`); depois o `ffprobe -count_frames` percorre o arquivo inteiro e exige stream de áudio, frames, duração positiva e contêiner compatível com a extensão. Qualquer falha bloqueia o envio. O hash é conferido de novo depois da inspeção.
2. **Transcrição:** `gpt-transcribe`, pela API de transcrição. O modelo transcreve a fala e não segue instruções; o texto resultante entra na extração dentro de `<conteudo_externo>`, como qualquer texto do cidadão. A resposta traz o texto e os idiomas detectados.
3. **Trechos incertos:** o `gpt-transcribe` não aponta leituras duvidosas, então `trechos_incertos` fica vazio no áudio. A confirmação humana dos dados críticos, com o áudio ao lado, e a comparação com o gabarito cobrem essa lacuna.
4. **Versão revisada:** só ajusta espaços e quebras de linha, sem trocar nenhum caractere. Isso inclui juntar dígitos ditados um a um ("1 2 3 4 5 6 7 8 9 - 0 0" vira "123456789-00"): separados, CPF, RG e protocolo escapariam do mascaramento e da comparação com o gabarito.
5. **Registro:** idioma detectado, idiomas indicados, modelo, duração do áudio (medida localmente pelo `ffprobe`) e latência da chamada ficam em `dados/processados/audio-01/<id>/extracao_texto.json` e no log.
6. **Comparação:** só com gabarito marcado `validado_por_humano: true`, com texto de referência, autoria, data e dados críticos preenchidos. Sem isso, a etapa registra "comparação pendente" e não grava métricas. A similaridade e a taxa de acerto por palavra não são WER padrão.
7. **Critério de aceite:** protocolo, data e solicitante passam pela confirmação humana antes da minuta, com o player do áudio ao lado na interface.

## RF07 — Voz da minuta aprovada

- **Só minuta aprovada e inalterada:** `python -m src.main audio-minuta <id>` ou o botão da interface. O fluxo confere status e hash da aprovação; áudio anterior nunca é sobrescrito.
- **Lacunas com aviso:** se a minuta tem "não localizado", ela traz, desde a geração, o aviso "Os campos identificados como não localizado representam informações ausentes no documento." Assim o aviso é revisado e aprovado junto com o texto. Sem ele, a síntese é bloqueada. A locução não acrescenta nada depois da aprovação.
- **Preparação da fala** (`markdown_conservador_v1`): tira marcas de título, lista, negrito, itálico e código; tira imagens, que são decorativas (o brasão não é lido); mantém links com o destino. Bloqueia HTML, tabelas e blocos de código, que precisam virar texto simples antes da aprovação. A locução aceita até 4096 caracteres, limite da Speech API.
- **Saída:** WAV PCM validado (cabeçalho, frames e comprimento) antes de gravar. A Speech API envia o WAV como em streaming, com os tamanhos do cabeçalho em `0xFFFFFFFF`; o `llm_client.py` preenche os tamanhos reais antes da validação. Voz, estilo, hashes da minuta, do texto falado e do áudio, e duração ficam nos metadados da minuta e no log.

## Resultados reais (31/10/2026)

| Etapa | Resultado |
|---|---|
| Inspeção do `entrada_audio.mp3` | MP3, 89,16 s |
| Transcrição (`638263b33c98`) | 4,1 s de chamada; US$ 0,0068 estimado (cobrança por minuto de áudio); idioma detectado `pt` |
| Texto transcrito | Nomes, datas, curso, e-mail e declaração corretos; protocolo, CPF e RG já agrupados |
| Mascaramento antes da extração | CPF, RG e e-mail mascarados |
| Campos extraídos | Protocolo 2026-000142, data "14 de outubro de 2026", solicitante Marcos Vinícius de Almeida Santos, categoria `matricula`; confirmados por pessoa sem correção |
| Comparação com o gabarito validado | 97,7% das palavras certas (127 de 130), no bruto e no revisado; 6 de 6 dados críticos; erros apontados: "1200" como "1.200", "10" como "dez", "informem" como "informe" |
| Voz da minuta aprovada do `audio-01` (`638263b33c98`) | WAV PCM de 80,6 s, 24 kHz, mono, 16 bits, voz `marin`; 13,9 s de chamada; hash do texto sintetizado igual ao registrado na aprovação. **Ouvida: o protocolo saiu como "2026, zero, zero, 142", com um zero a menos** |
| Voz da minuta aprovada do `texto-01` (`0b09035747ca`) | WAV PCM de 99,9 s, voz `marin`, com a instrução de ler o protocolo algarismo por algarismo; 14,6 s de chamada; hash igual ao da aprovação. Ouvida: protocolo com os três zeros. É o áudio de referência do RF07 |

**Áudio contra texto aprovado (critério de aceite do RF07):** cada WAV foi transcrito com `gpt-transcribe` e comparado com o texto falado esperado (`resultados/audios/<id>_verificacao.json`): 97,9% das palavras no `audio-01` e 97,8% no `texto-01`, sem acréscimos. Nos dois, a transcrição registrou o protocolo errado ("2026 00142" e "2026 00042"), e a escuta humana decidiu:

- No `audio-01`, a voz de fato omitiu um zero. É um erro crítico: o áudio não corresponde ao texto aprovado num dado crítico. O arquivo fica como evidência e não deve ser usado.
- No `texto-01`, a voz falou os três zeros; o erro foi da transcrição de verificação.

Em testes curtos com a mesma frase, a omissão do zero apareceu e desapareceu entre tentativas com a mesma instrução, e soletrar os dígitos com vírgulas piorou o resultado. A instrução de ler o protocolo algarismo por algarismo foi acrescentada ao estilo e acertou nas tentativas feitas, mas a síntese continua não determinística. A verificação automática serve para achar acréscimos e omissões de palavras; números só se confirmam ouvindo.

## Gabarito

`dados/gabaritos/audio-01.json` foi validado por Victor Griggi Moreira Regis da Silva ouvindo o original: a fala é "no turno noturno". O gabarito só vale com `validado_por_humano: true`, autoria, data e dados críticos como valores; a saída do modelo nunca deve ser usada como gabarito.

## Segurança e privacidade

- Use só dados fictícios. O áudio vai inteiro ao provedor: o mascaramento do texto vem depois e não anonimiza a gravação.
- Mensagens de erro locais não repassam a saída do `ffprobe`; o log não guarda áudio nem texto falado.
- O hash local protege a consistência entre aprovação e áudio, não impede adulteração conjunta de arquivo e metadados.

## Acessibilidade

O áudio amplia o acesso para pessoas com deficiência visual ou com dificuldade de leitura. O texto continua disponível, inclusive para pessoas surdas. Continuam como limites a linguagem burocrática, a pronúncia de siglas, nomes e caminhos de arquivo, o ritmo e o equipamento de quem ouve. A voz é sintética, e as políticas de uso da OpenAI exigem informar ao ouvinte que ela é gerada por IA; não há clonagem de voz. A validade técnica do WAV não comprova a fidelidade da fala: o áudio precisa ser ouvido antes do uso.

## Testes

`python -m pytest` roda a suíte inteira, incluindo `testes/test_audio.py`, com SDK e `ffprobe` simulados e sem chamar a API. Os testes cobrem validação do arquivo, transcrição, junção dos dígitos, bloqueio por lacuna sem aviso, limite da locução, preparação da fala, validação do WAV, correção do cabeçalho em streaming e integração com o fluxo.

## Limitações

- O `gpt-transcribe` não marca trechos incertos; a incerteza da transcrição só aparece na confirmação humana e na comparação com o gabarito.
- `gpt-4o-mini-tts` e os demais modelos da Speech API serão desligados em 06/01/2027; o substituto indicado, `gpt-realtime-2.1-mini`, só funciona pela Realtime API (fonte: docs oficiais OpenAI API, text-to-speech, out/2026).
- A voz pode errar números entre uma geração e outra; todo áudio precisa ser ouvido antes do uso, com atenção a protocolo e datas.
- A Speech API não informa tokens, então a voz fica sem estimativa de custo.
- O aviso de voz gerada por IA não faz parte da locução: acrescentá-lo exige que ele esteja no texto aprovado, porque a locução não acrescenta nada ao que foi aprovado.
- O ruído moderado do áudio real não foi avaliado à parte; o caso tem uma gravação só.
