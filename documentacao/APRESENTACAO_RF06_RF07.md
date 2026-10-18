# Participação no Desafio Prático 1 — RF06 e RF07

Material de até **3 slides**, com notas de demonstração. Verificado em 18/10/2026.
As notas e comandos não representam execuções de inferência já realizadas.

## Slide 1 — Minha responsabilidade e tecnologias

**Objetivo:** transformar mensagem de voz fictícia em texto verificável (RF06)
e disponibilizar a minuta aprovada em áudio acessível (RF07).

- **Speech-to-Text:** o modelo ouve o arquivo e produz uma transcrição. O texto
  bruto é preservado; a revisão local ajusta somente espaços e quebras de linha.
- **Text-to-Speech:** o modelo transforma o texto aprovado em fala, com voz e
  entonação institucional. O arquivo WAV passa por validação técnica.
- **Tecnologias:** Python, Gemini/SDK `google-genai` 2.31.0, ffprobe e WAV.
  Modelos configurados: `gemini-3.8-flash` (STT) e `gemini-3.8-flash-tts` (TTS),
  voz `Kore`, estilo em português brasileiro.
- **Relação com o curso:** Aula 01 — limites e responsabilidade; Aulas 02–04 —
  ferramentas, prompts seguros, APIs e credenciais; Aula 05 — STT/TTS e ffprobe;
  Aula 06 — integração multimodal Gemini. Aula 07 integra o contexto do desafio,
  mas geração de imagens não faz parte desta responsabilidade.
- **Acessibilidade:** áudio amplia o acesso para pessoas com deficiência visual
  ou dificuldade de leitura; não substitui texto, atendimento a pessoas surdas
  nem conferência de pronúncia e compreensão.

## Slide 2 — Fluxos e resultados realmente comprovados

**RF06:** áudio original → validação de extensão/tamanho/formato/duração → STT →
bruto e revisado → comparação com referência humana → conferência de nomes,
protocolos e datas antes da minuta. Aqui não executamos a geração da minuta.

**RF07:** minuta aprovada pela equipe → verificação de status e hash → texto de
locução conservador → TTS → WAV validado → conferência auditiva humana.
Campos “não localizado” exigem aviso já presente no texto aprovado; nenhum aviso
é acrescentado depois da aprovação.

**Resultados locais comprovados nesta etapa:**

- Original MP3 validado por ffprobe: **89,16 segundos**. SHA-256:
  `aa396a4bc0d990ef05b031d8771cbad2d46ebc45ec1ad1adf4d23cb3c7cd2fa6`.
- SDK 2.31.0 instalado; cliente Interactions importável e interface aceita kwargs.
  Isso não comprova aceitação de uma requisição ou autenticação no serviço.
- A chave é carregada do `.env`; não há variável de ambiente preexistente em
  conflito nem espaços internos detectados. Seu valor não foi mostrado.
- **Não há transcrição Gemini bem-sucedida ou WAV institucional produzido.**
  O log existente registra uma tentativa anterior com `AutenticacaoInvalida`.
- O gabarito contém referência fornecida pelo integrante, mas ainda não está
  validado. Não foi alterado nesta etapa. Não há minuta aprovada disponível.

<details>
<summary>Notas de demonstração — comandos somente de áudio</summary>

Executar da raiz do repositório, com o ambiente do projeto:

```bash
source .venv/bin/activate
ffprobe -v error -show_entries format=format_name,duration -of json dados/originais/entrada_audio.mp3
xdg-open dados/originais/entrada_audio.mp3
```

Ouvir a gravação e confirmar a referência existente. Falta preencher
`elaborado_por`, resolver a ambiguidade “no turno no turno” (sem presumir
“noturno”), conferir nomes, protocolo, datas, CPF/RG e e-mail contra o áudio,
confirmar data/autoria da referência e só então marcar
`validado_por_humano=true`. Não usar saída do modelo como referência independente.
`campos_ausentes_esperados` contém descrições de lacunas; não é avaliação automática
completa de campos. A comparação reutilizada usa similaridade, não WER padrão.

**RF06 isolado, somente após autorização explícita para consumo da API:**
o bloco abaixo chama apenas o módulo de áudio e persiste suas evidências usando
os componentes existentes. Não chama extração de campos, minuta, OCR ou imagens.
É uma instrução de reprodução, não um script novo instalado no projeto nem uma
inferência executada nesta etapa.

