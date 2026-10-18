# Validação técnica RF06/RF07 — FIC_DEV

**Data:** 18/10/2026. **Branch:** `feat/audio-rf06-rf07`.
**Resultado:** 30 testes distintos aprovados, 0 testes executados falhos.
Quatro desses testes de integração foram repetidos separadamente e passaram;
não devem ser somados como outros quatro testes distintos. Os três comandos
pytest falharam antes da coleta: são verificações bloqueadas, não testes aprovados.
**RF06 e RF07 ainda não estão prontos para inferência real neste ambiente.**

Nenhuma chamada de modelo, teste de chave, consulta autenticada, inferência ou
operação de cobrança foi executada. Consultas públicas à documentação não são
inferência. Nenhum commit, push, merge ou alteração de módulo dos colegas.


## Atualização — diagnóstico e preparação do ambiente (18/10/2026)

**Esta seção é o estado vigente; as seções numeradas abaixo preservam o histórico
da validação anterior.** Nesta continuação não se criou outro ambiente virtual:
foi utilizado exclusivamente o `.venv` do projeto. Nenhuma funcionalidade foi
reimplementada e nenhum código de modalidade ou dos colegas foi modificado.

### Causa identificada do bloqueio

Além do erro de resolução em `pypi.org`, `files.pythonhosted.org`,
`archive.ubuntu.com` e `ai.google.dev`, foi testada a criação local de sockets
TCP e UDP: ambas falham com `PermissionError`, errno 1 (`Operation not permitted`).
`resolvectl status` também é bloqueado no acesso ao barramento do sistema.
Isso demonstra uma restrição de rede/processo desta sessão, anterior ao acesso
aos servidores de pacotes. Não demonstra que o DNS do computador esteja avariado.
Não se deve editar `/etc/resolv.conf` ou trocar DNS público para tentar resolver.

O sistema usa o stub `127.0.0.53` do systemd-resolved. Variáveis comuns de proxy e
de índice pip não estão definidas. A nova instalação de `requirements.txt` no
`.venv` falhou ao tentar conexão com PyPI; a mensagem final sobre versão não
encontrada não permite concluir inexistência de pacote. Não houve download ou
instalação bem-sucedida de dependência, nem alteração global de rede/proxy/DNS.

**Intervenção externa necessária:** executar a preparação em um terminal com
rede permitida ou disponibilizar à sessão acesso de rede autorizado. Não há
correção dentro do projeto capaz de remover a proibição de criar sockets. Não
foi solicitado sudo nem tentado contornar essa restrição.

### Ambiente e testes desta continuação

- Python 3.12.3; `.venv` preexistente preservado. Nenhum venv duplicado.
- SDK `google-genai` e pytest continuam ausentes; dotenv 1.2.4 é reutilizado por
  PYTHONPATH acadêmico e Pillow disponível é 10.2.0, diferente do requisito 13.0.0.
- `.venv/pyvenv.cfg` ainda permite pacotes de sistema. Após instalar as versões
  corretas, a preparação abaixo reconfigura o mesmo ambiente sem essa herança.
- Chave Gemini ausente tanto no ambiente quanto no `.env` do projeto (inexistente).
  Somente booleanos foram exibidos; autenticação e cota não foram consultadas.
- Modelos mantidos: `gemini-3.8-flash` em STT/texto e `gemini-3.8-flash-tts` em
  TTS, voz `Kore`. Compatibilidade continua documental; SDK instalado não existe
  para uma verificação executável, e respostas falsas não substituem isso.
- 30 testes distintos de áudio aprovados, 0 falhos. Os 4 testes selecionados de
  integração passaram novamente, mas já fazem parte dos 30.
- Comandos pytest de áudio, integração e suíte completa foram repetidos e
  bloqueados antes da coleta por `No module named pytest`. Não se declara
  regressão dos colegas ausente com base em suíte que não pôde ser executada.
- Sintaxe: 26 arquivos Python válidos. Não houve defeito reproduzido que exigisse
  correção de código RF06/RF07 nesta etapa.

Logs novos: `evidencias_validacao_audio/ambiente_rede.txt`, `ambiente_pip.txt`,
`ambiente_unittest_audio.txt`, `ambiente_unittest_integracao.txt` e
`ambiente_pytest_{audio,integracao,completo}.txt`. Logs anteriores foram preservados.

