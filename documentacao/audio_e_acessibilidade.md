# Áudio e acessibilidade (RF06 e RF07)

Transcrição da mensagem de voz (RF06) e versão falada da minuta aprovada (RF07), em `src/audio.py`. As duas chamadas passam pelo `ClienteLLM` (timeout, `store=False`, erros traduzidos, custo), como todo o projeto.

## Base nas aulas

- Aula 05: STT e TTS, revisão humana, pronúncia, entonação, FFmpeg e `ffprobe`.
- Aulas 03 e 04: prompt seguro, configuração, timeout e cliente centralizado.
- Aula 06: Gemini, Interactions API e mídia em base64. Os exemplos práticos de voz da Aula 05 usam OpenAI; aqui o mesmo conceito é aplicado ao Gemini.
- Sem biblioteca Python nova: `subprocess`, `wave`, `base64` e `hashlib` da biblioteca padrão, mais o `ffprobe` como ferramenta de sistema.

## Configuração

Requer FFmpeg com `ffprobe` no PATH (ver Instalação no README). Em `config.json`:

- `modelos.transcricao`: `gemini-3.8-flash`; `modelos.tts`: `gemini-3.8-flash-tts`;
- `audio.voz`: `Kore` (voz predefinida); `audio.estilo`: português do Brasil, tom institucional, claro e pausado, sem acréscimos;
- `audio.timeout_inspecao_s`: 30 s para o `ffprobe`; o timeout da API é o `timeout_segundos` geral.

Formatos aceitos: MP3, WAV, M4A, OGG e FLAC, até 20 MiB e dentro do limite de 20 MB da requisição inline. Não há upload pela Files API.

## RF06 — Transcrição

1. **Validação:** extensão, tamanho e hash (`entradas.py`); depois o `ffprobe -count_frames` percorre o arquivo inteiro e exige stream de áudio, frames, duração positiva e contêiner compatível com a extensão. Qualquer falha bloqueia o envio. O hash é conferido de novo depois da inspeção.
2. **Transcrição:** `prompts/transcricao_v1.md` trata o áudio como conteúdo externo; ordens faladas são dados, e trecho inaudível não é completado por contexto. A resposta traz texto bruto, idioma e trechos incertos, em JSON validado.
3. **Versão revisada:** só ajusta espaços e quebras de linha, sem trocar nenhum caractere. Isso inclui juntar dígitos ditados um a um ("1 2 3 4 5 6 7 8 9 - 0 0" vira "123456789-00"): separados, CPF, RG e protocolo escapavam do mascaramento e da comparação com o gabarito.
4. **Registro:** idioma, modelo, duração do áudio (medida localmente pelo `ffprobe`) e latência da chamada ficam em `dados/processados/audio-01/<id>/extracao_texto.json` e no log.
5. **Comparação:** só com gabarito marcado `validado_por_humano: true`, com texto de referência, autoria, data e dados críticos preenchidos. Sem isso, a etapa registra "comparação pendente" e não grava métricas. A similaridade e a taxa de acerto por palavra não são WER padrão.
6. **Critério de aceite:** protocolo, data e solicitante passam pela confirmação humana antes da minuta, com o player do áudio ao lado na interface.

## RF07 — Voz da minuta aprovada

- **Só minuta aprovada e inalterada:** `python -m src.main audio-minuta <id>` ou o botão da interface. O fluxo confere status e hash da aprovação; áudio anterior nunca é sobrescrito.
- **Lacunas com aviso:** se a minuta tem "não localizado", ela traz, desde a geração, o aviso "Os campos identificados como não localizado representam informações ausentes no documento." Assim o aviso é revisado e aprovado junto com o texto. Sem ele, a síntese é bloqueada. A locução não acrescenta nada depois da aprovação.
- **Preparação da fala** (`markdown_conservador_v1`): tira marcas de título, lista, negrito, itálico e código; tira imagens, que são decorativas (o brasão não é lido); mantém links com o destino. Bloqueia HTML, tabelas e blocos de código, que precisam virar texto simples antes da aprovação.
- **Saída:** WAV PCM validado (cabeçalho, frames e comprimento) antes de gravar. Voz, estilo, hashes da minuta, do texto falado e do áudio, duração, tokens e custo ficam nos metadados da minuta e no log.

## Resultados reais (18/10/2026)

| Etapa | Resultado |
|---|---|
| Inspeção do `entrada_audio.mp3` | MP3 mono, 48 kHz, 89,16 s |
| Transcrição (`838ebbb718e7`) | 11,0 s; 2.685 tokens de entrada e 717 de saída; US$ 0,0047 estimado; idioma `pt`; nenhum trecho incerto apontado |
| Texto transcrito | Nomes, datas, curso, e-mail e declaração corretos. Protocolo, CPF e RG vieram dígito a dígito, o que motivou a junção na versão revisada |
| Mascaramento antes da extração | Na primeira rodada, só o e-mail foi mascarado; com a junção dos dígitos, CPF, RG e e-mail passam a ser mascarados |
| Campos extraídos | Protocolo 2026-000142, data 14 de outubro de 2026, solicitante Marcos Vinícius de Almeida Santos, categoria `matricula` |
| Comparação com o gabarito | Pendente: o `audio-01.json` ainda não foi validado por quem ouviu o áudio |
| Síntese de voz (teste técnico) | WAV PCM de 12,4 s, 24 kHz, mono, 16 bits; 6,1 s de chamada; US$ 0,0028 estimado |

## Gabarito

`dados/gabaritos/audio-01.json` só vale depois que alguém **ouvir o original** e registrar o texto literal, a autoria, a data e os dados críticos como valores. O texto de referência atual coincide palavra por palavra com a transcrição do modelo, inclusive em "no turno no turno", e por isso não serve como referência independente até ser conferido. A saída do modelo nunca deve ser usada como gabarito.

## Segurança e privacidade

- Use só dados fictícios. O áudio vai inteiro ao provedor: o mascaramento do texto vem depois e não anonimiza a gravação.
- Mensagens de erro locais não repassam a saída do `ffprobe`; o log não guarda áudio nem texto falado.
- O hash local protege a consistência entre aprovação e áudio, não impede adulteração conjunta de arquivo e metadados.

## Acessibilidade

O áudio amplia o acesso para pessoas com deficiência visual ou com dificuldade de leitura. O texto continua disponível, inclusive para pessoas surdas. Continuam como limites a linguagem burocrática, a pronúncia de siglas, nomes e caminhos de arquivo, o ritmo e o equipamento de quem ouve. A voz é sintética e deve ser apresentada como tal; não há clonagem de voz. A validade técnica do WAV não comprova a fidelidade da fala: o áudio precisa ser ouvido antes do uso.

## Testes

`python -m pytest` roda a suíte inteira, incluindo `testes/test_audio.py`, com SDK e `ffprobe` simulados e sem chamar a API. Os testes cobrem validação do arquivo, esquema da transcrição, junção dos dígitos, bloqueio por lacuna sem aviso, preparação da fala, validação do WAV e integração com o fluxo.

## Limitações

- O ruído moderado do áudio real não foi avaliado à parte; o caso tem uma gravação só.
- A estimativa de custo soma os tokens de raciocínio à saída, sem confirmação de que o SDK já os inclui (ver `llm_client.py`); o valor pode estar superestimado.
- Sem Files API: áudios acima do limite inline precisam ser reduzidos pelo operador, sem alterar o original.
