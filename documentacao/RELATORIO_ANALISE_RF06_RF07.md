# Relatório técnico — análise de RF06 e RF07

**Projeto:** Central Inteligente de Atendimento e Comunicação Institucional — Desafio Prático 1, Módulo 3, FIC_DEV.
**Data:** 18/10/2026.
**Responsabilidade analisada:** processamento de áudio e acessibilidade.
**Diretório de trabalho:** `/home/andre/estudos/ficdev2026/Desafio modulo 3/`.
**Repositório:** `FIC_DEV-IA-Desafio1/`.
**Referência Git inspecionada:** branch `main`, commit `bf91e841c982a95cafd14afd398e2d58a2ac8731`.

## 1. Escopo, método e limites da análise

Este documento consolida a análise anterior dos materiais das Aulas 01 a 07, do enunciado e do código existente. Sua finalidade é orientar uma implementação posterior de RF06 e RF07, preservando os módulos e contratos dos colegas.

A análise precedente utilizou inspeção de arquivos, extração textual de PDF/DOCX/PPTX, leitura de código e documentação, consultas locais ao Git e análise sintática com `ast.parse`. Também consultou páginas públicas oficiais do Google para verificar formatos e disponibilidade documentada de áudio. Não houve envio de arquivos para inferência, consumo de API de modelos, instalação de dependências ou execução da aplicação.

Nenhuma funcionalidade foi implementada. A geração deste relatório autoriza somente este arquivo, fora do repositório da equipe.

### 1.1 Classificação das evidências

| Classificação | Significado neste relatório |
|---|---|
| Verificado por inspeção | O arquivo foi examinado e contém a estrutura ou o comportamento descrito. Não comprova execução bem-sucedida. |
| Verificado estaticamente | Uma inspeção automatizada sem executar os módulos confirmou uma propriedade, como sintaxe ou igualdade de hashes. |
| Relatado em documentação | Há uma declaração no projeto, mas os artefatos ou a execução não foram verificados nesta auditoria. |
| Não verificado | Depende de execução, audição, revisão visual ou inspeção adicional não realizada. |
| Ausente | Não foi encontrada a implementação ou evidência correspondente nos arquivos examinados. |

Existência de testes não equivale a testes aprovados. Existência de código não equivale a aceite acadêmico demonstrado.

### 1.2 Limitações expressas

- O enunciado em PDF foi lido integralmente por extração textual; suas duas cópias são idênticas por SHA-256.
- Foram examinados conteúdos textuais extraíveis dos materiais e exemplos relevantes. Não houve avaliação visual integral das ilustrações incorporadas.
- Não houve audição dos áudios. Não se afirma qual é o conteúdo exato da mensagem fornecida, sua qualidade acústica ou a presença de ruído moderado.
- Não foram executados testes, comandos da aplicação ou chamadas de inferência.
- Não foi feito `git fetch`; a relação com `origin/main` corresponde à referência local.
- Preços acadêmicos são referências datadas. Consulta pública de documentação não comprova disponibilidade ou cota na conta da equipe.
- Valores de `.env`, tokens e credenciais não foram expostos.

## 2. Conclusões executivas

1. **RF06 e RF07 têm infraestrutura de integração, mas não possuem seus núcleos implementados.** `src/audio.py` contém `transcrever()` e `sintetizar()`, ambas levantando `PendenteDeImplementacao`.
2. A base compartilhada já valida entradas, grava artefatos, compara textos com gabaritos, exige confirmação humana dos dados críticos e registra eventos.
3. O fluxo de síntese já bloqueia minutas sem aprovação e alterações posteriores à aprovação por comparação de SHA-256.
4. A implementação deve preservar `ArquivoEntrada`, `TextoExtraido`, o esquema de extração e o cliente centralizado `ClienteLLM`.
5. A Aula 05 é a principal base pedagógica de áudio; sua prática usa majoritariamente OpenAI. Gemini e Interactions aparecem no curso, especialmente na Aula 06. Áudio com Gemini é uma adaptação desse conteúdo à arquitetura existente.
6. As pastas de resultados e processados contêm somente `.gitkeep`. Execuções relatadas na documentação não possuem artefatos locais disponíveis neste clone.
7. Falta `dados/gabaritos/audio-01.json`. A referência deve ser elaborada por audição humana antes da primeira inferência; não pode ser copiada da solicitação textual sem conferência.
8. A próxima implementação recomendada é validar tecnicamente o áudio e medir sua duração localmente com `ffprobe`, antes de consumir API.

## 3. Resumo detalhado das Aulas 01 a 07

### 3.1 Aula 01 — Conceitos Fundamentais

**Fonte principal:** `Aula1/Aula-01-Conceitos-Fundamentais.pdf`.

O material diferencia Inteligência Artificial, aprendizado de máquina, aprendizado profundo e IA generativa. Apresenta aprendizado supervisionado, não supervisionado e por reforço; pesos de modelos; treinamento e validação; Transformers, modelos de difusão e outras arquiteturas generativas. Discute modelos de raciocínio, computação no momento da resposta, agentes e limites de confiabilidade.

São abordados modelos proprietários e de pesos abertos, com exemplos das famílias GPT, Gemini, Claude, Llama, Qwen, DeepSeek, Gemma e GPT-OSS. A discussão distingue acesso por API, publicação de pesos e condições de licença. Trata de autonomia, custos, alucinação e responsabilidade no uso institucional.

**Aplicação no desafio:** justificar a seleção de modelos e manter revisão humana de fatos. Uma saída fluente não comprova fidelidade, e um modelo multimodal não dispensa validação de nomes, datas ou protocolos. A aula é conceitual e não exige adicionar biblioteca ao projeto.

### 3.2 Aula 02 — Ferramentas de IA Generativa

**Fontes:** `Aula2/Aula-02-Ferramentas-IA-Generativa.docx.pdf`, `Aula2/exemplos/` e materiais de `Aula2/minilab/`.

Apresenta assistentes conversacionais, ferramentas especializadas, agentes de codificação e o ecossistema Hugging Face. Discute ChatGPT, Gemini, Claude, Perplexity, NotebookLM e ferramentas de programação. Diferencia interface de assistente, execução por agente e chamada programática a modelo.

