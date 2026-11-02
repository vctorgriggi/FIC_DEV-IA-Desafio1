# Central Inteligente de Atendimento — Desafio 1

Protótipo local (FIC_DEV, IA Generativa) que recebe solicitações fictícias em
texto, áudio e imagem e gera minutas para revisão humana. Enunciados em
`enunciado/desafio-1/` e `enunciado/desafio-2/`; instalação, comandos, modelos
e limitações no `README.md`.

## Como rodar

```bash
source .venv/bin/activate      # Python >= 3.11 (Pillow 13); o 3.9 do macOS não instala
python -m pytest               # não chama a API
python -m src.main verificar   # versões, chave e arquivos dos casos
python -m src.main interface   # interface local em http://127.0.0.1:8000
python -m src.main assistente  # assistente do Desafio 2 (Streamlit) em http://127.0.0.1:8501
```

Não há lint nem typecheck configurados.

## Regra de ouro

**Nenhuma resposta sai sem decisão humana registrada.** O código não tem e não
ganha função de envio; a minuta termina em `revisao.py`, e o áudio só sai de
minuta aprovada e inalterada (enunciado, seções 3 e 13).

## Estrutura

```
src/              # base compartilhada + uma parte por modalidade (tabela no README)
prompts/          # <nome>_v<N>.md; prompt alterado é versão nova, nunca edição
dados/originais/  # entradas do desafio; nunca alterar (o hash vai para o log)
dados/gabaritos/  # resultado esperado, escrito antes de executar o caso
dados/acervo/     # acervo fictício do Desafio 2; acervo.json é o manifesto (id, título, versão)
indice/           # índice Chroma, fora do git; recria-se a partir do acervo
interface/        # front-end Vite/React; dist/ é versionado e servido por src/web.py
```

Desafio 2 em andamento: base, contratos e divisão por estudante em
`documentacao/desafio-2/plano.md`.

## Nunca fazer

- Nunca chamar o SDK da OpenAI fora de `src/llm_client.py` — ali ficam
  timeout, `store=False`, tradução de erros, tokens e custo; chamada direta
  escapa do RF04 e do RF11.
- Nunca usar dado pessoal real, nem em teste — enunciado, RF12 e seção 13.
- Nunca pôr chave em código, `config.json`, log ou commit — só no `.env`.
- Nunca zipar a pasta para a entrega — leva `.env` e `.venv`; use
  `git archive --format=zip -o entrega.zip HEAD`.

## Convenções

- Contrato entre modalidades: `TextoExtraido` (`tipos.py`) e o esquema de
  `extracao.py`. Mudança só com acordo do grupo, e no mesmo commit que ajusta
  `normalizar_extracao` e os testes — três partes dependem dele.
- Contrato do Desafio 2: `src/schemas.py` (`ESQUEMA_VERSAO`) e as
  assinaturas dos esqueletos. Mudança combinada no grupo, versão nova do
  esquema e, no mesmo commit, quem produz e quem consome o tipo.
- Erros: falha do provedor vira subclasse de `ErroLLM`; `main.py` traduz em
  mensagem e código de saída. Parte não implementada levanta
  `PendenteDeImplementacao`.
- Testes: `testes/falsos.py` imita o SDK; nenhum teste chama a API.
- Log (`audit.py`): guarda referências (caminho, versão e hash do prompt),
  não conteúdo. Texto enviado ao provedor passa antes por
  `privacidade.mascarar`.
- Saídas geradas (`resultados/`, `dados/processados/`) ficam fora do git; a
  rodada final da entrega entra num commit próprio com `git add -f`.
- Uso de IA: declarado de forma resumida em `documentacao/uso_de_ia.md`,
  escrito pelo grupo. Commits não levam trailer de coautoria de IA.
- Interface: só chama funções de fluxo.py e revisao.py; regra de negócio não
  mora no front-end. Mudou interface/src → `npm run build` e commite dist/.
  O Streamlit do Desafio 2 (`src/app.py`) segue a mesma regra com
  `fluxo_rag.py`, as partes e `revisao.py`.
- Identificadores e mensagens em português.

## Gotchas

- Agente escreve `client.chat.completions.create` → o projeto usa a Responses
  API (`client.responses.create`); texto, transcrição, voz e imagem têm cada
  um seu método em `ClienteLLM`.
- Agente liga repetições do SDK → o cliente usa `max_retries=0` e prazo de
  relógio: repetir um 429 de cota esgotada só atrasa a mesma recusa. A única
  repetição (5xx e conexão, RF16) fica em `ClienteLLM._executar`.
- RF07 depois de 06/01/2027 → todos os modelos da Speech API desligam nessa
  data; o substituto indicado só roda pela Realtime API. Trocar de modelo
  dentro da Speech API não resolve.
- Agente indexa os editais de `enunciado/desafio-2/arquivos/` → são documentos
  públicos reais, e a seção 16 pede acervo criado para o exercício. Eles ficam
  fora de `dados/acervo/`.
- `categorias` do `config.json` inclui `revisao` (RF15, intenção ambígua) e é a
  mesma lista do enum de `extracao.esquema_extracao` → a regressão do Desafio 1
  (T15) também pode devolver `revisao`, que os gabaritos do Desafio 1 não preveem.
