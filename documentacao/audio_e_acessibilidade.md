# Áudio e acessibilidade — RF06/RF07

Implementação técnica integrada. Na validação para versionamento, a suíte completa
aprovou 110 testes e 26 subtestes, sem chamadas Gemini. O MP3 foi inspecionado
realmente com ffprobe (89,16 s). **Aceite acadêmico pendente**: inferência real,
confirmação final do gabarito e dos dados críticos, minuta aprovada e conferência
auditiva do WAV ainda não foram comprovadas. Os registros de bloqueios abaixo
pertencem às etapas anteriores; o estado vigente está no relatório de validação.

## Arquitetura e conteúdo das aulas

- Aula 05: STT/TTS, revisão humana, pronúncia, entonação, FFmpeg/ffprobe.
- Aulas 03/04: prompt seguro, configuração, timeout e cliente centralizado.
- Aula 06: Gemini/Interactions e mídia base64. A integração de áudio adapta
  esses conhecimentos; os exemplos práticos de voz da Aula 05 usam OpenAI.
- Sem biblioteca Python nova: biblioteca padrão (`subprocess`, `wave`, `base64`,
  `hashlib`, `unittest`) e infraestrutura existente. `ffprobe` é ferramenta de
  sistema ensinada na Aula 05. Nenhuma instalação privilegiada foi realizada.

Entrada: `ArquivoEntrada` → revalidação de extensão/tamanho/hash → ffprobe →
STT pelo `ClienteLLM` → `TextoExtraido` → comparação válida ou aviso de pendência
→ extração existente → confirmação dos críticos → minuta aguardando revisão.

Saída: revisão existente + hash → preparação determinística → TTS pelo mesmo
cliente → validação WAV → gravação exclusiva → metadados e auditoria.
As assinaturas públicas de `transcrever()` e `sintetizar()` não mudaram.
Tipos, categorias e módulos de texto/OCR/imagem não foram alterados.

## Instalação e configuração

Siga o ambiente virtual e `requirements.txt` do README. Verifique `ffprobe -version`.
FFmpeg deve ser instalado pelo operador conforme seu sistema, sem ação automática
da aplicação. No Windows, disponibilize o diretório dos executáveis no PATH.
Configuração não sensível:

- `modelos.transcricao`: `gemini-3.8-flash`;
- `modelos.tts`: `gemini-3.8-flash-tts`;
- `audio.voz`: `Kore`, voz predefinida;
- `audio.estilo`: pt-BR, institucional, claro e pausado; separado do conteúdo;
- `audio.timeout_inspecao_s`: 30; timeout API existente: 180 segundos.
- Segredo somente em `GEMINI_API_KEY`/`.env`, nunca nesta documentação.

MP3, WAV, M4A, OGG e FLAC seguem a configuração compartilhada, até 20 MiB.
Também se limita a requisição inline serializada, com reserva de 64 KiB para
envelope/parâmetros. Arquivo grande deve ser reduzido pelo operador sem alterar
o original; upload automático/Files API não foi implementado.

## RF06 e integridade

`ffprobe -count_frames` percorre frames e exige stream de áudio, contagem
positiva, duração finita positiva e contêiner compatível com a extensão. Falha,
JSON inválido, stderr de erro, falta da ferramenta ou timeout bloqueiam a API.
É inspeção estrutural, não garantia de qualidade acústica ou ausência de toda
possível degradação do sinal. O hash é verificado novamente após a inspeção.

`transcricao_v1.md` trata toda a parte de mídia como conteúdo externo não
confiável. Ordens pronunciadas são dados, não instruções. Inaudível não é
completado por contexto. A resposta estruturada contém bruto, idioma e incertezas;
o código valida tipos, conserva o bruto e produz o revisado só normalizando
espaços/quebras. Não corrige palavras ou números por palpite. O modelo não é
consultado para estimar duração. `duracao_audio_s` é local;
`duracao_requisicao_s` é a latência de `RespostaLLM`.

Os artefatos existentes em `dados/processados/<caso>/<id>/` preservam textos,
metadados, comparação e campos. A confirmação humana existente exige protocolo,
data e solicitante antes da minuta. Similaridade de `SequenceMatcher` e taxa de
acerto por palavras **não são WER padrão** nem substituem a conferência crítica.

## Gabarito humano

`dados/gabaritos/audio-01.json` é um modelo vazio, com
`validado_por_humano=false`. Ouça o original e registre texto literal, autoria,
data e `dados_criticos` como valores, por exemplo o protocolo efetivamente ouvido,
nunca os nomes das chaves do esquema. Não use a saída do modelo como referência
independente. A validação requer texto, autoria e data não vazios, sinalizador
booleano verdadeiro e lista de valores críticos textuais. É declaração humana,
não autenticação criptográfica de autoria.

Enquanto pendente, a etapa `comparacao_gabarito` registra aviso, sem gravar
métricas enganosas. Com gabarito válido, usa o comparador existente para bruto,
revisado e críticos ausentes. Os testes têm referência fictícia independente
explicitamente rotulada como simulada. Ruído moderado do caso real continua não
avaliado. Preserve sempre o arquivo original.

## RF07 e aprovação

Use exclusivamente `python -m src.main audio-minuta <id>` para produção oficial.
A primitiva `audio.sintetizar()` é interna e recebe só texto; a autorização está
em `fluxo.sintetizar_minuta()`. Não é mecanismo de autenticação de usuários.