Os exemplos usam Python, SDK `openai`, `requests` e `python-dotenv`, incluindo o roteador Hugging Face Inference Providers. Abordam catálogo de modelos, token com permissão adequada, políticas de roteamento, conteúdo vazio e consumo de tokens. Exemplos e exercícios incluem GPT-OSS, Qwen e Llama.

**Aplicação:** configuração segura, comparação entre alternativas e entendimento de que uma assinatura de assistente não equivale automaticamente a créditos de API.

**Evidência acadêmica complementar:** `Aula2/minilab/analise_minilab_aula02.md` compara resultados e distingue consumo de tokens de custo efetivo. Esses resultados pertencem ao exercício, não à execução do desafio.

### 3.3 Aula 03 — Engenharia de Prompts

**Fontes:** `Aula3/Aula-03-Engenharia-de-Prompts.docx`, exemplos e mini-lab.

Ensina persona, contexto, tarefa, formato, exemplos e critérios de sucesso. Trabalha zero-shot, few-shot, metaprompting, decomposição e verificação. Diferencia raciocínio solicitado explicitamente de raciocínio interno controlado por parâmetros. Usa Markdown para organização, XML como delimitador e JSON para consumo por software.

Os exemplos utilizam `openai`, `python-dotenv` e `gpt-5.6-luna`. A aula também trata de temperatura, top-p, limite de tokens, esforço de raciocínio, conteúdo não confiável, prompt injection e arquivos de instrução persistente como `AGENTS.md` e `CLAUDE.md`.

**Aplicação:** elaborar prompts de transcrição literal e revisão conservadora; separar locução de instruções de estilo; impedir que conteúdo falado seja interpretado como ordem do sistema.

**Limitação dos exercícios:** `Aula3/mini-lab/relatorio-prompts.md` registra experimento não concluído por falta de créditos. Não deve ser usado como comprovação de execução de RF02.

### 3.4 Aula 04 — Provedores de Modelos e APIs

**Fontes:** `Aula4/Aula-04-Provedores-LLMs-APIs.docx`, `Aula4/Aula 04 — Provedores de LLMs e APIs.pptx`, `Aula4/Exemplos/`, análise e mini-lab locais.

Diferencia provedor, roteador e agregador de interface. Apresenta OpenAI, Google, Anthropic, Groq, OpenRouter e Hugging Face, além de outros provedores de infraestrutura. Explica autenticação, estrutura de requisição/resposta, SDKs e HTTP com `requests`.

Bibliotecas demonstradas incluem `openai`, `requests`, `python-dotenv`, `anthropic` e `google-genai`. Há exemplos de modelos GPT, Gemini, Claude e GPT-OSS. O material ensina timeout, verificação de chave, tratamento de falhas HTTP, leitura de uso de tokens e medição de tempo/custo.

**Aplicação:** manter as chamadas no cliente compartilhado, não duplicar acesso ao SDK em `audio.py`, tratar credenciais e registrar métricas de forma consistente.

**Cuidado metodológico:** a análise local `Aula4/analise_aula04.md` já registra limites de comparações de latência com modelos diferentes e problemas de tarifas presumidas. Este relatório não revalida afirmações jurídicas ou todos os preços dos materiais.

### 3.5 Aula 05 — Modelos de Áudio e Voz Sintética

**Fontes:** `Aula5/Aula-05-Modelos-Audio-Voz.docx`, `Aula5/exemplos/exemplo01.py` a `exemplo07.py`, `preparar_audio_reuniao.py` e saídas de exemplo.

É a base direta de RF06/RF07. Apresenta STT/ASR, TTS, normalização da fala, qualidade de transcrição, Word Error Rate (WER), formatos de entrada/saída, seleção de idioma, modelos com diferentes capacidades, controle de entonação, acessibilidade, legendas e diarização.

**Modelos de API apresentados:** `gpt-transcribe`, `gpt-4o-mini-transcribe`, `gpt-4o-transcribe`, `gpt-4o-transcribe-diarize`, `whisper-1`, `gpt-live-transcribe`, `gpt-4o-mini-tts` e modelos antigos de TTS citados para comparação. A prática principal utiliza `openai` e `python-dotenv`.

**Outros ecossistemas discutidos:** Google Cloud Speech-to-Text/Chirp, vozes Google Cloud, Gemini-TTS, Azure e ElevenLabs. Alternativas de pesos abertos incluem Whisper, Voxtral, Parakeet, Granite Speech, Chatterbox e Kokoro. A menção a um modelo não significa que exista implementação dele nos exemplos ou no projeto.

**Ferramentas locais:** FFmpeg para manipular áudio e `ffprobe` para medir duração. O exemplo 04 usa `subprocess` e `shutil.which()` para essa inspeção.

**Lições técnicas relevantes:**

- Formatos de resposta variam entre modelos; trocar apenas o identificador pode quebrar a requisição.
- Os exemplos reservam `verbose_json`, SRT e VTT ao modelo compatível, em vez de presumir suporte universal.
- SSML e instruções naturais não são intercambiáveis. O experimento da aula mostra SSML ignorado na API demonstrada da OpenAI.
- Controle de estilo deve ser separado do conteúdo que será falado.
- Nomes próprios, siglas, datas e números exigem audição humana.
- Simplificação textual pode melhorar acesso, mas não pode modificar uma minuta depois de aprovada sem nova conferência.
- Voz sintética deve ser identificada; não é necessário clonar voz de pessoa real.

### 3.6 Aula 06 — Multimodalidade, Visão e OCR

**Fontes:** `Aula6/Aula-06-Modelos-Multimodais-Visao-OCR.docx` e `Aula6/exemplos/`.

Apresenta imagens por URL e base64, upload de arquivos, PDF, resolução, custo de leitura e três rotas de OCR: clássico, especializado em documentos e multimodal de propósito geral. Trata de alucinação numérica, normalização silenciosa, omissão, incerteza e comparação com referência.

Ferramentas e bibliotecas incluem OpenAI, `google-genai`, Interactions API, Groq/Hugging Face, Mistral OCR/`mistralai`, Tesseract/`pytesseract` e Pillow. Discute PaddleOCR, modelos abertos e pré-processamento local.

