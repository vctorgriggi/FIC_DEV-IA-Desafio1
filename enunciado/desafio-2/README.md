# FIC_DEV

**PROGRAMADOR DE SISTEMAS COM IA**

## DESAFIO PRÁTICO 02

# Central Inteligente de Atendimento e Comunicação Institucional

**Inteligência Artificial Generativa**

| | |
|---|---|
| Carga horária recomendada | 12 horas de evolução do protótipo |
| Modalidade | equipe de até três estudantes |
| Conteúdos avaliados | Aulas 08 a 14 |
| Versão | 2.0 — 2026 |

Este desafio dá continuidade ao Desafio 01: a central multimodal passa a consultar um acervo institucional fictício, validar dados, responder com fontes e analisar avaliações de atendimento. O produto é um protótipo local para revisão humana.

> **Produto esperado**
>
> Assistente de documentos com saída estruturada, sumarização, classificação, extração de entidades, guardrails, busca vetorial e RAG, interface Streamlit, painel de sentimentos e trilha de auditoria. As minutas continuam sujeitas à aprovação humana.

---

## Sumário

| Seção | Arquivo | Página no PDF |
|---|---|---|
| 1. Orientações gerais | [01-orientacoes-gerais.md](01-orientacoes-gerais.md) | 2 |
| 2. Objetivos de aprendizagem | [02-objetivos-de-aprendizagem.md](02-objetivos-de-aprendizagem.md) | 2 |
| 3. Situação-problema | [03-situacao-problema.md](03-situacao-problema.md) | 2–3 |
| 4. Problema proposto | [04-problema-proposto.md](04-problema-proposto.md) | 3 |
| 5. Organização das equipes | [05-organizacao-das-equipes.md](05-organizacao-das-equipes.md) | 3 |
| 6. Dados de entrada e cenários mínimos | [06-dados-de-entrada-e-cenarios-minimos.md](06-dados-de-entrada-e-cenarios-minimos.md) | 3–4 |
| 7. Requisitos funcionais obrigatórios | [07-requisitos-funcionais-obrigatorios.md](07-requisitos-funcionais-obrigatorios.md) | 4–8 |
| 8. Correspondência entre aulas e requisitos funcionais | [08-correspondencia-entre-aulas-e-requisitos.md](08-correspondencia-entre-aulas-e-requisitos.md) | 9 |
| 9. Fluxo mínimo esperado | [09-fluxo-minimo-esperado.md](09-fluxo-minimo-esperado.md) | 9–10 |
| 10. Estrutura sugerida do projeto | [10-estrutura-sugerida-do-projeto.md](10-estrutura-sugerida-do-projeto.md) | 10 |
| 11. Testes obrigatórios | [11-testes-obrigatorios.md](11-testes-obrigatorios.md) | 10–11 |
| 12. Uso da Inteligência Artificial durante o desenvolvimento | [12-uso-da-ia-durante-o-desenvolvimento.md](12-uso-da-ia-durante-o-desenvolvimento.md) | 11–12 |
| 13. Entregáveis | [13-entregaveis.md](13-entregaveis.md) | 12 |
| 14. Apresentação | [14-apresentacao.md](14-apresentacao.md) | 12 |
| 15. Critérios de avaliação | [15-criterios-de-avaliacao.md](15-criterios-de-avaliacao.md) | 13 |
| 16. Restrições e princípios de segurança | [16-restricoes-e-principios-de-seguranca.md](16-restricoes-e-principios-de-seguranca.md) | 13 |

### Requisitos funcionais

| Requisito | Página no PDF |
|---|---|
| [RF14 — Extração estruturada e validação](07-requisitos-funcionais-obrigatorios.md#rf14--extração-estruturada-e-validação) | 4–5 |
| [RF15 — Sumarização classificação e entidades](07-requisitos-funcionais-obrigatorios.md#rf15--sumarização-classificação-e-entidades) | 5 |
| [RF16 — Guardrails moderação e limites](07-requisitos-funcionais-obrigatorios.md#rf16--guardrails-moderação-e-limites) | 5 |
| [RF17 — Embeddings e índice vetorial](07-requisitos-funcionais-obrigatorios.md#rf17--embeddings-e-índice-vetorial) | 5–6 |
| [RF18 — Chunking e recuperação](07-requisitos-funcionais-obrigatorios.md#rf18--chunking-e-recuperação) | 6 |
| [RF19 — Geração fundamentada com RAG](07-requisitos-funcionais-obrigatorios.md#rf19--geração-fundamentada-com-rag) | 6 |
| [RF20 — Assistente de documentos em Streamlit](07-requisitos-funcionais-obrigatorios.md#rf20--assistente-de-documentos-em-streamlit) | 6–7 |
| [RF21 — Provedor configurável e auditoria](07-requisitos-funcionais-obrigatorios.md#rf21--provedor-configurável-e-auditoria) | 7 |
| [RF22 — Classificação de sentimentos](07-requisitos-funcionais-obrigatorios.md#rf22--classificação-de-sentimentos) | 7 |
| [RF23 — Avaliação integrada e regressão](07-requisitos-funcionais-obrigatorios.md#rf23--avaliação-integrada-e-regressão) | 7–8 |
| [RF24 — Privacidade e revisão humana](07-requisitos-funcionais-obrigatorios.md#rf24--privacidade-e-revisão-humana) | 8 |

---

## Material fornecido

- [`Desafio_02-Pratico_IA_Generativa_Aulas_08_a_15.docx.pdf`](Desafio_02-Pratico_IA_Generativa_Aulas_08_a_15.docx.pdf): o enunciado original, em PDF.
- [`arquivos/`](arquivos/): o Edital nº 006/2026/SECITECI-MT (processo seletivo de alunos para cursos técnicos nas ETECs, 2º semestre) e seis editais retificadores, como foram recebidos.

## Entrega

Conforme as instruções de envio recebidas com o enunciado: por e-mail para ficdev00@gmail.com, com o assunto `Desafio02-FICDEV-IAGenerativa`, até 02/11/2026 às 23h59, pelo mesmo grupo do Desafio 1.

## Notas da transcrição

- A capa indica "Aulas 08 a 14", e o nome do arquivo, "Aulas_08_a_15". A seção 1 explica que a Aula 15 (memória conversacional e persona) fica para uma etapa posterior.
- Na seção 11, os requisitos citados em T01 a T04 parecem deslocados em relação à seção 7: T01 e T02 (esquema e regra de negócio) correspondem ao RF14, T03 (seis solicitações com gabarito) ao RF15, e T04 (entradas adversariais) ao RF16. A transcrição mantém o texto do PDF.

---

*Transcrição de `Desafio_02-Pratico_IA_Generativa_Aulas_08_a_15.docx.pdf` (13 páginas). O rodapé de cada página — "FIC_DEV | Inteligência Artificial Generativa | n" — foi omitido; a paginação está indicada no sumário.*
