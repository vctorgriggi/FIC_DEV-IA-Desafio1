# Entrega — Desafio Prático 02 · IA Generativa

**Central Inteligente de Atendimento**: assistente de documentos com RAG,
guardrails e revisão humana, evoluído a partir do Desafio 1.

Grupo: André Nunes, Daniel Alves e Victor Griggi Moreira Regis da Silva.

| | |
|---|---|
| Vídeo da apresentação | https://youtu.be/XiW-5hzud_U |
| Pasta da entrega (zip e slides) | https://drive.google.com/drive/folders/1UbQIg1MB6q_aj_eebnslz_G3aKHjwAyo |
| Repositório | https://github.com/vctorgriggi/FIC_DEV-IA-Desafio1 |

## Por onde começar

1. [`documentacao/desafio-2/integracao.md`](documentacao/desafio-2/integracao.md):
   estado da entrega, rodada final, métricas do RF23, matriz T01–T15 e
   decisões do operador.
2. [`documentacao/relatorio_tecnico.md`](documentacao/relatorio_tecnico.md),
   seção final: arquitetura, provedor configurável, custos, privacidade e
   limitações do Desafio 2.
3. [`README.md`](README.md): instalação e comandos.

## Como rodar

Requer Python 3.11 ou mais recente.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest                    # 389 testes, sem chamar a API
cp .env.example .env                # preencha OPENAI_API_KEY para usar o assistente
python -m src.main assistente       # http://127.0.0.1:8501
```

No assistente, a tela "Acervo e índice" tem o botão "Indexar o acervo": o
índice não vai no zip e se recria a partir de `dados/acervo/`.

## Onde está cada entregável (seção 13)

| Entregável | Onde |
|---|---|
| Código, dependências, configuração e README | `src/`, `requirements.txt`, `config.json`, `README.md` |
| Dados fictícios, acervo, gabaritos, esquemas e prompts | `dados/`, `src/schemas.py`, `prompts/` |
| JSON sintático × esquema; resumo, classificação e entidades | `documentacao/desafio-2/integrante-1.md` |
| Comparação de chunking e índice reproduzível | `documentacao/desafio-2/integrante-2.md` |
| Oito consultas RAG com fontes e decisões; três ataques | `documentacao/desafio-2/integracao.md`, `resultados/minutas_rag/` |
| Doze avaliações, métricas e painel | `documentacao/desafio-2/guardrails-sentimentos.md` |
| Matriz de testes, regressão, logs e exclusão | `documentacao/desafio-2/integracao.md`, `resultados/logs/` |
| Relatório técnico e uso de IA | `documentacao/relatorio_tecnico.md`, `documentacao/uso_de_ia.md` |

As evidências das execuções reais estão em
`documentacao/desafio-2/evidencias/`. Todos os dados são fictícios; nenhuma
resposta é enviada ao cidadão sem decisão humana registrada.