**Aplicação:** fundamenta o padrão de mídia do projeto e a separação entre texto bruto, revisado e trechos incertos. `Aula6/exemplos/exemplo06.py` demonstra Interactions e Files API do Gemini, reutilizáveis conceitualmente na integração de áudio.

### 3.7 Aula 07 — Geração e Edição de Imagens

**Fontes:** `Aula7/Aula-07-Geracao-Imagens.docx` e `Aula7/exemplos/`.

Aborda difusão, espaço latente, condicionamento por prompt, passos, orientação, semente e limitações de reprodutibilidade. Ensina sujeito, composição, estilo, iluminação, proporção e restrições; geração, edição com máscara, fundo transparente e medição de custos.

Modelos/ecossistemas discutidos incluem GPT Image, Gemini/Nano Banana, FLUX, Stable Diffusion e Midjourney. Exemplos usam `openai`, `python-dotenv`, Pillow e utilitários da biblioteca padrão, incluindo leitura de blocos PNG para examinar proveniência.

**Aplicação:** explica a solução existente de gerar ilustração sem texto e aplicar tipografia/selo por código, além de manter prompt, modelo, data e revisão. Não exige alteração da parte de imagem para concluir RF06/RF07.

## 4. Diagnóstico da arquitetura atual

### 4.1 Estrutura

O projeto é um protótipo local em Python, com CLI, arquivos JSON/Markdown e eventos JSONL. Não foi identificada necessidade de banco de dados, servidor web ou framework de agentes.

```text
src/main.py
  └─ src/fluxo.py
      ├─ entradas.validar_arquivo()
      ├─ texto direto / audio.transcrever() / vision.extrair_texto()
      ├─ comparação com gabarito para áudio e imagem
      ├─ privacidade.mascarar() → extracao.extrair_campos()
      ├─ confirmação humana dos críticos para áudio e imagem
      ├─ minuta.gerar_minuta() → aguardando_revisao
      └─ revisão humana → status + hash

audio-minuta <id>
  └─ aprovação + integridade → audio.sintetizar() → WAV
```

Geração/edição de imagem e revisão da peça têm comandos próprios.

### 4.2 Componentes examinados

| Arquivo | Responsabilidade |
|---|---|
| `src/main.py` | Comandos, mensagens e códigos de saída. |
| `src/config.py`, `config.json` | Configuração, caminhos, modelos, casos, limites e tarifas. |
| `src/llm_client.py` | Cliente único Gemini; timeout, falhas, saída vazia, tokens e custo estimado. |
| `src/entradas.py` | Validação compartilhada e SHA-256. |
| `src/tipos.py` | Contrato `TextoExtraido` e exceção de funcionalidade pendente. |
| `src/extracao.py` | Esquema e extração dos campos da solicitação. |
| `src/minuta.py` | Minuta com dados estruturados e referências. |
| `src/prompts.py` | Carregamento, versão/hash e delimitação. |
| `src/privacidade.py` | Mascaramento de padrões e ocultação de segredos. |
| `src/vision.py` | OCR multimodal, bruto/revisado/incertos. |
| `src/image_generation.py` | Ilustração, composição Pillow e proveniência. |
| `src/revisao.py` | Confirmação crítica, decisão, hash, checklist e taxas. |
| `src/comparacao.py` | Similaridade, erros e presença de valores críticos. |
| `src/audit.py` | Eventos JSONL associados à execução. |
| `src/audio.py` | Assinaturas e documentação; STT/TTS pendentes. |

### 4.3 Instruções do repositório

`AGENTS.md` determina que nenhuma resposta seja enviada automaticamente e que o áudio derive de minuta aprovada e inalterada. Todas as chamadas Gemini devem passar por `llm_client.py`. Os contratos entre modalidades são `TextoExtraido` e o esquema de extração. Prompts alterados recebem nova versão; originais devem permanecer inalterados. `CLAUDE.md` importa `AGENTS.md`.

Essas instruções reforçam a preservação dos módulos dos colegas e não autorizam implementações nesta etapa documental.

### 4.4 Modelos e dependências configurados

| Tarefa | Modelo em `config.json` |
|---|---|
| Texto, transcrição e visão | `gemini-3.8-flash` |
| TTS | `gemini-3.8-flash-tts` |
| Imagem | `gemini-3.1-flash-lite-image` |

Dependências declaradas: `google-genai==2.31.0`, `python-dotenv==1.2.4`, `pytest==9.1.1`, `pillow==13.0.0`. Timeout configurado: 180 segundos. Segredo esperado: variável `GEMINI_API_KEY`. `.env.example` existe e está versionado.

No interpretador `python3` ativo na análise: Python 3.12.3, Pillow 10.2.0; `google-genai`, `python-dotenv` e `pytest` não encontrados nesse interpretador. `ffprobe` não foi encontrado no PATH. Isso não comprova ausência em outros ambientes virtuais.

### 4.5 Estado e evidências locais

- Git sem alterações reportadas, branch `main`, referência local `origin/main`.
- Commit atual: `bf91e84`, texto, experimento e mitigação de injeção.
- Histórico relevante: `cc643aa`, confirmação de incertezas; `b462230`, imagem/OCR; `aff83bf`, base compartilhada.
- Quatro originais fornecidos são idênticos por SHA-256 às cópias no repositório.
- Áudio: 2.853.120 bytes; `file` reconheceu MP3, 48 kHz, mono, 256 kbps. Duração e conteúdo não confirmados.
- `dados/processados/` e `resultados/{audios,minutas,imagens,logs}/` contêm apenas `.gitkeep`.
- 25 arquivos de `src/` e `testes/` passaram na análise sintática AST, sem importação/execução dos módulos.
- Foram contadas 61 funções de teste declaradas; parametrização pode mudar a quantidade de casos. Nenhum teste foi executado.

## 5. Matriz RF01 a RF13

O status considera implementação e evidências separadamente. As obrigações abaixo sintetizam o enunciado original, páginas 3 a 6; não substituem sua leitura.