### Preparação no próprio `.venv`, sem ambiente adicional

Executar fora da restrição de rede desta sessão, na raiz do projeto:

```bash
cd '/home/andre/estudos/ficdev2026/Desafio modulo 3/FIC_DEV-IA-Desafio1'
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
python -m pytest testes/test_audio.py
python -m pytest testes/test_fluxo_e_revisao.py testes/test_audit_e_main.py
python -m pytest
```

`python3 -m venv .venv` reutiliza o diretório e, sem a opção
`--system-site-packages`, desativa a herança. Não usar `--clear`, apagar o venv
ou trocar versões para ocultar falha de instalação. Não executar a aplicação
antes de uma instalação bem-sucedida. Se uma versão realmente não for encontrada
com rede funcional, registrar a evidência e avaliar com o grupo; não presumir
esse diagnóstico a partir da falha de conexão atual.

### FFmpeg sem sudo: abordagem nativa preparada

`ffprobe`, `ffmpeg` e `ffplay` estão ausentes. Os índices APT locais conhecem o
pacote Ubuntu noble `ffmpeg` versão candidata `7:6.1.1-3ubuntu5`. A simulação
`apt-get --simulate install ffmpeg` prevê só esse pacote novo, sem adicionar
bibliotecas. Não há `.deb` no cache para extrair sem download. A simulação não
instala nada nem confirma que o arquivo ainda existe no servidor.

Após restabelecer rede, há uma opção sem alterar pacotes globais: baixar o pacote
nativo e extraí-lo dentro do mesmo `.venv`. Procedimento preparado, **não executado**:

```bash
cd '/home/andre/estudos/ficdev2026/Desafio modulo 3/FIC_DEV-IA-Desafio1'
mkdir -p .venv/ffmpeg/pacotes
(
  set -e
  cd .venv/ffmpeg/pacotes
  apt-get download ffmpeg
  for pacote_ffmpeg in ffmpeg_*.deb; do
    dpkg-deb --extract "$pacote_ffmpeg" ..
  done
)
export PATH="$PWD/.venv/ffmpeg/usr/bin:$PATH"
ffprobe -version
ffmpeg -version
```

O pacote é obtido pelo APT configurado do sistema, não por download de executável
avulso de terceiros. A extração não registra instalação no dpkg nem modifica
`/usr`; o PATH vale para o terminal atual. Validar as versões/comandos antes do
uso; bibliotecas ausentes ou índice desatualizado precisam ser tratados com o
administrador, sem alteração global automática. Repetir o `export PATH` nos
terminais de demonstração. Esse preparo não deve ser descrito como FFmpeg já
instalado ou testado nesta sessão.

Alternativa administrativa, apenas em sessão privilegiada já autorizada:
`apt-get install ffmpeg`. O agente não executou esse comando e não usou sudo.

### Gabarito RF06 e audição do original

O modelo `dados/gabaritos/audio-01.json` já existe no formato esperado, com
`validado_por_humano=false`, referência/autoria/data/críticos vazios. Foi
preservado assim; nenhuma transcrição foi inventada. O original continua igual
à cópia fornecida (SHA-256 registrado na seção 4).

Caminho absoluto para audição:

`/home/andre/estudos/ficdev2026/Desafio modulo 3/FIC_DEV-IA-Desafio1/dados/originais/entrada_audio.mp3`

`xdg-open` foi localizado. Em um terminal da sessão gráfica do computador:

```bash
xdg-open '/home/andre/estudos/ficdev2026/Desafio modulo 3/FIC_DEV-IA-Desafio1/dados/originais/entrada_audio.mp3'
```

Ou abrir esse arquivo pelo gerenciador de arquivos. Não se iniciou reprodução
nesta sessão nem se afirma que o aplicativo gráfico foi testado. Após extração
do pacote e PATH acima, `ffplay dados/originais/entrada_audio.mp3` é outra opção,
ainda não validada aqui. Ouvir integralmente, preencher texto e valores críticos
literais e só então validar a referência. A validação de áudio e os comandos
pagos permanecem separados nas seções 7 e 8 abaixo.

### RF07 e intervenções humanas indispensáveis

