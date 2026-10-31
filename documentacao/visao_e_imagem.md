# Visão/OCR (RF08) e peça visual (RF10)

## RF08 — Visão e OCR

**Rota escolhida: visão multimodal na nuvem.** O `gpt-6.1-terra` recebe o PDF inteiro como arquivo (`input_file`, com texto e imagem das páginas) e devolve, numa chamada com saída JSON validada por esquema em modo estrito, o texto bruto, a versão revisada, os trechos incertos e uma avaliação de legibilidade. Prompts: `prompts/ocr_v1.md` (tarefa) e `prompts/sistema_seguro_v1.md` (regras).

Motivo: a ficha mistura texto impresso com campos manuscritos em letra de forma, com rasuras. A rota multimodal faz leitura, correção de formato e marcação de incerteza no mesmo passo. Não comparamos com um OCR tradicional; essa comparação fica como limitação.

**Proteções:**

- O PDF original não é alterado; o hash SHA-256 dele vai para o log de cada execução.
- O texto bruto fica preservado em `texto_bruto.txt`, separado do `texto_revisado.txt`. A revisão só corrige formato (acento, espaço, pontuação de data, CPF e e-mail) e não troca número, nome ou data por palpite.
- Leitura duvidosa ou ilegível vai para `trechos_incertos`.
- Comparação com o gabarito (`dados/gabaritos/imagem-01.json`) em `comparacao_gabarito.json`: similaridade, taxa de acerto por palavra, lista de substituições, omissões e inserções, e dados críticos não encontrados. A métrica ignora caixa e acento e preserva a pontuação de dados.
- Protocolo, data e solicitante passam por confirmação humana antes da minuta (critério de aceite do RF08). Campo preenchido na confirmação deixa de constar como ausente para a minuta.

**Quando o processamento local seria preferível:**

- **Privacidade:** a ficha real teria CPF, RG, filiação, data de nascimento e e-mail. Diferente do texto, que é mascarado antes do envio (`privacidade.mascarar`), a imagem vai inteira ao provedor e não dá para mascarar antes.
- **Soberania:** dados de cidadãos sob guarda de um órgão público passariam a ser tratados por um provedor estrangeiro, fora do controle da instituição e sujeitos ao contrato e à política dele. Pela API, a OpenAI não usa os dados enviados para treinar modelos por padrão, mas guarda registros por até 30 dias para monitoramento de abuso (fonte: docs oficiais OpenAI API, your-data, out/2026).
- **Custo e dependência:** em volume alto e recorrente, o custo por chamada e a dependência de um fornecedor pesam mais do que manter um modelo local.
- **Operação e auditoria:** uso sem internet, ou exigência de auditar o modelo por inteiro.

Neste desafio, a nuvem é aceitável porque os dados são fictícios e a Responses API é chamada com `store=False`.

## RF10 — Peça visual de orientação

- **Especificação:** `prompts/peca_visual_v1.json`, com sujeito, composição, estilo, iluminação, proporção e restrições, além do texto da peça. O caso é `imagem-01`, e a orientação vem da regra de frequência presente na ficha e na solicitação em texto.
- **Restrições sempre aplicadas** (`RESTRICOES_OBRIGATORIAS` em `src/image_generation.py`): sem texto na ilustração; sem pessoas reais ou rostos identificáveis; sem brasões, bandeiras, logotipos ou símbolos oficiais.
- **Tamanho:** a API recebe tamanho em pixels, não proporção; a proporção 4:3 da especificação vira 1536x1152 (`image_generation.TAMANHOS`).
- **Texto por código:** o modelo gera só a ilustração, e o texto e o selo são aplicados com Pillow. Assim o texto da peça sai exatamente igual aos dados do caso; a revisão confere a ilustração.
- **Proveniência:**
  - selo visível na peça ("Ilustração gerada por IA (modelo) — conteúdo sintético, material fictício");
  - nota de proveniência, prompt, especificação, modelo e data no `.json` ao lado da imagem;
  - ilustração original do modelo preservada como `<id>_ilustracao_ia.png`.
- **Revisão:** checklist com cinco itens (textos; símbolos e objetos; pessoas e mãos; coerência com o caso; selo visível), na interface ou em `python -m src.main revisar-peca <id>`. Aprovar exige todos os itens conferidos.
- **Custo:** cobrado por token; a API não tem camada gratuita para geração de imagem.

## Resultados (rodada de 31/10/2026)

**OCR de `imagem-01`**, execução final `0f37876c722b` (`dados/processados/imagem-01/0f37876c722b/`; `gpt-6.1-terra`, 18,0 s, 2.555 tokens de entrada e 1.371 de saída, US$ 0,0094 estimado). As três leituras do caso nesta rodada ficaram entre 97,0% e 97,7% de palavras corretas, e em todas o protocolo saiu como ilegível:

| Item | Resultado |
|---|---|
| Similaridade com o gabarito (bruto / revisado) | 0,970 / 0,970 |
| Palavras corretas (bruto / revisado) | 97,7% / 97,7% (129 de 132) |
| Legibilidade avaliada pelo modelo | regular |
| Dados críticos encontrados | MARCOS VINICIUS DE ALMEIDA SANTOS, 12/08/2008, 123.456.789-00, 1234567-8, 01/02/2027, 14/10/2026 |
| Dados críticos não encontrados | 2026-000142, transcrito como `202[ilegível] - 000142` |
| Trechos incertos apontados pelo modelo | O dígito rasurado do protocolo e a parte final do CPF |
| Erros relevantes | E-mail com "exemplo" no lugar de "examplo" |

O modelo não arriscou o dígito rasurado: marcou-o como ilegível e incerto, e a extração deixou o protocolo como "não localizado". A confirmação humana preencheu 2026-000142, o mesmo protocolo da solicitação em texto do mesmo cidadão. Na execução `5270cc7d02bb`, o CPF também veio como `123.456.[ilegível]00`, forma que o mascaramento não reconhece (ver `lgpd_campos.md`).

**Peça visual** (`gpt-image-2.5-flare`, 14,2 s, 227 tokens de entrada e 724 de saída, US$ 0,0229 estimado): `resultados/imagens/09a2c80850f8.png`, com a ilustração original do modelo ao lado (`09a2c80850f8_ilustracao_ia.png`) e prompt, especificação, modelo, data e nota de proveniência em `09a2c80850f8.json`.

| Item | Resultado |
|---|---|
| Confirmação humana dos dados críticos | Protocolo preenchido com 2026-000142 nas três execuções; ver `avaliacao.md` |
| Decisão sobre a peça e justificativa | Aprovada, com os cinco itens do checklist marcados como conferidos (`09a2c80850f8.json`) |
| Ilustração | Sala de curso de enfermagem à noite, sem pessoas e sem texto embutido |
