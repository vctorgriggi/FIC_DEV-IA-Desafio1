# Central Inteligente de Atendimento — Desafio 1

Protótipo local (FIC_DEV, IA Generativa) que recebe solicitações fictícias em
texto, áudio e imagem e gera minutas para revisão humana. Enunciado em
`enunciado/`; instalação, comandos, modelos e limitações no `README.md`.

## Como rodar

```bash
source .venv/bin/activate      # Python >= 3.10; o 3.9 do macOS não instala o SDK
python -m pytest               # não chama a API
python -m src.main verificar   # versões, chave e arquivos dos casos
python -m src.main interface   # interface local em http://127.0.0.1:8000
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
interface/        # front-end Vite/React; dist/ é versionado e servido por src/web.py
```

## Nunca fazer

- Nunca chamar o SDK do Gemini fora de `src/llm_client.py` — ali ficam
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
- Identificadores e mensagens em português.

## Gotchas

- Agente escreve `client.models.generate_content` → a doc atual do Gemini usa
  `client.interactions.create`; siga o formato das docstrings de `audio.py`,
  `vision.py` e `image_generation.py`.
- CLI parada por minutos após um 429 → o SDK repete esperando o `Retry-After`
  sem teto, e `attempts=0` vira 1; `llm_client.py` só deixa repetir 5xx e
  aplica prazo de relógio. Não troque isso por ajuste de `attempts`.
- Atualizou o `google-genai` → rode os testes: as exceções da Interactions API
  vêm de um módulo privado do SDK, e `testes/test_llm_client.py` quebra se ele mudar.

## Decisões em aberto

Nenhuma pendente.