| RF | Objetivo e obrigações | Diagnóstico | Aceite, evidências e validação pendentes |
|---|---|---|---|
| RF01 | Entrada reproduzível, configuração, segredos externos, `.env.example` e versões. | Implementado no código; instalação não validada. | Executar seguindo apenas README; preservar registro de ambiente. `verificar` escreve arquivo, por isso não foi executado. |
| RF02 | Três prompts: zero-shot, estruturado e por metaprompt; mesmo modelo/parâmetros; avaliar fidelidade, invenção, formato, tom, lacunas e tempo utilizável. | Parcialmente demonstrado por documentação. A/B/C, saídas e matriz presentes; B incorporado em produção. | Rastrear metaprompt, parâmetros e medições; tempos não estão em segundos e há tokens aproximados. Rever avaliação de alucinação. |
| RF03 | Sistema separado dos dados, conteúdo delimitado, proteção contra instruções externas, proibição de invenção, ausências e saída verificável; caso de injection. | Proteções e caso adversarial presentes; eficácia semântica não demonstrada nesta auditoria. | Comprovar resultado real do caso adversarial e falhas residuais. Delimitação não garante comportamento do modelo. |
| RF04 | Chamada configurável, timeout, chave ausente/inválida, limite, indisponibilidade e vazio; duração/tokens/custo sem segredos. | Implementado no cliente; chamada real não reproduzida. | Demonstrar chamada e falhas; conferir tokens de pensamento e telemetria de TTS. |
| RF05 | Campos obrigatórios, categoria documentada, ausências/confiança, original e JSON válido. | Implementado; artefatos de execução ausentes. | Validar JSON e esperado/obtido; robustez contra tipos anômalos precisa de atenção. |
| RF06 | Validar áudio, STT, bruto/revisado, idioma/modelo/duração e comparação. | Parcial: infraestrutura presente; STT ausente. | Implementar núcleo, gabarito e resultados. Conferir nomes, datas e protocolos antes da minuta. |
| RF07 | Fala da minuta aprovada, voz/tom, aviso de ausências, formato comum e acessibilidade. | Parcial: aprovação/hash presentes; TTS ausente. | Implementar síntese e tratamento aprovado das lacunas; ouvir e conferir correspondência sem acréscimos. |
| RF08 | OCR/visão, original/bruto/corrigido, incertezas, gabarito/acertos/erros e justificativa local. | Implementado no código; demonstração pendente. | Gabarito de imagem é rascunho com autoria/data vazias e categoria indefinida; faltam resultados e confirmação demonstrada. |
| RF09 | Minuta institucional baseada em dados disponíveis, lacunas, fontes e nenhum envio automático. | Implementado; qualidade real não verificada. | Conferir conteúdo e apresentação do brasão. Não há implementação de renderização HTML/PDF em `gerar_minuta()`. |
| RF10 | Prompt visual completo, gerar/editar, revisão, modelo/data/prompt, identificação sintética e proveniência; sem pessoa real não autorizada. | Implementado no código; resultados ausentes. | Produzir peça, nota e decisão humana. Serviço depende de cobrança. |
| RF11 | ID/data/modalidade/origem, provedor/modelo/parâmetros/prompt, saída/tempo/erro/decisão, sem chave. | Parcial; estrutura implementada sem logs locais reais. | TTS não transporta resposta completa ao evento; hash próprio do prompt de sistema não é registrado nas chamadas. |
| RF12 | Dados fictícios; campos pessoais/finalidade/necessidade/risco; minimização. | Parcial: mascaramento e política presentes. | Falta matriz de dados; mídia bruta sai integralmente; revisão pode reintroduzir dados. Nenhuma evidência pode conter segredo ou dado real. |
| RF13 | Fidelidade/completude/formato/linguagem/segurança; esperado/obtido, gravidade, correção/regeneração, taxa e riscos. | Parcial: revisão e taxas implementadas. | Falta protocolo completo e resultados por caso. Demonstrar caso aprovado e rejeitado ou corrigido. |

### 5.1 Dependências funcionais

```text
RF01 / RF04 / RF11 / RF12 → infraestrutura das modalidades
RF06 ou RF08 → RF05 → confirmação crítica → RF09 → RF13 → RF07
RF02 → escolha do prompt de RF09
RF03 → proteção das etapas com conteúdo externo
RF10 → fluxo de geração e revisão visual próprio
```

## 6. RF06 — diagnóstico detalhado de Speech-to-Text

### 6.1 Implementação encontrada

`src/audio.py:13` define:

```python
transcrever(arquivo: ArquivoEntrada, *, cliente: ClienteLLM, config: Config) -> TextoExtraido
```

O corpo levanta `PendenteDeImplementacao("RF06", "áudio")`. A docstring descreve o resultado esperado, mas não constitui implementação nem teste de API.

### 6.2 O que pode ser reutilizado

| Necessidade | Código disponível | Limite atual |
|---|---|---|
| Seleção da entrada | Caso `audio-01` em `config.json` | Não é upload interativo; recebe arquivo do caso configurado. |
| Extensão/tamanho/existência | `entradas.validar_arquivo()` | Não valida decodificação/conteúdo real do áudio. |
| Original e integridade | `ArquivoEntrada.sha256` e evento de entrada | Não substitui audição ou referência humana. |
| Persistência | `fluxo.processar_caso()` | Depende de `transcrever()` retornar resultado válido. |
| Bruto/revisado/incertos | `TextoExtraido` | Produção desses textos ainda ausente. |
| Comparação | `comparar_com_gabarito()` | Sem gabarito, a etapa é pulada. |
| Conferência humana | `confirmar_campos_criticos()` | Exige protocolo/data/solicitante; não equivale à conferência automática de todos os números. |
| Auditoria | `_etapa()` e `_anotar()` | O módulo deve devolver resposta e prompt para aproveitar a telemetria. |

### 6.3 Pendências obrigatórias

1. Medir duração real e validar áudio decodificável antes da chamada.
2. Executar STT via cliente centralizado.
3. Preservar texto bruto e produzir versão revisada conservadora.
4. Identificar trechos incertos sem inventar leitura.
5. Registrar idioma, modelo, duração e método de medição.
6. Criar `dados/gabaritos/audio-01.json` antes da inferência.
7. Comparar bruto e revisado com a referência e apontar erros relevantes.
8. Demonstrar conferência crítica anterior à minuta.
9. Registrar resultados e evidências de teste, inclusive limites de ruído.