O fluxo de revisão/hash foi reconferido: somente `aprovada` ou
`aprovada_com_correcao`, com SHA-256 compatível, segue para síntese. Nenhuma minuta
foi criada ou aprovada em nome de alguém. As seções 7 e 8 contêm o procedimento
reproduzível; agora apontam para o `.venv` do próprio projeto.

Antes de aprovação, incluir o aviso de lacunas se necessário e conferir a locução.
Após autorização de custos: processar o caso, conferir críticos, revisar a minuta
pelo CLI e somente então executar `audio-minuta`. Não editar metadados para
contornar aprovação ou hash. A audição e decisão finais continuam humanas.

**Prontidão atual:** RF06 e RF07 seguem bloqueados para inferência real. As ações
externas mínimas são: permitir rede/preparar as dependências no mesmo venv,
disponibilizar FFmpeg (a opção local dispensa administrador), configurar chave e
cota Gemini, validar gabarito e minuta, e autorizar consumo antes de inferir.
Nenhum outro desenvolvimento de funcionalidade foi identificado como necessário
pelos testes disponíveis. A confirmação da suíte completa/SDK continua pendente,
portanto não se garante que inexistam defeitos ainda não exercitados.

**Git:** branch e HEAD preservados, sem commit/push/stage. Nesta continuação só
este relatório foi atualizado e foram acrescentadas evidências com prefixo
`ambiente_`; todos os demais arquivos preexistentes foram preservados.

---

## Histórico — validação anterior


## Estado para versionamento — 18/10/2026

Esta é a síntese vigente; os diagnósticos de ambiente abaixo são históricos.
A suíte completa foi executada novamente antes do commit: **110 testes e 26
subtestes aprovados, 0 falhas**, sem chamadas Gemini. Evidência:
`evidencias_validacao_audio/commit_pytest_completo.txt`.

O ambiente já dispõe do SDK 2.31.0, pytest 9.1.1 e ffprobe; o MP3 foi validado
com 89,16 segundos. O gabarito contém referência fornecida pelo integrante,
mas permanece com `validado_por_humano=false` e autoria pendente. Nenhuma
validação humana foi inventada. Ainda faltam confirmação da referência e dos
dados críticos, verificação do acesso Gemini após a falha de autenticação
anterior, inferências autorizadas, minuta efetivamente aprovada e audição do WAV.
RF06/RF07 não são declarados integralmente homologados.

O commit reúne implementação, prompt, testes, configuração não sensível,
gabarito pendente, documentação, relatórios históricos e slides. A análise
inicial foi arquivada em `RELATORIO_ANALISE_RF06_RF07.md`, preservando o original
fora do repositório. Arquivos de credenciais, ambientes, caches e artefatos
temporários não integram o commit. Não foi executado push.

## 1. Inspeção e preservação

Foram relidos o relatório de implementação, documentação de acessibilidade,
AGENTS, README, configuração, requisitos e os módulos de áudio/fluxo. A árvore
já continha 7 arquivos rastreados modificados e 6 arquivos novos da implementação.
Essas alterações foram preservadas. O HEAD continua em
`bf91e841c982a95cafd14afd398e2d58a2ac8731`.

Um inventário SHA-256 inicial dos arquivos do projeto foi comparado ao final:
nenhum arquivo preexistente foi alterado nesta validação. Este relatório e a
pasta de evidências são novos. O ambiente virtual de inspeção criado
provisoriamente dentro do projeto foi removido após a tentativa; o ambiente
isolado para instalação ficou em `/tmp/ficdev-validacao-venv`.

## 2. Estado do ambiente

