# Uso de IA no desenvolvimento

Registro exigido pela Seção 10 do enunciado. A IA foi usada como apoio: tirar
dúvidas, sugerir abordagens e revisar trechos. O código, os prompts e as
decisões são da equipe.

## 1. Ferramentas e modelos

- **Assistente de apoio:** Google Antigravity IDE, modelo Gemini 3.8 Flash (High).
- **Modelos da solução:** `gpt-6.1-terra`, `gpt-transcribe`, `gpt-4o-mini-tts` e `gpt-image-2.5-flare`, via SDK `openai` 3.41.0.

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

## Desafio 2 — Integrante 1 (31/10/2026)

Foi usado o agente Codex para implementar dados fictícios, RF14/RF15, testes e
instruções de reprodução. O identificador exato do modelo do agente não foi
exposto nesta sessão. Não houve chamadas reais da solução: a chave estava
ausente; SDK falso e evidências reais estão identificados separadamente.

Solicitações relevantes: (1) construir a base e gabaritos antes de chamar
modelos; (2) implementar extração estrita com um único reparo e regras locais;
(3) verificar resumo, entidades e classificação nos seis casos e calcular a
métrica por código. Aceitos: Pydantic estrito e diagnóstico sem copiar valores
inválidos. Modificado: resumo generativo passou a selecionar passagens literais
para permitir conferir suporte por código. Não adotados: completar o protocolo
ilegível do OCR com o áudio e acrescentar categoria ao contrato compartilhado
sem acordo. Erros encontrados durante a implementação: sintaxe de decorador de
teste e falso erro do provedor incompatível com o adaptador; ambos corrigidos.
Datas de nascimento confundidas com data da solicitação e prefixos de protocolo
receberam testes próprios. Evidências e limitações estão em
`documentacao/desafio-2/integrante-1.md`. A revisão e responsabilidade final da
equipe permanecem necessárias; o agente não registra aprovação humana.
