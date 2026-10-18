# Uso de IA no desenvolvimento

Registro exigido pela Seção 10 do enunciado. A IA foi usada como apoio: tirar
dúvidas, sugerir abordagens e revisar trechos. O código, os prompts e as
decisões são da equipe.

## 1. Ferramentas e modelos

- **Assistente de apoio:** Google Antigravity IDE, modelo Gemini 3.8 Flash (High).
- **Modelo da solução:** `gemini-3.8-flash` via `google-genai` 2.31.0 (Interactions API).

## 2. Solicitações relevantes

1. Ajuda para mapear, no enunciado, os requisitos da parte de texto (RF02, RF03, RF05, RF09, RF12).
2. Dúvidas sobre saída estruturada com esquema JSON no SDK `google-genai`.
3. Sugestões de entrada adversarial para o caso de prompt injection.

## 3. Sugestões aceitas, modificadas e rejeitadas

- **Aceita:** usar `response_format` com esquema JSON e enum de categorias.
- **Modificada:** timeout de 60 s, ajustado pela equipe para 180 s após testes reais.
- **Rejeitada:** qualquer envio automático de resposta; toda minuta passa por decisão humana.

## 4. Erros encontrados

- O timeout sugerido era curto para o modelo e estourava na primeira chamada.
- Tags falsas como `</conteudo_externo>` precisavam ser neutralizadas antes de entrar no prompt.

## 5. Validação

- Testes automatizados (`python -m pytest`), sem chamada à API.
- Execução real dos casos, com revisão humana das saídas.

## 6. Responsabilidade

A equipe revisou e entende todo o código, prompts e documentação, e assume
responsabilidade integral pela solução entregue.
