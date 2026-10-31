# 11. Testes obrigatórios

A matriz deverá informar ID, requisito, entrada, resultado esperado, resultado obtido, evidência e situação. Um cenário pode ter múltiplas execuções; resultados de referência devem preceder a chamada ao modelo.

| Teste | Cenário | Resultado esperado |
|---|---|---|
| T01 | RF15 — JSON válido com tipo incorreto e campo ausente. | Rejeição do esquema ou ausência explícita; nenhuma minuta inválida. |
| T02 | RF15 — Data impossível ou dado não presente no original. | Regra de negócio bloqueia e solicita revisão. |
| T03 | RF16 — Seis solicitações com gabarito. | Resumo fiel, categoria e entidades avaliados. |
| T04 | RF17 — Três entradas adversariais. | Instruções não executadas e segredo não revelado. |
| T05 | RF16 — Fora de escopo, arquivo excessivo e limite de chamadas. | Bloqueio ou revisão e limite respeitado. |
| T06 | RF17 — Reinício e reindexação do mesmo acervo. | Índice reutilizado e sem duplicação. |
| T07 | RF18 — Duas configurações e cinco perguntas. | Top-k comparado e acerto calculado. |
| T08 | RF19 — Cinco perguntas respondíveis. | Respostas e citações verificadas contra fontes. |
| T09 | RF19 — Duas perguntas sem evidência. | Abstenção e encaminhamento ao operador. |
| T10 | RF19 — Fontes contraditórias. | Prioridade documentada ou conflito e revisão. |
| T11 | RF20/RF24 — Aprovação e rejeição na interface. | Estados e justificativas persistidos; sem envio automático. |
| T12 | RF21 — Troca de geração e falha do serviço. | Índice preservado; falha tratada e auditada. |
| T13 | RF23 — Filtro, duplicata e conjunto vazio. | Totais corretos, denominador visível e sem divisão por zero. |
| T14 | RF24 — Exclusão de documento e derivados. | Trechos removidos da busca e exclusão registrada. |
| T15 | RF23 — Regressão textual e áudio ou OCR. | Entradas anteriores seguem até minuta e revisão. |

---

[← Anterior: 10. Estrutura sugerida do projeto](10-estrutura-sugerida-do-projeto.md) · [Índice](README.md) · [Próxima: 12. Uso da Inteligência Artificial durante o desenvolvimento →](12-uso-da-ia-durante-o-desenvolvimento.md)
