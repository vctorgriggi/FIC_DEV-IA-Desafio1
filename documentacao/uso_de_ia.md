# Uso de IA no desenvolvimento

Documento exigido pela Seção 10 do enunciado para assegurar transparência, rastreabilidade e governança no uso de assistentes de codificação.

## 1. Ferramentas, Modelos e Versões Utilizados

- **Assistente de Codificação:** Google Antigravity IDE (Agentic AI Assistant).
- **Modelo de Linguagem do Assistente:** Gemini 3.8 Flash (High).
- **Modelo de IA Generativa da Solução:** `gemini-3.8-flash` via SDK `google-genai` (versão 2.31.0) usando a Interactions API.
- **Ambiente de Execução:** Python 3.12.9 (Windows x64), pytest 9.1.1, python-dotenv 1.2.4.

## 2. Solicitações Relevantes Feitas à IA

1. **Solicitação 1 — Mapeamento de Requisitos e Responsabilidades:**
   - *Comando:* Análise integral do documento `Desafio_01-Pratico_IA_Generativa_Aulas_01_a_07.docx.pdf` e identificação do que é necessário para o papel de "gerenciamento e manipulação de textos com IA".
   - *Resultado:* Mapeamento preciso dos requisitos RF02 (Experimento de prompts), RF03 (Prompt seguro e injeção), RF05 (Extração JSON estruturada), RF09 (Minuta institucional) e RF12 (LGPD/minimização).

2. **Solicitação 2 — Implementação da Extração Estruturada e Minuta:**
   - *Comando:* Implementação de `src/extracao.py` e `src/minuta.py` integrando chamadas ao Gemini com *Structured Outputs* e esquema JSON validado com categorias documentadas.
   - *Resultado:* Criação das funções `extrair_campos` e `gerar_minuta`, além de criação dos prompts versionados em `prompts/`.

3. **Solicitação 3 — Criação do Caso de Teste de Prompt Injection e Experimento de Prompts:**
   - *Comando:* Elaboração de uma entrada adversarial contendo tentativa de evasão de tag `</conteudo_externo>` e pedidos de concessão indevida de valores, e execução do experimento controlado comparando Prompts A, B e C.
   - *Resultado:* Criação de `dados/originais/entrada_texto_injection.txt`, `dados/gabaritos/texto-injection.json` e relatório comparativo com dados empíricos em `documentacao/experimento_prompts.md`.

## 3. Sugestões Aceitas, Modificadas e Rejeitadas

- **Aceita:** Utilização de `response_format` com esquema JSON rigoroso no SDK `google-genai` para forçar o Gemini a responder apenas dados tipados com enum de categorias e valor `"não localizado"`.
- **Aceita:** Criação de caso de teste com Prompt Injection e fechamento simulado de tags XML para demonstrar empiricamente a robustez do `prompts.delimitar()`.
- **Modificada:** O timeout original configurado em 60s no `config.json` foi estendido para 180s, pois chamadas com modelos de raciocínio profundo da família Flash exigem margem adicional de latência de rede.
- **Rejeitada:** Qualquer tentativa de envio automatizado de e-mail ou despacho: mantida a premissa inegociável de que nenhuma resposta sai sem a validação e decisão explícita de um servidor humano (`Human-in-the-Loop`).

## 4. Erros ou Inadequações Encontrados e Corrigidos

- **Timeout em Chamada Inicial:** A chamada inicial via `interactions.create` excedeu 60 segundos devido ao tempo de pensamento interno do modelo; ajustado para 180 segundos no `config.json`.
- **Dependência Ausente:** A biblioteca `google-genai` não estava inicialmente instalada no Python do sistema; instalada com sucesso via `pip install -r requirements.txt`.
- **Escape de Tags em Prompt Injection:** Identificada necessidade de garantir que tags falsas de `</conteudo_externo>` no texto do usuário fossem neutralizadas para `&lt;/conteudo_externo>` antes da concatenação, o que funcionou com 100% de eficácia.

## 5. Forma de Validação do Código e do Conteúdo Gerado

- **Bateria de Testes Unitários:** Execução de 58 testes automatizados via `python -m pytest`, cobrindo tratamento de erros de API, validação de arquivos, conformidade de esquemas JSON e integridade dos prompts.
- **Teste de Conexão Real:** Execução do comando `python -m src.main verificar --chamar-api` validando comunicação ativa com o Google AI Studio.
- **Execução End-to-End do Pipeline:** Processamento real dos casos `texto-01` e `texto-injection` com validação humana dos artefatos produzidos (`dados/processados/` e `resultados/minutas/`).

## 6. Declaração de Responsabilidade

A equipe revisou linha por linha o código-fonte, os prompts, as saídas produzidas e a documentação técnica, atestando a compreensão plena de todos os módulos e assumindo responsabilidade integral sobre a solução entregue.