### 6.4 Gabarito

O arquivo de áudio está presente, mas o gabarito correspondente não existe. A equipe deve ouvir o arquivo original e registrar referência textual, autoria, data, campos esperados e valores críticos literais. Trechos inaudíveis devem ser identificados como tais.

Não usar a solicitação textual ou a saída do modelo como verdade de referência sem conferência. Não fornecer o gabarito à transcrição: isso contaminaria a avaliação e poderia induzir preenchimento por expectativa.

### 6.5 Duração e validação

Recomenda-se `ffprobe`, explicitamente utilizado na Aula 05, exemplo 04. A latência de `RespostaLLM.duracao_s` é tempo da requisição, não duração do áudio. O metadado deve distingui-los.

No exemplo didático, ausência de `ffprobe` retorna `0.0`; para o desafio, zero não deve ser apresentado como duração medida. Recomenda-se erro compreensível antes da API, ou estado explícito de duração indisponível sem declarar RF06 concluído.

O limite local de 20 MiB é aplicado ao arquivo. A documentação Gemini consultada limita a requisição inline completa a 20 MB, incluindo prompts e arquivos. É necessário considerar serialização e base64. Para o arquivo atual, de aproximadamente 2,72 MiB, não se identifica proximidade desse limite; os casos de fronteira continuam necessários.

### 6.6 Revisão e comparação

A revisão pode corrigir apresentação, espaçamento e pontuação sem alterar fatos. Não deve trocar protocolo, data ou nome por valor mais plausível. A confirmação humana pode corrigir os campos usados pela minuta, preservando a transcrição bruta original.

`comparacao.py` usa `SequenceMatcher`, similaridade e alinhamento de palavras. Isso é útil para RF06, mas **não corresponde ao cálculo padrão de WER**. O enunciado exige comparação e erros relevantes, não obriga WER. Se a equipe optar por declarar WER, deve implementar distância de edição apropriada, documentar normalização e não renomear a similaridade atual.

## 7. RF07 — diagnóstico detalhado de Text-to-Speech

### 7.1 Implementação encontrada

`src/audio.py:29` define:

```python
sintetizar(texto_aprovado: str, destino: Path, *, cliente: ClienteLLM, config: Config) -> dict
```

O corpo levanta `PendenteDeImplementacao("RF07", "áudio")`.

`fluxo.sintetizar_minuta()` já lê os metadados, aceita apenas status aprovados e compara o hash atual com `revisao.sha256_minuta`. O destino previsto é `resultados/audios/<id>.wav`. Esse controle deve permanecer como ponto de entrada da funcionalidade.

### 7.2 Pendências

- Chamar TTS, decodificar e validar o arquivo retornado.
- Selecionar voz e estilo institucional em configuração rastreável.
- Separar instruções do texto falado.
- Definir tratamento de Markdown, referência de imagem, caminhos e linhas de assinatura.
- Resolver o aviso de campos “não localizado” antes da aprovação.
- Registrar texto efetivamente falado ou sua referência/hash, modelo, voz, estilo, formato e telemetria.
- Conferir auditivamente nomes, protocolos, datas, omissões e acréscimos.
- Documentar acessibilidade e limitações.

### 7.3 Correspondência com o aprovado

O hash atual vincula o arquivo Markdown à aprovação. Inserir um aviso, simplificar texto com LLM ou alterar conteúdo durante a síntese pode romper a correspondência substantiva mesmo que o arquivo original não seja modificado.

Recomenda-se que o aviso de ausência já faça parte do material submetido à aprovação. Exemplo de política a validar pela equipe: “Os campos identificados como não localizado representam informações ausentes no documento.” Esse texto é proposta, não alteração já autorizada do prompt dos colegas.

Se houver preparação determinística para locução, documentar regras e vínculo com o original. Caso a transformação mude conteúdo ou produza versão simplificada, submeter essa versão à conferência antes da síntese. A Aula 05 demonstra simplificação, mas o desafio exige a versão falada da minuta aprovada.

### 7.4 Formato, voz e estilo

WAV é formato comum e já é o destino definido pelo fluxo. Não há necessidade inicial de converter para MP3. Recomenda-se voz predefinida, sem clonagem, português brasileiro, tom claro, institucional e acolhedor, com ritmo pausado e pronúncia verificável de números.

A documentação pública atual confirma `gemini-3.8-flash-tts`, saída WAV e estilo em anotação `speech_metadata`. O campo textual é destinado à recitação literal. Essa confirmação externa valida a viabilidade documental, não uma execução na conta da equipe.

### 7.5 Telemetria

O fluxo atual recebe apenas um dicionário de `sintetizar()`, registra configurações e modelo, mas não usa `_anotar()` com `RespostaLLM`. Assim, tokens e custo não são transportados como nas outras modalidades. Deve haver adaptação mínima, testada e documentada para registrar essa informação sem alterar desnecessariamente o contrato público.

### 7.6 Benefícios e limitações

O áudio amplia acesso para pessoas com deficiência visual, dificuldade de leitura ou preferência por conteúdo falado. Deve coexistir com o texto. Não resolve sozinho necessidades de pessoas surdas, dificuldade cognitiva, falta de equipamento ou linguagem institucional excessivamente complexa. Pronúncia e entonação precisam de validação; voz sintética deve ser identificada.

## 8. Reutilização e contratos de integração

### 8.1 Fluxo de dados

| Função/tipo | Entrada | Saída e uso |
|---|---|---|
| `validar_arquivo()` | Caminho, modalidade e configuração | `ArquivoEntrada` com bytes acessíveis, MIME, extensão, tamanho e SHA-256. |
| `audio.transcrever()` | `ArquivoEntrada`, cliente e configuração | `TextoExtraido`. |
| `TextoExtraido` | Bruto, revisado, lista de incertezas, metadados, resposta e prompt | Persistência, comparação e auditoria. |
| `mascarar()` | Texto revisado e tipos configurados | Texto minimizado e contagens. |
| `extrair_campos()` | Texto minimizado e origem | `ResultadoExtracao.campos`. |
| `normalizar_extracao()` | Campos e categorias | Estrutura compartilhada. |
| `confirmar_campos_criticos()` | Campos e incertezas | Campos confirmados/corrigidos e lista de alterações. |
| `gerar_minuta()` | Campos e referências | `Minuta`, posteriormente salva para revisão. |
| `registrar_decisao()` | ID, decisão, justificativa e revisor | Estado final de revisão e hash do arquivo. |
| `sintetizar_minuta()` | ID da execução | Verificação da aprovação e chamada de TTS. |

