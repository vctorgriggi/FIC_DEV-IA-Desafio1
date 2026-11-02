# Uso de IA no desenvolvimento

A IA foi usada como apoio. O código, os prompts e as decisões são da equipe.

## Desafio 1

- **Ferramenta:** Google Antigravity IDE (Gemini 3.8 Flash).
- **Solicitações:** mapear requisitos, tirar dúvidas sobre saída em JSON, sugerir casos de ataque.
- **Aceita:** saída com esquema JSON. **Modificada:** timeout. **Rejeitada:** envio automático.
- **Erros:** timeout curto demais; tags falsas no texto de entrada.
- **Validação:** testes automatizados e execução real com revisão humana.

## Desafio 2

- **Ferramentas:** OpenAI Codex e Claude Code.
- **Solicitações:** apoio na escrita do código, na revisão e nos testes.
- **Aceita:** validação por esquema. **Modificada:** parâmetros de chunking. **Rejeitada:** alterar gabarito.
- **Erros:** ajustes de configuração e de regras, corrigidos com testes.
- **Validação:** testes sem API e rodadas reais com o provedor.
