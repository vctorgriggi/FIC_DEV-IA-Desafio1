# 8. Fluxo mínimo esperado

| Etapa | Responsabilidade mínima | Evidência |
|---|---|---|
| Entrada | Receber texto, áudio ou imagem e validar o arquivo. | Arquivo original e registro do caso. |
| Extração | Transcrever áudio ou extrair texto por OCR/visão. | Texto bruto, texto revisado e comparação com gabarito. |
| Compreensão | Classificar e extrair campos em estrutura JSON. | JSON válido e campos ausentes sinalizados. |
| Geração | Produzir minuta com prompt seguro e contexto delimitado. | Prompt, saída e fontes utilizadas. |
| Acessibilidade | Gerar versão em áudio do texto aprovado. | Arquivo de voz e configurações. |
| Comunicação visual | Gerar ou editar peça institucional. | Imagem, prompt e nota de proveniência. |
| Revisão | Aprovar, rejeitar ou solicitar correção. | Decisão humana e justificativa. |
| Auditoria | Registrar modelos, parâmetros, tempos, erros e custos. | Log estruturado e relatório final. |

---

[← Anterior: 7. Requisitos funcionais obrigatórios](07-requisitos-funcionais-obrigatorios.md) · [Índice](README.md) · [Próxima: 9. Estrutura sugerida do projeto →](09-estrutura-sugerida-do-projeto.md)
