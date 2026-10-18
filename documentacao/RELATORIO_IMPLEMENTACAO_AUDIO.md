# Relatório de implementação — áudio RF06/RF07

Data: 18/10/2026. Projeto FIC_DEV, Desafio Prático 1, Módulo 3.
Base: `bf91e841c982a95cafd14afd398e2d58a2ac8731`.
Branch local: `feat/audio-rf06-rf07`.

**Situação:** implementação técnica integrada e 30 testes simulados aprovados.
**RF06 e RF07 não têm aceite acadêmico integral comprovado.** Faltam ambiente
fixado/SDK executável, ffprobe real, referência humana, inferências autorizadas
e revisão auditiva. Não houve consumo de API, commit, push ou merge.

> Registro histórico da implementação inicial. Para o estado de versionamento,
> consulte `RELATORIO_VALIDACAO_AUDIO.md`: suíte completa com 110 testes e 26
> subtestes aprovados; inferências e homologação humana continuam pendentes.

## A. Resumo do que foi implementado

- RF06: revalidação de entrada/hash, inspeção estrutural com ffprobe e duração,
  transcrição via cliente central, esquema validado, bruto preservado, revisão
  determinística e trechos incertos. Tempos da mídia e da requisição separados.
- RF07: TTS por modelo/voz/estilo configurados, preparação conservadora, bloqueio
  de lacunas sem aviso previamente aprovado, validação WAV e gravação exclusiva.
- Integração: aprovação/hash existentes preservados; telemetria de síntese em
  auditoria/metadados; comparação somente com referência de áudio validada.
- Modelo de gabarito explicitamente não validado e documentação de reprodução.
- Testes sem rede e sem inferência, incluindo pipeline com código real de
  extração/minuta e respostas de SDK simuladas.

## B. Arquivos criados e modificados

| Arquivo | Ação e motivo |
|---|---|
| `src/audio.py` | Substitui funções pendentes; auxiliares locais, STT, TTS, validação e locução. |
| `src/fluxo.py` | Gating de referência humana; validação do WAV e telemetria TTS. |
| `config.json` | Adiciona somente seção `audio`: timeout local, voz e estilo. |
| `prompts/transcricao_v1.md` | Novo prompt de transcrição fiel/segura. |
| `dados/gabaritos/audio-01.json` | Modelo vazio, `validado_por_humano=false`. |
| `testes/test_audio.py` | 30 testes unittest, compatíveis também com coleta pytest. |
| `testes/test_fluxo_e_revisao.py` | Atualiza etapas e falso WAV; pendência genérica agora é injetada explicitamente. |
| `testes/test_audit_e_main.py` | Teste de código de pendência usa erro simulado, sem pressupor RF06 ausente. |
| `README.md` | Estado atual e instruções de áudio; remove descrição obsoleta de texto pendente. |
| `documentacao/audio_e_acessibilidade.md` | Arquitetura, formatos, erros, configuração, regras e limites. |
| `documentacao/uso_de_ia.md` | Complemento Codex, preservando integralmente o registro anterior. |
| `documentacao/evidencias_audio_unittest.txt` | Saída real da execução de testes simulados. |
| `documentacao/RELATORIO_IMPLEMENTACAO_AUDIO.md` | Este relatório. |

O ambiente `.venv/` foi criado localmente e é ignorado pelo Git. Não houve
alteração de `requirements.txt`, tipos, categorias, prompts preexistentes,
originais, cliente, revisão, módulos de OCR/imagem ou geração de texto.

## C. Descrição técnica de RF06

Assinatura preservada: `transcrever(arquivo, *, cliente, config) -> TextoExtraido`.

1. Reutiliza `validar_arquivo()` e compara modalidade/hash com a entrada recebida.
2. Executa ffprobe com timeout, sem shell, `-count_frames` e saída JSON.
3. Exige áudio com frames positivos, duração finita positiva e contêiner compatível;
   erro no stderr, falha de processo, ferramenta ausente ou saída inválida reprova.
