# 10. Estrutura sugerida do projeto

```text
desafio_ia_generativa/
  README.md | requirements.txt | .env.example | .gitignore
  config.json
  dados/ originais/ acervo/ avaliacoes/ gabaritos/ processados/
  src/ app.py | llm_client.py | schemas.py | nlp.py
       guardrails.py | ingestion.py | embeddings.py | rag.py
       sentiment.py | metrics.py | audit.py
       audio.py | vision.py | image_generation.py (reutilizados)
  prompts/
  indice/
  resultados/ minutas/ metricas/ logs/
  testes/
  documentacao/
```

A organização é sugestiva. Mantenha separadas recuperação, geração, validação e agregação. Não distribua credenciais nem documentos reais junto ao índice.

---

[← Anterior: 9. Fluxo mínimo esperado](09-fluxo-minimo-esperado.md) · [Índice](README.md) · [Próxima: 11. Testes obrigatórios →](11-testes-obrigatorios.md)