A minuta precisa estar aprovada/aprovada com correção e ter o mesmo hash da
revisão. O áudio anterior não é sobrescrito. Para nova emissão, use outra
execução revisada e preserve o histórico. WAV inválido, truncado, sem frames ou
base64 inválido não é gravado como resultado válido. O fluxo confere novamente
a existência e estrutura do arquivo antes de registrar sucesso.

A locução não acrescenta avisos. Se existir “não localizado”, o texto aprovado
precisa incluir exatamente o aviso, ignorando caixa:

> Os campos identificados como não localizado representam informações ausentes no documento.

Inclua-o antes da revisão. Se a minuta já foi aprovada sem o aviso, produza outra
execução revisada; não edite metadados para contornar o hash. O aviso preserva a
lacuna, não a resolve. Nenhum prompt de minuta dos colegas foi modificado.

### Preparação `markdown_conservador_v1`

- Retira prefixo de título e marcador de lista não numerada.
- Retira linhas exclusivamente separadoras/assinatura horizontal.
- Retira delimitadores pareados de negrito/itálico/código inline simples.
- Converte links/imagens simples em rótulo seguido do destino entre parênteses;
  mantém fontes e destinos para não suprimir conteúdo aprovado.
- Normaliza espaços e quebras; não reescreve números, nomes, datas ou fatos.
- Bloqueia HTML/comandos vocais em `<...>`, tabelas, cercas de código e escapes.
  Prepare uma versão simples e aprove-a antes da síntese nesses casos.

Não é parser geral de Markdown. Caminhos preservados podem soar pouco naturais;
audição humana é necessária. Texto efetivamente enviado pode ser reconstruído
com a regra versionada e o Markdown preservado; seu SHA-256 fica nos metadados.
Não use LLM para simplificar depois da aprovação.

A requisição TTS usa conteúdo `user_input` com texto literal e anotação
`speech_metadata.style`; voz em `generation_config.speech_config`, saída audio.
O WAV PCM é validado com `wave`, incluindo frames, contêiner e comprimento.
Configurações, hashes, duração, tokens/custo disponíveis ficam em `sintese` nos
metadados da minuta e no evento. O áudio exige revisão auditiva posterior para
conferir correspondência; validade do WAV não comprova fidelidade da fala.

## Execução e testes

```bash
source .venv/bin/activate
python -m unittest testes.test_audio -v
python -m pytest
# Somente com custos/cota autorizados e ambiente preparado:
python -m src.main processar audio-01
python -m src.main revisar <id_execucao>
python -m src.main audio-minuta <id_execucao>
```

Resultados desta etapa: 30 testes unittest aprovados, com ffprobe e SDK falsos,
incluindo integração pelos módulos reais de campos/minuta. Suíte pytest bloqueada
por dependência ausente; instalação fixada bloqueada por DNS. Nenhuma inferência
real. Consulte `RELATORIO_IMPLEMENTACAO_AUDIO.md` para ambiente exato e evidência.

## Erros e segurança

`ArquivoInvalido` descreve falhas locais; `RevisaoInvalida`, bloqueios de revisão/
conteúdo; `RespostaVazia` e `RespostaMalformada`, saídas inválidas do provedor.
Falhas de rede/cota/autenticação usam `ErroLLM` existente. Mensagens locais não
repassam stderr da ferramenta. Logs não incluem áudio ou texto da locução.

Use apenas dados fictícios. Áudio original sai integralmente ao provedor; o
mascaramento textual posterior não anonimiza a gravação já enviada. `store=False`
não substitui análise da política de dados do plano. O hash local protege
consistência, não impede adulteração conjunta de arquivo e metadados.

## Custos e acessibilidade

Não houve cobrança de inferência nesta implementação. O custo estimado usa os
preços configurados e tokens devolvidos pelo cliente. Tarifa não é fatura;
`llm_client._tokens()` tem uma questão preexistente sobre possível dupla contagem
de pensamento, preservada fora do escopo. Confirme tarifas/cotas antes de rodar.
Falta de cota não autoriza trocar automaticamente de provedor.

Áudio amplia acesso a pessoas com deficiência visual ou dificuldade de leitura;
o texto deve continuar disponível, inclusive para pessoas surdas. Linguagem
burocrática, pronúncia de siglas/nomes, ritmo, equipamento e compreensão continuam
limitantes. Identifique a voz sintética ao apresentar o arquivo e confira
qualquer aviso falado antes da aprovação. Não há clonagem de voz.

## Compatibilidade: evidência e limite

Consultados em 18/10/2026: [áudio Gemini](https://ai.google.dev/gemini-api/docs/audio)
e [TTS Gemini](https://ai.google.dev/gemini-api/docs/speech-generation). A página de
TTS exige SDK Python >=2.25.0 e documenta o formato de voz/estilo/WAV utilizado;
o requisito do projeto é 2.31.0. Isso é compatibilidade documental, não validação
executável dessa versão nesta máquina. A instalação falhou antes de disponibilizar
o SDK. Ainda é necessário instalar as versões fixadas, executar a suíte original
e validar a serialização/serviço com chamada real autorizada. Os falsos não
comprovam que o endpoint ou a conta aceitam a requisição.
