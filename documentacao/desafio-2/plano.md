# Desafio 2 — base e divisão de tarefas

Entrega: **02/11/2026, 23h59** (ver `enunciado/desafio-2/README.md`). Enunciado por seção em `enunciado/desafio-2/`.

## O que a base já entrega

| Peça | Onde | Situação |
|---|---|---|
| Dependências (Chroma, Streamlit, pypdf, Pydantic) | `requirements.txt` | Pronta |
| Embeddings, perfis de geração (principal `gpt-6.1-terra`, alternativo `gpt-6-luna`), pastas, chunking A e B, limites | `config.json`, `Config.perfil_geracao` | Pronta |
| Embeddings pelo cliente único | `ClienteLLM.gerar_embeddings` | Pronta, com teste |
| Contratos entre as partes | `src/schemas.py` (`ESQUEMA_VERSAO = "2.0"`) | Pronta, com teste |
| Leitura e validação do manifesto do acervo | `ingestion.ler_manifesto` | Pronta, com teste |
| Proporção com numerador e denominador (sem divisão por zero) | `metrics.proporcao` | Pronta, com teste |
| Assistente Streamlit com as quatro telas ligadas às partes | `src/app.py`, `python -m src.main assistente` | Pronta; cada tela avisa a parte que falta |
| Esqueletos de cada parte, com o que se espera na docstring | `nlp.py`, `ingestion.py`, `embeddings.py`, `rag.py`, `fluxo_rag.py`, `guardrails.py`, `sentiment.py`, `metrics.py`, `revisao.registrar_decisao_rag` | Levantam `PendenteDeImplementacao` |
| Modelos de gabarito | `dados/gabaritos/_modelo_*.json` | Prontos |
| Pastas | `dados/acervo/` (manifesto vazio), `dados/avaliacoes/`, `resultados/minutas_rag/`, `resultados/metricas/`, `indice/` (fora do git) | Prontas |

Implementar uma parte é trocar o `raise PendenteDeImplementacao` pelo código, com testes que usem `testes/falsos.py` (nenhum teste chama a API). `testes/test_base_desafio2.py::test_partes_pendentes_avisam_qual_requisito_falta` lista as funções pendentes: tire da lista o que você implementar.

## Divisão (seção 5 do enunciado)

### Estudante 1 — esquemas, NLP, dados fictícios e gabaritos (RF14, RF15)

**Primeiro, porque os outros dependem disso:** os dados da seção 6, com gabarito escrito antes de qualquer chamada ao modelo.

- Acervo: 6 documentos em `dados/acervo/` e no `acervo.json`, com 2 temas e 2 formatos (TXT e PDF textual), cada um com id, título e versão. Um deles altera outro com vigência explícita (`substitui` e `vigencia_inicio`), para a pergunta contraditória; outro traz uma instrução maliciosa (ataque no acervo).
- 6 solicitações em `dados/originais/`: 4 completas, 1 incompleta, 1 ambígua; incluir as saídas já obtidas no áudio e no OCR (`texto_revisado.txt` do `audio-01` e do `imagem-01`). Gabarito: `_modelo_solicitacao_d2.json`.
- 8 perguntas do RAG: 5 respondíveis, 2 sem resposta no acervo, 1 com fontes contraditórias. Gabarito: `_modelo_pergunta_rag.json`, com o trecho literal de referência.
- 12 avaliações em `dados/avaliacoes/avaliacoes.json` (`[{"id", "texto"}]`): 3 positivas, 3 negativas, 3 neutras, 3 ambíguas ou mistas. Gabarito: `_modelo_sentimentos.json`, com a regra de ambiguidade escrita.
- 3 ataques: instrução maliciosa na solicitação, no acervo e tentativa de obter segredo. Gabarito: `_modelo_ataque.json`.

**Depois:** `src/nlp.py` (extração validada com no máximo uma correção, regras de negócio, comparação JSON sintático e esquema, ficha de compreensão) e os prompts versionados em `prompts/`. Testes do enunciado: T01, T02, T03. Métrica: acurácia de categoria com `metrics.proporcao`.

### Estudante 2 — embeddings, índice, RAG e abstração de provedor (RF17, RF18, RF19, RF21)

`ingestion.extrair_texto` e `dividir`, `embeddings.IndiceVetorial` (Chroma persistente, upsert sem duplicar, exclusão por documento), `rag.responder` e `minuta_fundamentada`, e `fluxo_rag.processar_solicitacao` com a auditoria do RF21. Experimento de chunking A contra B com as 5 perguntas respondíveis (RF18). Demonstração da troca para o perfil `alternativo` sem reindexar. Testes: T06, T07, T08, T09, T10, T12, T14.

Até os dados do Estudante 1 chegarem, dá para desenvolver com documentos de teste em `tmp_path`.

### Estudante 3 — guardrails, Streamlit, sentimentos e painel (RF16, RF20, RF22)

`src/guardrails.py` (entrada, trechos e saída; `ControleRecursos` com teto de chamadas e tokens e no máximo uma repetição por falha transitória), `sentiment.classificar`, `metrics.agregar_sentimentos` com o gráfico do painel, `revisao.registrar_decisao_rag` (estados pendente, aprovada, rejeitada, revisar) e o acabamento de `src/app.py`. Testes: T04, T05, T11, T13.

### Todos, no fim (RF23, RF24 e entrega)

- Matriz T01 a T15 (seção 11) com esperado, obtido, evidência e situação; regressão T15, reexecutando o `texto-01` e o `audio-01` ou o `imagem-01` do Desafio 1 até minuta e revisão.
- Demonstração da exclusão de um documento do índice e de uma minuta aprovada e outra rejeitada ou enviada para revisão (RF24).
- Relatório técnico breve, README (indexação e Streamlit) e registro do uso de IA.

## Ordem sugerida

1. **31/10:** Estudante 1 entrega acervo, solicitações, perguntas, avaliações, ataques e gabaritos. Estudantes 2 e 3 implementam com dados de teste.
2. **01/11:** cada parte roda com a API real sobre os dados do Estudante 1; integração pelo Streamlit.
3. **02/11:** matriz RF23, regressão, documentação, ensaio da apresentação e entrega (`git archive`, ver `AGENTS.md`).

## Regras de trabalho

- Uma branch por estudante e pull request para a `main`. `src/schemas.py`, `config.json` e as assinaturas dos esqueletos são o contrato: mudança combinada no grupo e no mesmo commit que ajusta quem usa.
- Gabarito antes da chamada ao modelo (seção 11); resultado baixo é relatado, nunca ajustado (seção 15).
- Só dados fictícios; nada de chave fora do `.env`; o índice (`indice/`) fica fora do git e se recria pelo assistente.

## Decisões em aberto do grupo

- **Acervo:** os editais em `enunciado/desafio-2/arquivos/` são documentos públicos reais, e a seção 16 pede documentos criados para o exercício. Usá-los como acervo (com um segundo tema em TXT escrito pelo grupo) ou escrever um acervo fictício inspirado neles? Vale confirmar com o professor.
- **Categorias:** o RF15 pede "outros" ou "revisão" entre as categorias; hoje `config.json` tem as cinco do Desafio 1, e a extração usa "não localizado" fora delas.
