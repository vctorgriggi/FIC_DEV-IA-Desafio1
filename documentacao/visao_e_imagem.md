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
  - ilustração original do modelo preservada como `<id>_ilustracao_ia.png`;
  - marca d'água SynthID, que o Gemini aplica em toda imagem gerada (fonte: docs oficiais Gemini API, image-generation, out/2026).
- **Revisão:** `python -m src.main revisar-peca <id>` passa por um checklist com cinco itens (textos; símbolos e objetos; pessoas e mãos; coerência com o caso; selo visível). Aprovar exige todos os itens conferidos.
- **Custo:** geração de imagem não tem cota gratuita. Custa US$ 0,0336 por imagem 1K (fonte: docs oficiais Gemini API, pricing, out/2026).

## Resultados

Preencher após a execução real.

| Item | Resultado |
|---|---|
| Similaridade com o gabarito (bruto / revisado) | |
| Taxa de acerto por palavra (bruto / revisado) | |
| Dados críticos não encontrados | |
| Trechos incertos apontados pelo modelo | |
| Erros relevantes | |
| Decisão sobre a peça e justificativa | |
