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

Em 01/11/2026, Codex auxiliou na implementação da parte 3 do Desafio 2
(RF16/RF20/RF22), incluindo regras locais de guardrail, prompt de sentimentos,
painel Streamlit, revisão persistida e testes sem API. A solicitação foi
implementar essas RFs no projeto existente. Foram adotados filtros com contagem
determinística e classificação indeterminada com revisão em falhas individuais.
As 12 avaliações e seu gabarito foram criados como exemplos fictícios antes de
qualquer classificação real. A conferência humana dos rótulos e a validação com
o provedor ainda precisam ser feitas pela equipe; testes simulados não medem
qualidade do modelo.

A equipe revisou e entende todo o código, prompts e documentação, e assume
responsabilidade integral pela solução entregue.

Na integração da principal `2728ddd` em 01/11/2026, Codex ajudou a resolver
conflitos, antecipar a verificação de contexto RAG, compartilhar o orçamento
com embeddings, corrigir falsos positivos em negações e preservar os bytes
do acervo no Windows. As avaliações locais da primeira implementação foram
substituídas pelas doze avaliações oficiais do Integrante 1, mantendo seu
gabarito `D2-sentimentos.json`. A validação nova executa módulos reais com
transporte simulado; saídas NLP históricas são reproduzidas e as minutas de
integração são sintéticas. Nenhuma nova execução real ou aprovação humana é
alegada. A análise e o canvas distinguem essas evidências das rodadas reais
anteriores presentes no repositório.

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

## Continuação do Integrante 1 — validação real (01/11/2026 UTC)

Codex executou as seis solicitações com a OpenAI, corrigiu falhas observadas e
registrou o histórico sem alterar os gabaritos. Solicitações relevantes:
(1) validar RF14/RF15 com dados reais da API sob orçamento de US$ 1;
(2) incluir revisao de modo compatível; (3) aceitar paráfrases sem aceitar
fatos inventados. Aceitos: categoria aditiva e verificação semântica com fontes
literais. Modificados: resumo estritamente extrativo e política que confundia
ficha sem pedido com categoria ambígua. Rejeitada: reescrita do gabarito null
para inflar a acurácia. Corrigidos: conflito de ausência entre sistemas D1/D2,
data de matrícula omitida, protocolo parcial como entidade, classificação de
emissão como matrícula e assunto omitido por ausência de cabeçalho.

O agente realizou conferência técnica, sem registrar aprovação humana. Os
resultados reais (31 chamadas; US$ 0,065461 estimados) e os testes offline estão
identificados separadamente na documentação do Integrante 1. Todos os modelos
continuam acessados via ClienteLLM; nenhuma chave integra as evidências.