4. Confere novamente o hash dos bytes após a inspeção.
5. Aplica limite da requisição inline serializada, com reserva para envelope.
6. Usa `ClienteLLM.gerar()` com `config.modelo('transcricao')`, prompt de tarefa
   versionado, sistema seguro e esquema JSON.
7. Valida os tipos de bruto/idioma/incertos e rejeita ausência de fala ou formato.
8. Mantém o bruto literalmente dentro do JSON; revisa apenas espaços/quebras,
   sem substituir palavra, data ou protocolo por inferência.
9. Retorna metadados de idioma, modelo, duração medida, método, formato/codecs,
   duração da chamada, hash original e referência/hash do sistema seguro.

A entrada de mídia é separada das instruções. O prompt declara todo áudio externo
como não confiável; instruções faladas são conteúdo, e inaudíveis não são inventados.
Isso mitiga, mas não prova imunidade a prompt injection ou alucinação.

A comparação existente é reutilizada. Para áudio, a referência deve declarar
validação humana verdadeira e ter texto, autoria/data não vazios e lista textual
de críticos. Um modelo não validado registra comparação pendente, sem impedir
as outras etapas nem gerar métrica fictícia. Similaridade não é WER padrão.

## D. Descrição técnica de RF07

Assinatura preservada: `sintetizar(texto_aprovado, destino, *, cliente, config) -> dict`.

O ponto oficial é `fluxo.sintetizar_minuta()`: conserva status aprovado/aprovado
com correção e SHA-256 da revisão. A primitiva não possui contexto de aprovação
nem deve ser chamada diretamente como produção oficial.

Preparação `markdown_conservador_v1` remove marcadores simples de apresentação,
conserva conteúdo e destinos de referências e não reescreve fatos. HTML/comandos
vocais, tabelas, cercas de código e escapes bloqueiam a síntese para revisão.
Não é parser geral de Markdown. Um teste detectou e corrigiu remoção indevida
de underscores em caminhos; a regressão está coberta.

Se houver “não localizado”, a minuta já aprovada deve conter o aviso definido
em `audio.AVISO_LACUNAS`. O módulo não acrescenta esse aviso; sem ele, bloqueia
antes da chamada. Se a revisão já foi encerrada, produza outra execução revisada
em vez de editar metadados para contornar o hash.

TTS recebe texto literal em conteúdo `user_input`, estilo em anotação
`speech_metadata` e voz em `generation_config.speech_config`. Usa o modelo TTS
configurado e o cliente central. WAV base64 é decodificado com validação e
inspecionado com `wave`: RIFF/WAVE PCM, comprimento consistente e frames completos.
Só então grava com modo exclusivo, sem sobrescrever evidência anterior.

O fluxo também confirma arquivo presente/válido antes do sucesso. Guarda modelo,
voz, estilo, formato, hashes, preparação, duração do áudio/requisição, tokens e
custo disponível. Validação estrutural não comprova que a fala é fiel ou agradável;
a audição é pendência obrigatória.

## E. Contratos e integrações

Preservados `ArquivoEntrada`, `TextoExtraido`, assinaturas públicas, categorias,
campos estruturados e diretórios. Áudio revisado alimenta extração/minuta dos
colegas; não existe segunda implementação dessas tarefas.

A confirmação humana de protocolo/data/solicitante continua antes da minuta.
A comparação de áudio não validado agora deixa aviso explícito na auditoria.
A parte de imagem continua com seu fluxo anterior de gabarito.

Resultados em `dados/processados/<caso>/<id>/`; minutas e metadados em
`resultados/minutas/`; WAV em `resultados/audios/`; eventos em
`resultados/logs/execucoes.jsonl`. Configurações de voz ficam também no campo
`sintese` dos metadados. Não há envio automático ao cidadão.

## F. Modelos e bibliotecas

- STT: `gemini-3.8-flash`; TTS: `gemini-3.8-flash-tts`, conforme config existente.
- Voz padrão `Kore`, configurável; estilo pt-BR institucional separado do conteúdo.
- SDK requerido pelo projeto: `google-genai==2.31.0`, sem alteração.
- Demais versões declaradas: dotenv 1.2.4, pytest 9.1.1, Pillow 13.0.0.
- Biblioteca padrão: subprocess, wave, base64, hashlib, JSON, unittest/mock.
- ffprobe da Aula 05 para inspeção/duração; não instalado nesta etapa.