Estrutura esperada pela parte textual:

```text
protocolo, data, solicitante, assunto, pedido, categoria,
campos_ausentes, confianca, necessita_revisao, motivo_revisao
```

Categorias atuais: `matricula`, `informacao`, `solicitacao_documentos`, `reclamacao`, `cancelamento`.

O módulo de áudio deve entregar texto revisado. Não deve duplicar a extração de campos ou a geração de minuta.

### 8.2 Artefatos e localização

```text
dados/processados/<caso>/<id>/
  texto_bruto.txt
  texto_revisado.txt
  extracao_texto.json
  comparacao_gabarito.json
  extracao.json

resultados/minutas/<id>.md
resultados/minutas/<id>.json
resultados/audios/<id>.wav
resultados/logs/execucoes.jsonl
```

`extracao_texto.json` deve guardar metadados de áudio e incertezas. Não é necessário criar outro armazenamento paralelo para os mesmos dados.

### 8.3 Preservação do trabalho dos colegas

Não recriar `extrair_campos()`, `gerar_minuta()`, OCR, composição visual, revisão ou auditoria. Não alterar os originais. Preservar assinaturas de `transcrever()` e `sintetizar()`, categorias e esquema dos campos. Uma mudança compartilhada só se justifica para uma lacuna concreta, como telemetria de TTS ou aprovação do texto de locução, e precisa de teste e comunicação ao grupo.

## 9. Tecnologias recomendadas e fundamentação

| Alternativa | Relação com as aulas | Adequação e limitações |
|---|---|---|
| Gemini + `google-genai` | Provedor/SDK nas Aulas 04/06; Interactions na Aula 06; Gemini-TTS discutido na Aula 05. | Melhor compatibilidade com a base existente. Áudio exige adaptação, não cópia direta dos exemplos de STT/TTS OpenAI. |
| OpenAI STT/TTS | Prática direta da Aula 05. | Forte aderência aos exemplos, mas exige SDK, credencial e adaptação do cliente/custos. Alternativa se houver impedimento concreto no caminho atual. |
| Whisper local | Aula 05, modelos abertos e soberania. | STT sem envio da gravação; exige pesos, dependências, hardware e tempo. Não resolve TTS. |
| Kokoro/Chatterbox | Alternativas abertas de TTS da Aula 05. | Exigem integração e avaliação de português; ampliam escopo operacional. |
| Google Cloud Speech/TTS | Aula 05, incluindo credencial de conta de serviço. | Não é a mesma integração da Gemini API; adiciona configuração e dependências. |
| FFmpeg/ffprobe | Requisitos e exemplo 04 da Aula 05. | Recomendado para duração/validação local; instalação futura precisa ser documentada. |

**Escolha recomendada:** manter Gemini, o cliente compartilhado e WAV; usar `ffprobe` para inspeção local. Não há necessidade demonstrada de `pydub`, `librosa`, LangChain, banco de dados ou servidor web.

### 9.1 Custos

Os números de OpenAI presentes na Aula 05 são históricos acadêmicos e não foram revalidados como orçamento atual. Para alternativas locais, ausência de cobrança de API não elimina custo de hardware, energia, instalação e operação.

A página oficial Google consultada informa, para Gemini 3.8 Flash TTS padrão pago até 31/12/2026, US$ 0,50 por milhão de tokens de texto de entrada e US$ 9 por milhão de tokens de áudio de saída, com camada gratuita sujeita a limites. O projeto contém essas tarifas para TTS. A tarifa não comprova disponibilidade da cota ou custo de uma execução concreta. O relatório de execução deve utilizar consumo retornado pela API, distinguindo estimativa de cobrança efetiva.

## 10. Arquivos previstos para implementação posterior

Todos os itens desta seção são propostas, não alterações realizadas.

| Arquivo | Ação prevista | Justificativa |
|---|---|---|
| `src/audio.py` | Modificar | Validação técnica, duração, STT, revisão conservadora, TTS e validação de saída. |
| `prompts/transcricao_v1.md` | Criar | Tarefa de transcrição fiel, incertezas e proteção contra instruções no áudio. |
| `dados/gabaritos/audio-01.json` | Criar | Referência humana anterior à inferência. |
| `testes/test_audio.py` | Criar | Testes específicos sem API real. |
| `testes/test_fluxo_e_revisao.py` | Modificar pontualmente | Substituir expectativa de RF06 pendente e completar validações de integração. |
| `config.json` | Modificar pontualmente | Voz, estilo e parâmetros não sensíveis necessários. |
| `src/fluxo.py` | Modificar somente se necessário | Transportar telemetria de TTS e verificar existência/validade do artefato antes de sucesso. |
| `documentacao/audio_e_acessibilidade.md` | Criar | Decisões, resultados, benefícios, limitações e critérios de qualidade. |
| `README.md` | Atualizar | Pré-requisitos, comandos e estado real das funcionalidades. |
| `documentacao/uso_de_ia.md` | Complementar com o grupo | Registrar Codex e consolidar ferramentas efetivamente utilizadas. |
| Novo prompt de minuta versionado | Condicional | Apenas se aviso de lacunas ou texto de locução exigir mudança do material aprovado. Não editar silenciosamente o prompt existente. |

Não se prevê alteração de `TextoExtraido`, do esquema de extração ou dos módulos de imagem. `requirements.txt` só precisará mudar se uma dependência Python adicional se mostrar necessária; `ffprobe` é dependência de sistema, não pacote a incluir automaticamente ali.

## 11. Plano de implementação em etapas

