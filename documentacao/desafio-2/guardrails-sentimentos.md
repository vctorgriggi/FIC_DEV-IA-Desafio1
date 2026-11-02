# RF16, RF20 e RF22 — parte 3

Implementação das funções reservadas à parte 3 no plano do grupo. Os contratos
de `schemas.py` foram preservados.

## Guardrails (RF16)

Regras locais, sem serviço de moderação externo:

- Entrada vazia ou acima de 8.000 caracteres: bloquear. Ordem para ignorar
  regras (imperativo ou infinitivo: "esqueci as orientações" é relato e passa),
  revelar segredo do sistema, mudar papel ou enviar automaticamente: bloquear.
  Credencial com formato reconhecido: bloquear, sem repetir o valor no motivo.
  Pedido do cidadão que menciona senha: revisar.
- Linguagem potencialmente abusiva/ameaça: revisar. Ausência de termos do
  atendimento educacional/administrativo: revisar. Os padrões estão em
  `src/guardrails.py`; são heurísticas conservadoras, podem gerar falsos
  positivos e não cobrem toda paráfrase ou ataque ofuscado.
- Arquivo: extensão `.txt`/`.pdf`, não vazio e até 5 MiB, conforme configuração.
  Esta função valida nome e tamanho; o extrator deve validar o conteúdo real.
- Trechos: uma decisão por trecho, preservando a ordem. Instruções embutidas ou
  segredos levam a revisar; o consumidor deve excluir esses trechos do prompt.
  Todo conteúdo permitido continua sujeito à delimitação por `prompts.delimitar`.
- Saída: bloquear fonte fora dos trechos recuperados, resposta fundamentada sem
  nenhuma citação, identificadores pessoais reconhecidos, credenciais e
  declaração de que a minuta foi enviada ou aprovada automaticamente
  ("documentos enviados" é orientação e passa). Fato do caso na minuta fica
  sem fonte; na pergunta avulsa, toda afirmação precisa de fonte
  (`rag._problemas`, que conhece o modo). Ausência de evidência, conflito e
  trecho suspeito pedem revisão. A presença de uma citação não prova suporte
  semântico: o operador precisa conferir a passagem original.
- Controle por execução: no máximo 8 tentativas e nenhuma nova chamada depois
  de atingir 60.000 tokens contabilizados. Cada repetição conta. O teto de tokens
  impede a chamada seguinte; o consumo da chamada em curso só é conhecido após
  a resposta e pode ultrapassar o teto. Tokens não informados não são estimados.
  Timeout permanece no adaptador e repetição transitória fica limitada a uma.

## Revisão e painel (RF20/RF22)

Em Solicitação, a minuta pendente aceita aprovar, rejeitar ou revisar, sempre
com justificativa e identificação fictícia do revisor. Resultado e horário são
persistidos em `resultados/minutas_rag/` e o evento em `resultados/logs/`.
Decisão registrada não pode mudar. Minuta bloqueada não aceita aprovação.
O operador pode reabrir um registro pelo ID. Não existe função de envio.

Avaliações inclui 12 textos fictícios em `dados/avaliacoes/avaliacoes.json`, com
gabarito oficial do grupo em `dados/gabaritos/D2-sentimentos.json`. Mensagens mistas sem
predominância clara, irônicas ou sem contexto devem ser indeterminadas e pedir
revisão. A justificativa descreve o texto, sem inferir traços do autor.

O prompt versionado separa instruções e avaliação delimitada; dados pessoais e
chaves reconhecidas são ocultados. Saída validada pelo esquema, ID e polaridade
configurada. Falha individual gera indeterminada, pede revisão e não interrompe
as demais avaliações. Cada avaliação tem orçamento próprio. Auditoria guarda
metadados e indicação de falha, sem o texto da avaliação.

O último lote fica em `resultados/metricas/sentimentos.json`. Painel acessível
após reinício, com filtro, gráfico, numerador/denominador por polaridade e total
de revisões. Duplicatas por ID contam uma vez (primeira ocorrência) e são
indicadas. Filtro vazio não seleciona avaliações; denominador zero resulta em
`null`. Confiança declarada não participa das contas. A conferência contra o
gabarito usa o lote completo, independente do filtro, e conta faltantes como erro.

## Verificação e integração

Executar:

```powershell
python -X utf8 -m pytest testes/test_d2_guardrails_sentimentos.py testes/test_base_desafio2.py
```

No Windows, `-X utf8` também permite rodar os testes antigos de áudio que leem
arquivos UTF-8 sem declarar a codificação. Os testes usam SDK falso e Streamlit AppTest;
verificam T04, T05, T11 e T13, falhas individuais, 12 avaliações e persistência.
As respostas simuladas verificam integração e contratos, não qualidade do modelo.

## Rodada real (RF22)

`python -m scripts.avaliar_sentimentos_d2`, perfil `principal` (`gpt-6.1-terra`),
prompt `sentimento_v1`, contra `D2-sentimentos.json` escrito antes da execução.
Uma chamada por avaliação, nenhuma falha. Evidência:
`evidencias/integrante-3-sentimentos-openai.json` e os 12 eventos `sentimento`
em `evidencias/integrante-3-auditoria-sentimentos.json`.

| Medida | Resultado |
|---|---|
| Polaridade igual ao gabarito | 11/12 = 0,917 |
| Positivas, negativas, neutras | 3/3, 3/3, 3/3 |
| Ambíguas `indeterminada` com revisão | 2/3 (AV-10 ironia, AV-12 sem contexto) |
| Tokens entrada / saída | 4.864 / 1.177 |
| Custo estimado | US$ 0,0107 |

**Divergência: AV-11** (gabarito `indeterminada`, aspectos opostos sem
predominância) saiu `negativa` sem pedido de revisão: o modelo considerou que o
pedido sem solução predomina sobre o elogio. O gabarito não foi alterado. A
consequência é que uma avaliação mista entra no painel como negativa sem passar
pelo operador; a regra do prompt não basta para esse caso.

A conferência humana dos 12 rótulos e das justificativas segue pendente.

As partes de NLP, índice e RAG da principal `9258998` estão integradas. O RAG
valida contexto antes da geração, exclui documentos suspeitos, audita IDs e
decisões, e protege também a consulta avulsa. O fluxo compartilha o controle de
recursos entre geração e embeddings. A reprodução offline das seis solicitações
usa NLP e guardrails reais com saídas NLP históricas e RAG sintético; há teste do
fluxo completo pelo Streamlit. Ver [análise da integração](integracao.md).
