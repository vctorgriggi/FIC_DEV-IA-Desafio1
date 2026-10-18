# Visão/OCR (RF08) e peça visual (RF10)

## RF08 — Visão e OCR

**Rota escolhida: visão multimodal na nuvem.** O `gemini-3.8-flash` recebe o PDF inteiro como documento e devolve, numa chamada com saída JSON validada por esquema, o texto bruto, a versão revisada, os trechos incertos e uma avaliação de legibilidade. Prompts: `prompts/ocr_v1.md` (tarefa) e `prompts/sistema_seguro_v1.md` (regras).

Motivo: a ficha mistura texto impresso com campos manuscritos em letra de forma, com rasuras. A rota multimodal faz leitura, correção de formato e marcação de incerteza no mesmo passo. Não comparamos com um OCR tradicional; essa comparação fica como limitação.

**Proteções:**

- O PDF original não é alterado; o hash SHA-256 dele vai para o log de cada execução.
- O texto bruto fica preservado em `texto_bruto.txt`, separado do `texto_revisado.txt`. A revisão só corrige formato (acento, espaço, pontuação de data, CPF e e-mail) e não troca número, nome ou data por palpite.
- Leitura duvidosa ou ilegível vai para `trechos_incertos`.
- Comparação com o gabarito (`dados/gabaritos/imagem-01.json`) em `comparacao_gabarito.json`: similaridade, taxa de acerto por palavra, lista de substituições, omissões e inserções, e dados críticos não encontrados. A métrica ignora caixa e acento e preserva a pontuação de dados.
- Protocolo, data e solicitante passam por confirmação humana antes da minuta (critério de aceite do RF08).

**Quando o processamento local seria preferível:**

- **Privacidade:** a ficha real teria CPF, RG, filiação, data de nascimento e e-mail. Diferente do texto, que é mascarado antes do envio (`privacidade.mascarar`), a imagem vai inteira ao provedor e não dá para mascarar antes.
- **Soberania:** dados de cidadãos sob guarda de um órgão público passariam a ser tratados por um provedor estrangeiro, fora do controle da instituição e sujeitos ao contrato e à política dele. Na camada gratuita do Gemini, o conteúdo enviado é usado para melhorar os produtos do Google (fonte: docs oficiais Gemini API, pricing, out/2026).
- **Custo e dependência:** em volume alto e recorrente, o custo por chamada e a dependência de um fornecedor pesam mais do que manter um modelo local.
- **Operação e auditoria:** uso sem internet, ou exigência de auditar o modelo por inteiro.

Neste desafio, a nuvem é aceitável porque os dados são fictícios e as chamadas usam `store=False`.

## RF10 — Peça visual de orientação

- **Especificação:** `prompts/peca_visual_v1.json`, com sujeito, composição, estilo, iluminação, proporção e restrições, além do texto da peça. O caso é `imagem-01`, e a orientação vem da regra de frequência presente na ficha e na solicitação em texto.
- **Restrições sempre aplicadas** (`RESTRICOES_OBRIGATORIAS` em `src/image_generation.py`): sem texto na ilustração; sem pessoas reais ou rostos identificáveis; sem brasões, bandeiras, logotipos ou símbolos oficiais.
- **Texto por código:** o modelo gera só a ilustração, e o texto e o selo são aplicados com Pillow. Assim o texto da peça sai exatamente igual aos dados do caso; a revisão confere a ilustração.
- **Proveniência:**
  - selo visível na peça ("Ilustração gerada por IA (modelo) — conteúdo sintético, material fictício");
  - nota de proveniência, prompt, especificação, modelo e data no `.json` ao lado da imagem;
  - ilustração original do modelo preservada como `<id>_ilustracao_ia`, no formato em que o modelo devolve (nesta rodada, `.jpg`);
  - marca d'água SynthID, que o Gemini aplica em toda imagem gerada (fonte: docs oficiais Gemini API, image-generation, out/2026).
- **Revisão:** `python -m src.main revisar-peca <id>` passa por um checklist com cinco itens (textos; símbolos e objetos; pessoas e mãos; coerência com o caso; selo visível). Aprovar exige todos os itens conferidos.
- **Custo:** geração de imagem não tem cota gratuita. Custa US$ 0,0336 por imagem 1K (fonte: docs oficiais Gemini API, pricing, out/2026).

## Resultados (rodada de 18/10/2026)

**OCR de `imagem-01`**, primeira leitura (execução `4e54dbcf2418`, `dados/processados/imagem-01/4e54dbcf2418/`; `gemini-3.8-flash`, 22 s, 1.124 tokens de entrada e 2.843 de saída, US$ 0,0115 estimado). As quatro leituras seguintes também deram 2024-000142 no protocolo:

| Item | Resultado |
|---|---|
| Similaridade com o gabarito (bruto / revisado) | 0,952 / 0,970 |
| Palavras corretas (bruto / revisado) | 97% / 97% (128 de 132) |
| Dados críticos encontrados | 12/08/2008, 123.456.789-00, 1234567-8, 01/02/2027, 14/10/2026 |
| Dados críticos não encontrados | 2026-000142 (lido 2024-000142) e MARCOS VINICIUS DE ALMEIDA SANTOS (lido MARCUS) |
| Trechos incertos apontados pelo modelo | 01/02/2027 e 14/10/2026, ambos lidos corretamente |
| Erros relevantes | Protocolo com dígito rasurado lido como 4; "MARCOS" lido como "MARCUS"; e-mail com "exemplo" no lugar de "examplo" |
| Correção do texto revisado | Só acento e formato (CUIABA → CUIABÁ, e-mail juntado); nenhum número ou nome trocado, como o prompt exige |

O caso mostra o motivo da confirmação humana: o modelo errou o protocolo sem marcá-lo como incerto e marcou como incertas duas datas corretas. A comparação com o gabarito pegou os dois erros críticos.

**Peça visual** (`gemini-3.1-flash-lite-image`, 3,9 s, US$ 0,0337 estimado): `resultados/imagens/882e9080c8c0.png`, com a ilustração original do modelo ao lado (`882e9080c8c0_ilustracao_ia.jpg`) e prompt, especificação, modelo, data e nota de proveniência em `882e9080c8c0.json`. Na camada gratuita, a primeira tentativa recebeu "limit: 0 requests per day on Free Tier"; a peça foi gerada depois que o faturamento do projeto foi ativado.

| Item | Resultado |
|---|---|
| Confirmação humana dos dados críticos | Em `a28f7fde3ba8`, protocolo corrigido de 2024-000142 para 2026-000142. Em duas execuções anteriores, o valor lido foi confirmado sem correção; ver `avaliacao.md` |
| Decisão sobre a peça e justificativa | Aprovada, com os cinco itens do checklist marcados como conferidos (`882e9080c8c0.json`) |