A documentação oficial TTS consultada exige SDK Python >=2.25.0 e mostra o formato
utilizado. Isso é respaldo documental; **não foi possível validar a serialização
no SDK 2.31.0 instalado**, pois o download ficou bloqueado por DNS. Não se afirma
que clientes falsos comprovem aceitação pelo endpoint/conta. Nenhuma troca de
provedor ou biblioteca externa adicional foi feita.

Referências: [áudio](https://ai.google.dev/gemini-api/docs/audio) e
[TTS](https://ai.google.dev/gemini-api/docs/speech-generation), consultadas em
18/10/2026. Relação com aulas detalhada em `audio_e_acessibilidade.md`.

## G. Testes executados e resultados reais

| Grupo/verificação | Resultado nesta etapa |
|---|---|
| Novos testes RF06/RF07 | **30 aprovados**, execução real de unittest, SDK e ffprobe simulados. |
| Integração áudio → extração → confirmação → minuta → revisão → WAV | Aprovada dentro dos 30 testes; código real, respostas externas falsas. |
| Suíte original pytest | **Bloqueada**: `No module named pytest`. Não declarada aprovada. |
| Instalação das versões fixadas em `.venv` | **Bloqueada**: falha DNS ao acessar índice; nenhuma instalação global. |
| SDK 2.31.0/serialização executável | **Bloqueada** pela instalação; compatibilidade somente documental nesta sessão. |
| ffprobe no original/áudio corrompido real | **Bloqueado**: ferramenta ausente no PATH. |
| Sintaxe AST de `src/` e `testes/` | **26 arquivos válidos**, módulos não executados por esta checagem. |
| `git diff --check` | Aprovado. |
| Originais do repositório | **5 arquivos idênticos byte a byte ao HEAD**. |
| Inferência/audição reais | Não realizadas, sem autorização de consumo e sem validação humana. |

Ambiente dos testes disponíveis: Python 3.12.3, ambiente `.venv` local com acesso
somente de leitura aos pacotes do sistema, Pillow 10.2.0 e dotenv 1.2.4 reutilizado
via PYTHONPATH do ambiente acadêmico existente. **Não é o ambiente fixado completo**:
Pillow difere de requirements e pytest/SDK faltam. Nenhum pacote do sistema foi
alterado. Essa alternativa serviu para testes sem inferência, não comprova
reprodutibilidade das versões declaradas. unittest faz parte do Python.

Comando efetivamente executado, a partir da raiz do repositório:

```bash
PYTHONPATH=/home/andre/estudos/ficdev2026/.venv/lib/python3.12/site-packages \
  .venv/bin/python -m unittest testes.test_audio -v
```

Saída integral da rodada final: `documentacao/evidencias_audio_unittest.txt`.
Resultado: `Ran 30 tests` / `OK`. A evidência é de teste simulado, não de STT/TTS real.

Cobertura funcional inclui extensão/vazio/tamanho/hash, ffprobe ausente/falha/
timeout/corrupção/duração, limite inline, JSON inválido/vazio, bruto/revisado,
incertezas e críticos, referência validada/não validada, voz configurável,
preparação Markdown, lacunas, WAV inválido/truncado/sem frames, falha do provedor,
aprovação pendente/rejeitada/alterada, telemetria, erro auditado e ausência de
arquivo impedindo sucesso. Não é relatório quantitativo de cobertura de linhas.

## H. Recursos que funcionam com mocks

Inspeção de áudio, construção de requisições pelo cliente central, validação da
resposta STT, persistência/comparação, integração com texto, bloqueios de revisão,
TTS com WAV de teste e auditoria foram exercitados com dependências externas
simuladas. O WAV de teste contém frames artificiais, não fala gerada por IA.

## I. Recursos comprovados por chamadas reais

**Nenhum.** Não houve inferência nem cobrança. Os artefatos de execução dos testes
ficam em diretórios temporários e não foram apresentados como saídas do desafio.
Consulta pública de documentação não é execução da API de modelos.

## J. Bloqueios e atividades humanas

1. Disponibilizar rede para instalar as versões de `requirements.txt` em venv.
2. Executar a suíte completa e validar a interface real do SDK fixado.
3. Disponibilizar FFmpeg/ffprobe no PATH, sem instalação automática privilegiada.
4. Ouvir o original; preencher e validar gabarito humano antes da inferência.
5. Autorizar cota/custo para chamadas reais e registrar consumo real retornado.
6. Processar áudio, conferir nomes/datas/protocolos e avaliar ruído moderado.
7. Aprovar minuta, incluindo aviso de lacunas quando necessário, antes do TTS.
8. Ouvir WAV e conferir texto, pronúncia, omissões/acréscimos e acessibilidade.
9. Preservar artefatos reais e suas decisões/limitações para entrega acadêmica.

## K. Requisitos e critérios de aceite ainda pendentes

**RF06:** falta processamento real do original com duração medida, comparação
contra referência humana, análise dos erros e comprovação de conferência crítica.
Testes simulados não satisfazem esses critérios de demonstração.

**RF07:** falta fala real da minuta aprovada, audição e comprovação de
correspondência sem acréscimos relevantes. O bloqueio por lacunas pode exigir
nova geração/revisão do documento atual; não altera prompts dos colegas.

**Compartilhados:** avaliação RF13, matriz RF12 e demais problemas apontados no
relatório de análise permanecem sob responsabilidade conjunta. Não foram
corrigidos silenciosamente no escopo de áudio. A possível dupla contagem de
pensamento no cliente e a normalização dos campos pós-correção permanecem
limitações preexistentes a comunicar à equipe.

## L. Comandos para reproduzir

Em ambiente com rede, usando somente o venv do projeto:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
ffprobe -version
python -m unittest testes.test_audio -v
python -m pytest
```

O comando de teste não requer chave. Para a aplicação, configure `.env` conforme
`.env.example`. Depois de autorizar cota/custos e validar gabarito:

```bash
python -m src.main processar audio-01
python -m src.main revisar <id_execucao>
python -m src.main audio-minuta <id_execucao>
python -m src.main avaliacao
```

Os comandos da aplicação gravam artefatos. `processar`/`audio-minuta` chamam API.
Não os execute automaticamente para tentar resolver o bloqueio desta etapa.

## M. Evidências disponíveis

- Código e prompt versionado; gabarito vazio explicitamente pendente.
- `testes/test_audio.py`: testes simulados reproduzíveis.
- `documentacao/evidencias_audio_unittest.txt`: saída da execução real dos testes.
- Documentação de áudio e instruções no README.
- Diff local e branch de implementação. Nenhuma saída real de inferência foi criada.
- Comparação byte a byte dos originais e checagem de sintaxe/diff realizadas.

Logs temporários da tentativa de pytest podem não sobreviver ao ambiente; a falha
foi `No module named pytest`. A tentativa pip reportou DNS indisponível, não uma
conclusão de que as versões não existem no índice.

## N. Resumo do estado final do Git

Início: `main`, árvore limpa, HEAD `bf91e841c982a95cafd14afd398e2d58a2ac8731`.
Foi criada a branch local `feat/audio-rf06-rf07`. HEAD permanece nesse commit;
nenhum commit, stage, push, merge ou modificação remota foi feito.

Alterações locais intencionais: 7 arquivos rastreados modificados e 6 arquivos
novos, listados em B (incluindo este relatório). `.venv/` e caches ficam ignorados.
Todos os originais e módulos de texto/OCR/imagem permanecem inalterados. A alteração
de fluxo é limitada a comparação de áudio e rastreabilidade/validação TTS.

**Próxima atividade:** preparar o ambiente fixado e executar a suíte original;
em paralelo, preencher a referência humana. Só depois realizar inferência real
com autorização e concluir a avaliação auditiva. A implementação técnica não é
declaração de aceite acadêmico integral.