```bash
python - <<'PY'
import json
from src.audio import transcrever, gabarito_validado
from src.audit import Auditoria, Evento, novo_id
from src.comparacao import comparar_com_gabarito
from src.config import carregar_config
from src.entradas import validar_arquivo
from src.llm_client import ClienteLLM

c = carregar_config()
caso = c.caso('audio-01')
g = json.loads((c.raiz / caso['gabarito']).read_text(encoding='utf-8'))
assert gabarito_validado(g), 'Referência humana ainda não validada'
a = validar_arquivo(c.raiz / caso['arquivo'], 'audio', c)
cliente = ClienteLLM(c)
id_execucao = novo_id()
pasta = c.caminho('processados') / 'audio-01' / id_execucao
pasta.mkdir(parents=True, exist_ok=False)
auditoria = Auditoria(c)
evento = Evento(id_execucao=id_execucao, caso_id='audio-01', modalidade='audio',
                arquivo_origem=caso['arquivo'], etapa='extracao_texto',
                modelo=c.modelo('transcricao'))
try:
    r = transcrever(a, cliente=cliente, config=c)
    (pasta / 'texto_bruto.txt').write_text(r.texto_bruto, encoding='utf-8')
    (pasta / 'texto_revisado.txt').write_text(r.texto_revisado, encoding='utf-8')
    (pasta / 'extracao_texto.json').write_text(json.dumps({
        'metadados': r.metadados, 'trechos_incertos': r.trechos_incertos
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    comparacao = comparar_com_gabarito(r.texto_bruto, r.texto_revisado, g)
    (pasta / 'comparacao_gabarito.json').write_text(
        json.dumps(comparacao, ensure_ascii=False, indent=2), encoding='utf-8')
    evento.com_resposta(r.resposta)
    evento.versao_prompt = r.prompt.identificador
    evento.hash_prompt = r.prompt.hash
    evento.saida = c.relativo(pasta)
    print('Evidências RF06:', pasta)
except Exception as erro:
    # Só a classe: não copiar mensagens brutas do provedor ou credenciais.
    evento.erro = type(erro).__name__
    raise SystemExit('RF06 interrompido; verifique o tipo de falha no log.') from None
finally:
    auditoria.registrar(evento)
PY
```

Após executar: conferir e registrar erros relevantes na comparação e confirmar os
dados críticos antes de a equipe gerar sua minuta. Não modificar a referência
para fazê-la coincidir com o modelo. Não apresentar simples presença textual como
validação humana já concluída.

**RF07:** obter da equipe o ID e arquivos de uma minuta efetivamente aprovada,
com os metadados existentes da revisão. Não criar aprovação automática. Se a
minuta ainda aguarda revisão, a pessoa responsável usa o comando interativo:

```bash
python -m src.main revisar <id_da_minuta>
```

Se já foi aprovada, não revisar novamente nem editar seu conteúdo ou metadados
para contornar hash. Havendo lacunas sem aviso, devolver à equipe para uma versão
correta e revisada. Somente após autorização explícita para consumo TTS:

```bash
python -m src.main audio-minuta <id_da_minuta_aprovada>
ffprobe -v error -show_entries format=format_name,duration -of json resultados/audios/<id_da_minuta_aprovada>.wav
xdg-open resultados/audios/<id_da_minuta_aprovada>.wav
```

Ouvir integralmente contra o texto aprovado e registrar quem conferiu, data e
existência ou ausência de divergências em nomes, números, lacunas e conteúdo.
Nenhuma conferência auditiva foi registrada como realizada nesta etapa.

Não usar `python -m src.main processar audio-01` nesta demonstração isolada:
esse comando também executa extração e geração de minuta, fora do recorte pedido.

</details>

## Slide 3 — Testes, evidências e conclusão honesta

- **Testes executados nesta etapa:** 57 testes e 26 subtestes aprovados, 0 falhas,
  cobrindo áudio, integração/revisão e cliente/erros de API, sem consumo de modelo.
  Não confundir com a suíte completa de 110 testes informada anteriormente.
- **Evidência de testes:**
  `documentacao/evidencias_validacao_audio/apresentacao_testes_audio.txt`.
- **Evidências existentes para mostrar:** áudio original;
  `dados/gabaritos/audio-01.json` (ainda não validado);
  `resultados/logs/execucoes.jsonl` — execução `1d8c1355f434`, erro na transcrição.
  Mostrar o tipo do erro e a etapa, sem abrir `.env` na apresentação.
- **RF06 pendente:** confirmação da referência, resolução da falha de acesso,
  autorização e transcrição/comparação reais, seguidas de conferência crítica.
- **RF07 pendente:** minuta aprovada da equipe, autorização TTS, geração WAV e
  conferência humana de correspondência. Não há áudio final nem divergência
  auditiva comprovada para declarar.
- **Autenticação:** carregar a chave não prova que ela seja válida ou autorizada.
  O cliente classifica HTTP 401/403 e `API_KEY_INVALID` como autenticação inválida;
  o log disponível não guarda status/detalhe suficiente para distinguir essas
  causas. Não foi comprovado defeito de código. A equipe deve conferir chave,
  projeto/permissões/restrições no Google AI Studio. Não se fez nova chamada.

<details>
<summary>Notas — reprodução dos testes e evidências esperadas após autorização</summary>

```bash
source .venv/bin/activate
python -m pytest testes/test_audio.py testes/test_fluxo_e_revisao.py testes/test_llm_client.py -q
```

Os testes usam respostas falsas; não comprovam inferência, autenticação ou
correspondência de fala. Evidências reais ainda a obter, exclusivamente RF06/RF07:

- RF06: bruto/revisado, JSON com idioma/modelo/duração da gravação e requisição,
  comparação com referência validada e erros relevantes, conferência dos críticos.
- RF07: minuta aprovada e hash, WAV, voz/modelo/estilo/duração/configurações nos
  metadados e log, registro humano da audição/correspondência.

A documentação de acessibilidade e limitações já existe em
`documentacao/audio_e_acessibilidade.md`. Nenhuma evidência foi criada em nome de
revisor humano. Nenhum commit, push, alteração de contrato ou módulo dos colegas.
O gabarito e a transcrição fornecida pelo integrante permaneceram intactos.

</details>
