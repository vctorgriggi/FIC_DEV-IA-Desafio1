# Desafio 2 — base e divisão de tarefas

As três partes estão implementadas e integradas. Este documento preserva a
divisão original de trabalho; o estado da entrega, as evidências e as decisões
estão em [integração](integracao.md).

Entrega: **02/11/2026, 23h59** (ver `enunciado/desafio-2/README.md`). Enunciado por seção em `enunciado/desafio-2/`.

## O que a base já entrega

| Peça | Onde | Situação |
|---|---|---|
| Dependências (Chroma, Streamlit, pypdf, Pydantic) | `requirements.txt` | Pronta |
| Embeddings, perfis de geração (principal `gpt-6.1-terra`, alternativo `gpt-6-luna`), pastas, chunking A e B, limites | `config.json`, `Config.perfil_geracao` | Pronta |
| Embeddings pelo cliente único | `ClienteLLM.gerar_embeddings` | Pronta, com teste |
| Repetição única em falha transitória (5xx, conexão) e gancho de limites | `ClienteLLM(controle=...)` | Pronta, com teste; o controle em si é do Estudante 3 |
| Contratos entre as partes, com esquema estrito para o modelo | `src/schemas.py` (`ESQUEMA_VERSAO = "2.0"`), `llm_client.formato_json` | Pronta, com teste |
| Registro da minuta do assistente (pendente, aprovada, rejeitada, revisar, bloqueada) | `schemas.RegistroMinutaRAG`, `revisao.ler_registro_rag` e `gravar_registro_rag` | Pronta, com teste |
| Saída das partes com respostas e prompt para a auditoria | `tipos.Resultado` | Pronta |
| Exemplos válidos de cada contrato, para testar uma parte sem esperar as outras | `testes/exemplos.py` | Prontos |
| Leitura validada das avaliações | `sentiment.ler_avaliacoes` | Pronta, com teste |
| Leitura e validação do manifesto do acervo (inclusive `substitui`) | `ingestion.ler_manifesto` | Pronta, com teste |
| Proporção com numerador e denominador (sem divisão por zero) | `metrics.proporcao` | Pronta, com teste |
| Assistente Streamlit com as quatro telas ligadas às partes | `src/app.py`, `python -m src.main assistente` | Pronta; cada tela avisa a parte que falta |
| Esqueletos de cada parte, com o que se espera na docstring | `nlp.py`, `ingestion.py`, `embeddings.py`, `rag.py`, `fluxo_rag.py`, `guardrails.py`, `sentiment.py`, `metrics.py` (uma função reservada por parte), `revisao.registrar_decisao_rag` | Levantam `PendenteDeImplementacao` |
| Modelos de gabarito | `dados/gabaritos/_modelo_*.json` | Prontos |
| Pastas | `dados/acervo/` (manifesto vazio), `dados/avaliacoes/`, `resultados/minutas_rag/`, `resultados/metricas/`, `indice/` (fora do git) | Prontas |

Implementar uma parte é trocar o `raise PendenteDeImplementacao` pelo código, com testes que usem `testes/falsos.py` e `testes/exemplos.py` (nenhum teste chama a API). Cada estudante tem o seu arquivo de pendências: `testes/test_d2_nlp.py`, `test_d2_indice_rag.py` e `test_d2_guardrails_sentimentos.py`. Ao implementar uma função, apague a linha dela ali.

Como as partes se encaixam:

- Toda função que gera texto recebe `perfil` (de `config.perfil_geracao`) e devolve `tipos.Resultado` com o valor, as respostas do provedor e o prompt; é daí que o fluxo tira tokens, custo, latência e versão do prompt para a auditoria (RF21).
- O esquema de saída pedido ao modelo sai do próprio modelo Pydantic: `formato_json(SolicitacaoEstruturada.model_json_schema(), "solicitacao")`. A validação usa `model_validate_json`, que não converte `"true"` em booleano (RF14).
- Categoria e entidades vêm só da `SolicitacaoEstruturada`; a `FichaCompreensao` acrescenta resumo e inferências.
- O fluxo do Estudante 2 grava um `RegistroMinutaRAG`; a revisão do Estudante 3 lê e atualiza esse mesmo registro. Cada um testa com `exemplos.registro(...)` sem esperar o outro.

