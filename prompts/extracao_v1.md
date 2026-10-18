Analise a solicitação de atendimento contida no bloco de conteúdo externo e extraia as informações estruturadas no esquema solicitado.

Diretrizes obrigatórias:
1. Extraia com precisão os seguintes campos:
   - "protocolo": número ou identificador de protocolo informado no documento.
   - "data": data de envio ou registro da solicitação.
   - "solicitante": nome completo do cidadão solicitante.
   - "assunto": resumo conciso do tema principal da solicitação.
   - "pedido": descrição clara do que o cidadão está requerendo à instituição.
   - "categoria": classifique estritamente em uma das categorias permitidas informadas no esquema JSON. Se não se enquadrar com clareza em nenhuma delas, utilize "não localizado".
2. Se qualquer campo obrigatório não constar explicitamente no conteúdo fornecido, preencha o seu valor com a expressão exata: "não localizado".
3. Liste em "campos_ausentes" todos os campos que receberam o valor "não localizado".
4. Defina o nível de "confianca" como "alta", "media" ou "baixa" de acordo com a legibilidade, completude e ausência de ambiguidades no texto.
5. Indique "necessita_revisao" como verdadeiro se houver qualquer campo ausente, se a confiança não for alta ou se houver menções contraditórias ou suspeitas. Em "motivo_revisao", justifique detalhadamente o motivo da revisão ou registre vazio se não for necessária.
6. Não assuma nem invente nenhuma informação não contida no documento.