| Etapa | Objetivo | Dependências e conteúdo acadêmico | Critério de conclusão |
|---|---|---|---|
| 1 | Elaborar referência humana do áudio. | Audição do original; seção 6 do enunciado e Aula 05. | Gabarito datado, com autoria, texto e valores críticos conferidos antes da inferência. |
| 2 | Validar decodificação e medir duração. | `ArquivoEntrada`, `ffprobe`, Aula 05 exemplo 04. | Duração real; arquivo inválido/ferramenta ausente falham claramente antes da API. |
| 3 | Implementar STT preservando contrato. | Cliente central, prompt seguro; Aulas 03/05/06. | `TextoExtraido` válido com bruto/revisado/incertos/idioma/modelo/duração/resposta/prompt. |
| 4 | Integrar comparação e confirmação. | `processar_caso()`, gabarito e módulos textuais dos colegas. | Artefatos persistidos, erros apontados e confirmação crítica anterior à minuta. |
| 5 | Definir política de locução aprovada. | Equipe de texto/revisão; Aulas 03/05. | Markdown e lacunas tratados por regra explícita; nenhum acréscimo substantivo depois da aprovação. |
| 6 | Implementar TTS e telemetria. | Modelo/voz configurados e fluxo de aprovação existente. | WAV válido, configurações e consumo registrados; bloqueios preservados. |
| 7 | Avaliar resultados reais autorizados. | Ambiente preparado, cota controlada e revisor humano. | Transcrição comparada e áudio ouvido; erros e decisões documentados, sem simular sucesso. |
| 8 | Finalizar documentação e evidências. | Resultados das etapas anteriores e responsabilidade conjunta RF12/RF13. | Reprodução pelo README, protocolo de avaliação, custos/limites e caso aprovado mais rejeitado/corrigido. |

As etapas de código podem ser validadas inicialmente com SDK falso e mídia de teste. Chamadas reais não são necessárias para os testes unitários, mas são necessárias para demonstrar o requisito acadêmico de processamento efetivo.

## 12. Estratégia de testes e evidências

### 12.1 Testes de validação local

- Arquivo suportado e decodificável.
- Arquivo inexistente, vazio, extensão proibida e tamanho excedido.
- Arquivo arbitrário renomeado como `.mp3`.
- `ffprobe` ausente, falha de processo, saída sem duração, duração não numérica ou inválida.
- Limites da requisição inline sem consumir API.
- Diferenciar duração da mídia e latência de chamada.

### 12.2 Testes de STT com SDK falso

- Modelo selecionado pela configuração e mídia representada no formato esperado.
- Uso exclusivo de `ClienteLLM` e instrução de segurança.
- Transcrição vazia, JSON inválido e tipos incompatíveis.
- Preservação de bruto e revisão conservadora.
- Trecho incerto em nome, protocolo ou data.
- Metadados completos e resposta/prompt disponíveis para auditoria.
- Erros do provedor propagados na hierarquia existente.

### 12.3 Testes de integração RF06

- Texto revisado chega à extração após mascaramento.
- Gabarito gera comparação e valores críticos ausentes são registrados.
- Confirmação humana ocorre antes de `gerar_minuta()`.
- Correção do campo não altera o áudio original nem o texto bruto.
- Cancelamento não se transforma em aprovação.
- Atualizar o teste que hoje espera `PendenteDeImplementacao("RF06")`.

### 12.4 Testes de TTS

- Minuta aguardando revisão/rejeitada/alterada não chama síntese.
- Minuta aprovada e aprovada com correção seguem com o texto conferido.
- Estilo é separado do conteúdo falado.
- Lacunas seguem a política aprovada.
- Base64 inválido, mídia ausente ou arquivo inválido não viram sucesso.
- Arquivo gravado tem formato compatível com a extensão.
- Telemetria, voz, estilo e relação com a revisão são registrados.
- Não usar gravação inexistente no teste como comprovação de áudio válido.

### 12.5 Validação humana e artefatos

| Requisito | Evidência mínima |
|---|---|
| RF06 | Original/hash; referência humana; bruto e revisado; idioma/modelo/duração; comparação; análise dos erros críticos; confirmação anterior à minuta. |
| RF07 | Minuta e aprovação/hash; texto de locução, quando aplicável; WAV; voz/estilo/modelo/formato; registro de audição e conferência. |
| RF11 | Eventos relacionados ao caso/execução, com duração, modelo, parâmetros, prompts, resultado e falhas. |
| RF13 | Esperado/obtido, classificação de gravidade, justificativa e decisão; taxas e riscos residuais. |

Uma classificação proposta para a avaliação é: crítico para erro que muda identidade/protocolo/data ou inventa ato; relevante para omissão que compromete o pedido; apresentação para pontuação sem mudança de sentido. Essa rubrica é proposta de implementação e ainda deve ser aplicada, não resultado observado.

Ruído moderado deve ser demonstrado conforme o enunciado. Não foi confirmado se a entrada existente já satisfaz o cenário. Eventual variante futura deve preservar o original, ter proveniência e gabarito, sem inserir dados reais.

## 13. Riscos, problemas e dependências

### 13.1 Evidências e documentação

**Resultados ausentes:** documentação relata processamento real e testes, mas as pastas locais não contêm artefatos correspondentes. Não é possível reconstruir essas execuções neste clone.

**README desatualizado:** descreve texto como contrato pendente e diz que modalidades param na compreensão, apesar de o commit atual implementar extração e minuta.

**Experimento RF02:** a matriz declara ausência de alucinação, mas saídas B/C dizem que a demanda foi encaminhada a setor responsável, ato não demonstrado pelos campos usados como entrada. Essa avaliação precisa de revisão pelo responsável. Faltam rastreabilidade do metaprompt e tempos efetivamente medidos. Ausência de parâmetros de sampling não demonstra determinismo.

**Uso de IA:** `documentacao/uso_de_ia.md` registra Antigravity/Gemini, enquanto o contexto da equipe informa Claude e Codex. O documento pode refletir somente parte do trabalho; deve ser consolidado sem inventar atribuições.

### 13.2 Robustez de entrada e saída

**Extensão não comprova áudio:** validação compartilhada aceita arquivo pelo nome/tamanho, sem decodificar.

**Falhas de esquema:** `normalizar_extracao()` pressupõe `campos_ausentes` iterável; valor numérico pode causar erro. A confiança média com `necessita_revisao=False` não é forçada a revisão, apesar da instrução do prompt para confiança não alta.