## Divisão (seção 5 do enunciado)

### Estudante 1 — esquemas, NLP, dados fictícios e gabaritos (RF14, RF15)

**Primeiro, porque os outros dependem disso:** os dados da seção 6, com gabarito escrito antes de qualquer chamada ao modelo.

- Acervo: 6 documentos em `dados/acervo/` e no `acervo.json`, com 2 temas e 2 formatos (TXT e PDF textual), cada um com id, título e versão. Um deles altera outro com vigência explícita (`substitui` e `vigencia_inicio`), para a pergunta contraditória; outro traz uma instrução maliciosa (ataque no acervo).
- 6 solicitações em `dados/originais/`: 4 completas, 1 incompleta, 1 ambígua; incluir as saídas já obtidas no áudio e no OCR (`texto_revisado.txt` do `audio-01` e do `imagem-01`). Gabarito: `_modelo_solicitacao_d2.json`.
- 8 perguntas do RAG: 5 respondíveis, 2 sem resposta no acervo, 1 com fontes contraditórias. Gabarito: `_modelo_pergunta_rag.json`, com o trecho literal de referência.
- 12 avaliações em `dados/avaliacoes/avaliacoes.json` (`[{"id", "texto"}]`): 3 positivas, 3 negativas, 3 neutras, 3 ambíguas ou mistas. Gabarito: `_modelo_sentimentos.json`, com a regra de ambiguidade escrita.
- 3 ataques: instrução maliciosa na solicitação, no acervo e tentativa de obter segredo. Gabarito: `_modelo_ataque.json`.

**Depois:** `src/nlp.py` (extração validada com no máximo uma correção, regras de negócio, comparação JSON sintático e esquema, ficha de compreensão), `metrics.acuracia_categorias` e os prompts versionados em `prompts/`. Testes do enunciado: T01, T02, T03. Métrica: acurácia de categoria com `metrics.proporcao`.

### Estudante 2 — embeddings, índice, RAG e abstração de provedor (RF17, RF18, RF19, RF21)

`ingestion.extrair_texto`, `dividir`, `incluir_documento` e `excluir_documento`, `embeddings.IndiceVetorial` (Chroma persistente, upsert sem duplicar, trechos antigos apagados quando o arquivo muda, exclusão em todas as coleções), `metrics.acerto_recuperacao`, `rag.responder` e `minuta_fundamentada`, e `fluxo_rag.processar_solicitacao` com a auditoria do RF21. Experimento de chunking A contra B com as 5 perguntas respondíveis (RF18). Demonstração da troca para o perfil `alternativo` sem reindexar. Testes: T06, T07, T08, T09, T10, T12, T14.

Até os dados do Estudante 1 chegarem, dá para desenvolver com documentos de teste em `tmp_path`.

### Estudante 3 — guardrails, Streamlit, sentimentos e painel (RF16, RF20, RF22)

`src/guardrails.py` (entrada, arquivo, trechos e saída; `ControleRecursos` com `antes_da_chamada` e `registrar`, para o teto de chamadas e tokens; a repetição única já está no cliente), `sentiment.classificar`, `metrics.agregar_sentimentos` com o gráfico do painel, `revisao.registrar_decisao_rag` (estados pendente, aprovada, rejeitada, revisar) e o acabamento de `src/app.py`. Testes: T04, T05, T11, T13.

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

## Decisões do grupo

- Acervo fictício, escrito para o exercício; os editais reais de
  `enunciado/desafio-2/arquivos/` não são indexados (seção 16).
- Categoria `revisao` em `config.json` para intenção ambígua (RF15).
- Chunking A 250/50 e B 500/100 caracteres; B ativo (justificativa em
  `integrante-2.md`).