| Item | Detectado | Resultado |
|---|---|---|
| Sistema | Linux Mint 22.3, base Ubuntu noble | Sem mudanças de sistema. |
| Python | 3.12.3 | Compatível com mínimo documentado de 3.10. |
| `.venv` existente | `include-system-site-packages=true` | Preservado; não representa isolamento completo das bibliotecas. |
| Venv isolado novo | `/tmp/ficdev-validacao-venv`, sem pacotes de sistema | Criado; instalação não concluída por DNS. |
| `google-genai` | Ausente | Requer `2.31.0`; importação executada e bloqueada. |
| `pytest` | Ausente | Requer `9.1.1`; bloqueia coleta da suíte original. |
| `python-dotenv` | 1.2.4 pelo PYTHONPATH acadêmico | Versão requerida; não instalado no venv isolado novo. |
| Pillow | 10.2.0 do sistema, via `.venv` existente | Diverge do requisito 13.0.0. |
| ffprobe | Ausente no PATH | Inspeção real bloqueada. |
| FFmpeg | Ausente no PATH | Não instalado nesta etapa. |
| `GEMINI_API_KEY` no ambiente | Não presente/não vazia: falso | API não configurada. |
| `.env` do projeto | Ausente | Nenhum segredo foi exibido. |
| Minutas em `resultados/minutas/*.json` | 0 | Nenhuma minuta aprovada disponível para TTS real. |

A variável foi verificada somente por presença booleana, tanto no ambiente quanto
no arquivo de configuração de segredos; não foi impresso seu conteúdo. Não houve
tentativa de descobrir credencial em arquivos externos.

### 2.1 Instalações tentadas

Tentativa com `requirements.txt` e nova tentativa com índice público explícito:

```bash
python3 -m venv /tmp/ficdev-validacao-venv
/tmp/ficdev-validacao-venv/bin/python -m pip install \
  --index-url https://pypi.org/simple --disable-pip-version-check \
  --retries 1 --timeout 15 -r requirements.txt
```

Também foi tentada a instalação independente das dependências de teste, para
não deixar o SDK bloquear atividades independentes:

```bash
/tmp/ficdev-validacao-venv/bin/python -m pip install \
  --index-url https://pypi.org/simple --disable-pip-version-check \
  --retries 1 --timeout 15 pytest==9.1.1 python-dotenv==1.2.4 pillow==13.0.0
```

Resultado: falha de conexão/DNS, `Name or service not known`. Nenhuma dependência
requerida foi instalada com sucesso nesta etapa. A mensagem subsequente “No
matching distribution” não comprova que as versões não existam, pois o índice
não foi acessado. Nenhuma versão alternativa foi instalada silenciosamente.
Não foram usados sudo ou instalações globais.

### 2.2 FFmpeg — ação do administrador

Neste sistema, o pacote adequado é `ffmpeg`. Comando para um administrador já
autorizado, em sessão com privilégios:

```bash
apt-get install ffmpeg
```

**Não executado.** Pode exigir atualização dos índices e autorização do
administrador. Depois, verificar como usuário comum:

```bash
ffprobe -version
ffmpeg -version
```

## 3. Modelos, configurações e SDK

- STT: `gemini-3.8-flash`.
- Extração/minuta: `gemini-3.8-flash`.
- TTS: `gemini-3.8-flash-tts`.
- Voz: `Kore`; estilo pt-BR institucional, claro e pausado.
- Timeout local: 30 s; timeout do cliente: 180 s.
- `armazenar_no_provedor=false`; limite compartilhado de entrada: 20 MiB.
- TTS exige WAV novo e não sobrescreve uma emissão anterior.