**Correção sem renormalização:** depois da confirmação crítica, o fluxo não recalcula `campos_ausentes`; campo preenchido pode continuar marcado ausente. Trata-se de assunto compartilhado, não de motivo para reformular o módulo dos colegas.

**Exceções locais:** arquivo corrompido, falha de ferramenta ou decodificação devem ser traduzidos para erro compreensível; não presumir que `ErroLLM` cobre erros que ocorrem antes/depois da API.

### 13.3 Revisão e aprovação

**Proteção local:** hash verifica consistência com os metadados, não autentica o operador ou impede edição dos dois arquivos. Não há assinatura ou controle de acesso forte, o que deve ser explicitado como limitação do protótipo.

**Entrada correta:** `audio.sintetizar()` isolada recebe só texto; quem impõe aprovação é `fluxo.sintetizar_minuta()`. A documentação deve orientar o uso desse fluxo.

**Correção manual:** `aprovar_com_correcao` registra decisão/hash, mas não oferece editor ou histórico de diferenças. A correção deve ser feita e conferida antes da decisão. `nova_geracao` registra pedido, não dispara uma nova execução automaticamente.

**Indicadores:** a taxa “com correção” inclui aprovadas sem correção e com correção, segundo a fórmula atual. O nome deve ser explicado. A confirmação de dados críticos não identifica o operador como a revisão final.

### 13.4 Rastreabilidade e custos

**Telemetria TTS incompleta:** retorno atual não transporta `RespostaLLM` ao evento; o teste de bloqueio usa sintetizador falso que não grava arquivo.

**Tokens de pensamento:** `_tokens()` soma pensamento ao total de saída e o comentário admite não confirmar se já está incluído. Há risco de dupla contagem e custo superestimado; precisa de conferência do contrato do SDK antes de apresentar precisão financeira.

**Prompt de sistema:** não possui hash próprio registrado nas chamadas da mesma forma que o prompt de tarefa. Reconstrução rigorosa depende do versionamento e da preservação dessas referências.

**Comparação:** `SequenceMatcher` não é WER. Gabaritos de texto usam nomes de campos em `dados_criticos`, enquanto a função de conferência espera valores literais; hoje a comparação integrada é aplicada às modalidades não textuais, mas a convenção deve ser esclarecida.

### 13.5 Privacidade e dependência externa

- Áudio e imagem são enviados integralmente ao provedor; mascaramento textual posterior não desfaz essa exposição.
- Padrões de CPF/RG/e-mail/telefone não cobrem todos os possíveis identificadores.
- Correções humanas podem reintroduzir dados antes da geração da minuta, sem nova chamada explícita a `mascarar()`.
- `store=False` não deve ser apresentado como garantia universal sobre retenção, treinamento ou política contratual.
- Faltam matriz RF12 e protocolo completo RF13.
- Internet, serviço, versão do SDK, cota e política do plano condicionam chamadas reais.
- Testes importam classes de erro de módulo privado do SDK; atualização pode exigir manutenção.
- `ffprobe` não está disponível no PATH observado; sua instalação não foi autorizada nem executada nesta etapa.
- Referência a brasão em Markdown não comprova apresentação final com imagem; `arquivo_renderizado` não é produzido pela função atual.

## 14. Próxima atividade recomendada

**Primeiro incremento de código após autorização:** implementar auxiliares de validação técnica e medição local de duração em `src/audio.py`, baseados em `ffprobe`, com testes isolados e sem chamadas externas.

O incremento deve preservar contratos, rejeitar arquivo inválido e apresentar falha clara se faltar a ferramenta. Não deve retornar duração inventada nem usar a latência da API como duração da mídia.

**Pré-condição da primeira inferência STT:** elaborar o gabarito a partir de audição humana do original. A implementação não deve antecipar ou inventar essa referência.

Depois, implementar RF06; demonstrar integração com extração/minuta; definir tratamento aprovado de lacunas; implementar RF07; completar documentação e evidências. Não há autorização neste relatório para executar essas etapas.

## 15. Fontes e referências examinadas

### 15.1 Fontes locais

- Materiais principais e exemplos das Aulas 01 a 07 identificados na seção 3.
- `arquivos do desafio/Desafio_01-Pratico_IA_Generativa_Aulas_01_a_07.docx.pdf` e cópia no repositório.
- `FIC_DEV-IA-Desafio1/enunciado/`, especialmente requisitos, cenários, fluxo, entregáveis e restrições.
- `README.md`, `AGENTS.md`, `CLAUDE.md`, `config.json`, `requirements.txt` e `.gitignore`.
- Módulos de `src/` listados na seção 4; prompts de extração, sistema, minuta e OCR.
- `documentacao/experimento_prompts.md`, `visao_e_imagem.md`, `uso_de_ia.md` e índice documental.
- Gabaritos `_modelo.json`, `texto-01.json`, `texto-injection.json` e `imagem-01.json`.
- Testes de entradas/extração, fluxo/revisão, cliente, auditoria/CLI, privacidade/prompts e imagem, além de falsos e fixtures.

### 15.2 Documentação pública consultada na análise anterior

- [Google — Audio understanding](https://ai.google.dev/gemini-api/docs/audio): entrada de áudio e limite total da requisição inline.
- [Google — Text-to-speech generation](https://ai.google.dev/gemini-api/docs/speech-generation): modelo TTS, WAV, voz, texto literal e metadados de estilo.
- [Google — Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing): tarifas e distinções entre camadas consultadas em 18/10/2026.
- [Google — Interactions API](https://ai.google.dev/api/interactions-api): referência pública da interface usada pelo projeto.

As consultas públicas complementam a verificação de compatibilidade; não tornam uma tecnologia ensinada quando ela não consta dos materiais, nem comprovam testes reais do projeto.

## 16. Registro de encerramento

Este relatório contém diagnóstico e propostas. Não contém resultados de testes executados nesta sessão, aprovação de artefatos ou declaração de RF06/RF07 concluídos. A única criação autorizada nesta etapa é `RELATORIO_ANALISE_RF06_RF07.md`, fora da pasta do repositório. Implementação e instalação continuam pendentes de autorização.