A documentação pública de [TTS Gemini](https://ai.google.dev/gemini-api/docs/speech-generation)
exige SDK Python >=2.25.0 e descreve texto literal, `speech_metadata.style`,
`speech_config` e WAV. O requisito 2.31.0 satisfaz documentalmente o mínimo.
**Não há confirmação executável da serialização dessa versão nesta máquina:**
o SDK não está instalado. Testes com SDK falso não demonstram aceitação pelo
serviço, suporte de recursos na conta, autenticação, cota ou política do plano.
Os modelos configurados foram mantidos; não houve troca de serviço.

## 4. Entrada original e gabarito

Áudio: `dados/originais/entrada_audio.mp3`.

- Existe, com **2.853.120 bytes**.
- SHA-256: `aa396a4bc0d990ef05b031d8771cbad2d46ebc45ec1ad1adf4d23cb3c7cd2fa6`.
- Idêntico à cópia fornecida em `../arquivos do desafio/arquivos/`.
- Os 5 originais rastreados permanecem idênticos byte a byte ao HEAD.
- Inspeção técnica real foi tentada por `inspecionar_audio()` e interrompida pela
  ausência de ffprobe. Duração real e integridade de decodificação não comprovadas.

`dados/gabaritos/audio-01.json` existe, mas é um modelo não aprovado:
`validado_por_humano=false`; autoria, data, referência e críticos estão vazios.
Não foi preenchido ou inventado conteúdo. É preciso ouvir o original e registrar
referência independente antes da primeira inferência de avaliação. Não reutilizar
a saída do STT como verdade independente nem copiar o texto de outro canal sem
audição. Ruído moderado também precisa de avaliação humana.

## 5. Testes executados

| Grupo/comando | Resultado | Evidência |
|---|---|---|
| `python -m unittest testes.test_audio -v` | **30/30 aprovados** | `unittest_audio.txt` |
| Quatro testes de integração selecionados de `AudioSimuladoTest` | **4/4 aprovados**, repetição de casos já incluídos nos 30 | `unittest_integracao.txt` |
| `.venv/bin/python -m pytest testes/test_audio.py` | Bloqueado antes da coleta: pytest ausente | `pytest_audio.txt` |
| `.venv/bin/python -m pytest testes/test_fluxo_e_revisao.py testes/test_audit_e_main.py` | Bloqueado antes da coleta: pytest ausente | `pytest_integracao.txt` |
| `.venv/bin/python -m pytest` | Bloqueado antes da coleta: pytest ausente | `pytest_completo.txt` |
| AST de todos os `.py` de `src/` e `testes/` | **26 arquivos válidos** | `verificacoes_locais.txt` |
| `git diff --check` | Aprovado, saída 0 | `verificacoes_locais.txt` |
| `from google import genai` | Bloqueado por módulo ausente | `sdk_import.txt` |
| Inspeção real do MP3 | Bloqueada por ffprobe ausente | `verificacoes_locais.txt` |

As evidências estão em `documentacao/evidencias_validacao_audio/`. Os testes
simulam ffprobe, respostas STT e WAV: não são inferências reais. O WAV artificial
valida processamento de bytes; não contém fala institucional produzida pelo modelo.

Comando efetivamente executado para os testes disponíveis, sem alterar o ambiente
preexistente:

```bash
PYTHONPATH=/home/andre/estudos/ficdev2026/.venv/lib/python3.12/site-packages \
  .venv/bin/python -m unittest testes.test_audio -v
```

A repetição de integração usou os seguintes casos:

```bash
PYTHONPATH=/home/andre/estudos/ficdev2026/.venv/lib/python3.12/site-packages \
.venv/bin/python -m unittest \
  testes.test_audio.AudioSimuladoTest.test_pipeline_real_codigo_sdk_simulado \
  testes.test_audio.AudioSimuladoTest.test_pipeline_nao_compara_gabarito_nao_validado \
  testes.test_audio.AudioSimuladoTest.test_rejeitada_nao_sintetiza \
  testes.test_audio.AudioSimuladoTest.test_sintetizador_sem_arquivo_nao_registra_sucesso -v
```

A verificação da integração exercita o código real de extração/minuta, persistência,
comparação e auditoria, com dependências externas simuladas. Confirma que a revisão
ocorre antes da minuta, status pendente/rejeitado e hash alterado bloqueiam síntese,
e ausência de arquivo impede registrar sucesso. Não comprova o comportamento do
modelo, do SDK real ou da qualidade acústica.

## 6. Defeitos corrigidos e pendências

**Nenhuma correção de código nesta etapa:** os testes disponíveis não reproduziram
falha no escopo de áudio. Não se alteraram módulos dos colegas para contornar a
indisponibilidade de ferramentas ou fazer testes passarem.

Continuam pendentes:

1. Instalar as versões declaradas após restabelecer DNS/rede.
2. Executar a suíte original e conferir integração/serialização do SDK real.
3. Disponibilizar ffprobe e medir/validar o MP3 real.
4. Configurar a chave no ambiente ou `.env`, sem versioná-la, e verificar plano/cota.
5. Validar gabarito independente e conferir os dados críticos.
6. Criar uma minuta de execução real e aprová-la antes de emitir áudio.
7. Autorizar consumo de API; depois avaliar STT/TTS reais e ouvir o resultado.

Questões preexistentes dos módulos compartilhados, mantidas sem modificação:
possível dupla contagem de pensamento em `llm_client._tokens()`, ausência de
renormalização de campos após correção humana e diferenças entre taxas/indicadores
RF13. Não houve nova reprodução desses defeitos nesta validação; constam da
auditoria anterior como riscos. Similaridade textual atual não é WER padrão.

## 7. Procedimento exato de demonstração RF06

**Preparação sem inferência**, após resolver as dependências:

```bash
cd '/home/andre/estudos/ficdev2026/Desafio modulo 3/FIC_DEV-IA-Desafio1'
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest
ffprobe -version
python - <<'PY'
from src.config import carregar_config
from src.entradas import validar_arquivo
from src.audio import inspecionar_audio
c = carregar_config()
a = validar_arquivo(c.raiz / c.caso('audio-01')['arquivo'], 'audio', c)
print({'tamanho_bytes': a.tamanho_bytes, 'sha256': a.sha256})
print(inspecionar_audio(a.caminho, c))
PY
```

Ouvir o original; preencher o gabarito com referência, autoria/data e valores
críticos literais; só então marcar `validado_por_humano=true`. Configurar a chave
por meio seguro no ambiente ou `.env`, conforme `.env.example`, sem imprimi-la.

**Somente depois de autorização explícita de inferência/custos:**

```bash
python -m src.main processar audio-01
```

Esse comando pode fazer **três chamadas**: transcrição, extração e minuta. No
terminal, conferir protocolo, data e solicitante contra o original antes da minuta.
Guardar o ID exibido e conferir em `dados/processados/audio-01/<id>/`:

- `texto_bruto.txt`, sem edição;
- `texto_revisado.txt`, revisão de apresentação;
- `extracao_texto.json`, idioma/modelo/duração local/tempo da requisição;
- `comparacao_gabarito.json`, somente se a referência estiver validada;
- `extracao.json`, campos e correções humanas;
- eventos de execução em `resultados/logs/execucoes.jsonl`.

Registrar erros de nomes, datas e protocolos e sua gravidade. Similaridade alta
não autoriza pular conferência. Nenhuma dessas chamadas foi executada agora.

## 8. Procedimento exato de demonstração RF07

Antes da aprovação, conferir o conteúdo e a preparação determinística de locução.
Se houver “não localizado”, o aviso precisa fazer parte do texto aprovado:

> Os campos identificados como não localizado representam informações ausentes no documento.

Não incluir o aviso depois da aprovação. Se a minuta já tiver sido aprovada sem
aviso, usar outra execução revisada; não editar metadados para contornar o hash.
Minutas com HTML/tabelas/código precisam de texto simples previamente aprovado.

A partir do mesmo ambiente virtual, usar o ID real obtido na demonstração RF06:

```bash
read -r -p 'ID da execução real: ' id_execucao
python - "$id_execucao" <<'PY'
import sys
from src.config import carregar_config
from src.revisao import ler_metadados
from src.audio import preparar_locucao
c = carregar_config()
m = ler_metadados(c, sys.argv[1])
texto = (c.raiz / m['arquivo_minuta']).read_text(encoding='utf-8')
print(preparar_locucao(texto))
PY
python -m src.main revisar "$id_execucao"
```

A revisão exige decisão, justificativa e revisor fictício. Este passo é humano;
não automatizar aprovação para produzir evidência. A verificação seguinte não
chama API:

```bash
python - "$id_execucao" <<'PY'
import sys
from src.config import carregar_config
from src.revisao import ler_metadados, STATUS_APROVADOS, hash_arquivo
c = carregar_config()
m = ler_metadados(c, sys.argv[1])
assert m['status'] in STATUS_APROVADOS, 'Minuta não aprovada'
assert hash_arquivo(c.raiz / m['arquivo_minuta']) == m['revisao']['sha256_minuta'], 'Minuta alterada'
print('Status aprovado e hash compatível')
PY
```

**Somente com autorização de inferência/custos:**

```bash
python -m src.main audio-minuta "$id_execucao"
```

Validar o arquivo produzido, sem nova chamada:

```bash
python - "$id_execucao" <<'PY'
import sys
from src.config import carregar_config
from src.revisao import ler_metadados
from src.audio import validar_wav
c = carregar_config()
m = ler_metadados(c, sys.argv[1])
print(validar_wav((c.raiz / m['audio']).read_bytes()))
print({'arquivo': m['audio'], 'configuracoes': m['sintese']})
PY
```

Abrir o WAV em reprodutor local e ouvir integralmente, comparando com a locução
conferida: nomes, protocolos, datas, lacunas, avisos, omissões, acréscimos, ritmo
e entonação. Registrar responsável/data, decisão e divergências, sem atribuir voz
a pessoa real. Um WAV válido não comprova fidelidade. Não sobrescrever a primeira
emissão; eventual correção requer nova execução/revisão e preservação do histórico.

## 9. Custos e limites

Tarifas padrão pagas consultadas em 18/10/2026, por milhão de tokens, válidas na
página até 31/12/2026: Gemini 3.8 Flash entrada US$ 0,75 e saída US$ 3,75;
Gemini 3.8 Flash TTS texto de entrada US$ 0,50 e áudio de saída US$ 9,00.
Coincidem com `config.json`. Fonte: [preços oficiais](https://ai.google.dev/gemini-api/docs/pricing).

**Estimativa ilustrativa, não consumo medido:** TTS com 1.000 tokens de texto e
1.500 de áudio custaria US$ 0,014. Para cada chamada Flash, a fórmula configurada
é `(tokens_entrada × 0,75 + tokens_saida × 3,75) / 1.000.000`. Sem duração/consumo
real não há orçamento total confirmado para o caso. Há risco preexistente na
contagem de pensamento do cliente. Não confundir estimativa com fatura.

A camada gratuita depende de disponibilidade/cota da conta; não foi verificada.
Não se garante custo zero. Repetições e chamadas de extração/minuta também contam.
O código limita requisição inline a 20 MB e a entrada local a 20 MiB; a
[documentação de áudio](https://ai.google.dev/gemini-api/docs/audio) confirma o limite
total inline. Estilo de voz não altera o dever de conferir texto e pronúncia.

## 10. Checklist de prontidão

| Condição | Estado |
|---|---|
| Código integrado e contratos preservados | Confirmado localmente, com SDK falso. |
| Testes disponíveis de áudio | 30 aprovados. |
| Suíte completa e versões exatas | Pendente; instalação/coleta bloqueadas. |
| SDK real e serialização | Pendente. |
| ffprobe/FFmpeg | Ausentes. |
| Original preservado | Confirmado por bytes/hash; decodificação pendente. |
| Gabarito independente | Presente só como modelo, não validado. |
| Chave Gemini | Ausente. |
| Conta, modelos habilitados e cota | Não verificados por autenticação. |
| Minuta aprovada e inalterada | Ainda não existe neste clone. |
| Aviso de lacunas aprovado | Conferir na futura minuta. |
| Autorização para inferência | Não concedida nesta etapa. |
| Conferência auditiva | Pendente após geração real. |

**RF06:** não pronto neste ambiente. O código pode seguir sem gabarito, mas a
comparação/aceite exige referência humana. **RF07:** não pronto neste ambiente;
precisa SDK/chave/conta, autorização e minuta aprovada. ffprobe não é utilizado
na validação WAV de saída, mas é necessário ao fluxo de entrada RF06.

## 11. Estado final do Git e evidências

Branch e HEAD preservados, sem commit, stage ou push. Nenhum arquivo preexistente
alterado nesta etapa; alterações anteriores permanecem. Foram adicionados este
relatório e `documentacao/evidencias_validacao_audio/` com resultados e bloqueios.

Arquivos de evidência: `unittest_audio.txt`, `unittest_integracao.txt`,
`pytest_audio.txt`, `pytest_integracao.txt`, `pytest_completo.txt`,
`verificacoes_locais.txt`, `sdk_import.txt`, `instalacao_requirements.txt`,
`instalacao_pypi.txt` e `instalacao_testes.txt`. São logs de verificações locais,
não resultados reais de STT/TTS. Segredos não foram exibidos nem copiados.

Não se declara aceite acadêmico integral de RF06/RF07. Próxima ação humana:
restabelecer acesso ao índice de pacotes, disponibilizar FFmpeg com autorização,
configurar chave/cota e validar o gabarito. Só depois autorizar e executar as
inferências e a revisão auditiva conforme os procedimentos acima.
