# 7. Requisitos funcionais obrigatórios

Cada requisito deverá ser implementado, testado e demonstrado. Quando um serviço pago não estiver disponível, a equipe poderá utilizar cota gratuita ou modelo aberto equivalente, desde que documente a substituição e preserve a finalidade pedagógica do requisito.

| Requisito | Título |
|---|---|
| [RF01](#rf01--inicialização-e-configuração) | Inicialização e configuração |
| [RF02](#rf02--experimento-de-engenharia-de-prompts) | Experimento de engenharia de prompts |
| [RF03](#rf03--prompt-seguro-e-conteúdo-não-confiável) | Prompt seguro e conteúdo não confiável |
| [RF04](#rf04--chamada-de-api-e-tratamento-de-falhas) | Chamada de API e tratamento de falhas |
| [RF05](#rf05--entrada-textual-e-extração-estruturada) | Entrada textual e extração estruturada |
| [RF06](#rf06--transcrição-de-áudio) | Transcrição de áudio |
| [RF07](#rf07--síntese-de-voz-e-acessibilidade) | Síntese de voz e acessibilidade |
| [RF08](#rf08--visão-e-ocr) | Visão e OCR |
| [RF09](#rf09--geração-da-minuta-institucional) | Geração da minuta institucional |
| [RF10](#rf10--geração-ou-edição-de-imagem) | Geração ou edição de imagem |
| [RF11](#rf11--registro-e-rastreabilidade) | Registro e rastreabilidade |
| [RF12](#rf12--lgpd-privacidade-e-minimização) | LGPD, privacidade e minimização |
| [RF13](#rf13--avaliação-de-qualidade-e-revisão-humana) | Avaliação de qualidade e revisão humana |

---

## RF01 — Inicialização e configuração

A solução deverá possuir um ponto de entrada reproduzível.

- ser executada por comando documentado, preferencialmente `python -m src.main`;
- utilizar arquivo de configuração para caminhos, modelos e parâmetros não sensíveis;
- carregar segredos por variáveis de ambiente ou arquivo `.env` não versionado;
- fornecer `.env.example` sem credenciais reais;
- registrar as versões de Python e das principais bibliotecas.

**Critério de aceite:** um integrante deve conseguir instalar e executar a solução seguindo apenas o `README.md`.

## RF02 — Experimento de engenharia de prompts

A equipe deverá executar um experimento controlado com três prompts para a mesma tarefa de redação institucional.

- Prompt A: instrução zero-shot curta;
- Prompt B: prompt estruturado manualmente com Persona, Contexto, Tarefa, Formato e Critérios de sucesso;
- Prompt C: prompt produzido com auxílio de um metaprompt;
- manter o mesmo modelo e, quando possível, os mesmos parâmetros nos três testes;
- avaliar fidelidade ao contexto, dados inventados, formato, tom, lacunas e tempo até um resultado utilizável;
- selecionar e justificar o prompt que será incorporado ao sistema.

**Critério de aceite:** as três entradas, saídas e a matriz comparativa devem acompanhar a entrega.

## RF03 — Prompt seguro e conteúdo não confiável

O prompt de produção deverá separar instruções do sistema e conteúdo fornecido pelo usuário.

- delimitar claramente o conteúdo externo;
- orientar o modelo a tratar instruções presentes em documentos como dados, não como comandos;
- proibir a invenção de fatos, prazos, autoridades e fundamentos legais;
- usar a expressão não localizado quando um campo obrigatório estiver ausente;
- solicitar saída estruturada e verificável;
- incluir teste de prompt injection em pelo menos uma entrada.

## RF04 — Chamada de API e tratamento de falhas

A solução deverá realizar pelo menos uma chamada programática a um provedor de modelo.

- enviar modelo, mensagem e parâmetros de geração de forma configurável;
- definir timeout;
- tratar chave ausente, autenticação inválida, limite de requisições, indisponibilidade e resposta vazia;
- não registrar credenciais nos logs;
- registrar tempo de resposta e, quando disponível, uso de tokens e custo estimado;
- fornecer mensagem compreensível quando o serviço não estiver disponível.

## RF05 — Entrada textual e extração estruturada

Para cada solicitação textual, o sistema deverá gerar uma representação estruturada.

- identificar protocolo, data, solicitante fictício, assunto e pedido;
- classificar o tema em uma lista documentada de categorias;
- indicar campos ausentes e nível de confiança ou necessidade de revisão;
- preservar o texto original;
- gravar o resultado em JSON.

**Critério de aceite:** a estrutura JSON deverá permanecer válida mesmo quando houver campos ausentes.

## RF06 — Transcrição de áudio

A aplicação deverá processar pelo menos uma mensagem de voz fictícia.

- validar extensão e tamanho do arquivo;
- executar speech-to-text por API ou modelo aberto;
- preservar a transcrição bruta e produzir uma versão revisada;
- registrar idioma, modelo e duração do áudio;
- comparar a transcrição com um texto de referência e apontar erros relevantes.

**Critério de aceite:** nomes, números de protocolo e datas devem ser conferidos antes da geração da minuta.

## RF07 — Síntese de voz e acessibilidade

O sistema deverá gerar uma versão falada da minuta aprovada.

- utilizar text-to-speech por API ou modelo aberto;
- selecionar voz e instruções de entonação adequadas a uma comunicação institucional;
- não sintetizar campos marcados como não localizado sem aviso ao ouvinte;
- salvar o arquivo de áudio em formato comum;
- documentar como o recurso amplia a acessibilidade e quais limitações permanecem.

**Critério de aceite:** o áudio deve corresponder ao texto aprovado, sem acréscimos relevantes.

## RF08 — Visão e OCR

A solução deverá extrair informações de um documento fictício.

- implementar uma rota de OCR tradicional ou visão multimodal;
- preservar o arquivo original e o texto bruto extraído;
- produzir uma versão corrigida sem alterar o sentido;
- identificar trechos ilegíveis ou incertos;
- comparar o resultado com um gabarito e registrar acertos e erros;
- justificar quando seria preferível processamento local por soberania ou privacidade.

**Critério de aceite:** dados críticos extraídos da imagem devem passar por confirmação humana.

## RF09 — Geração da minuta institucional

O sistema deverá produzir uma minuta de resposta.

- usar somente os dados presentes na entrada ou fornecidos no contexto;
- seguir o modelo institucional definido pela equipe;
- marcar explicitamente informações ausentes;
- incluir referências aos arquivos de origem utilizados;
- impedir envio automático.

## RF10 — Geração ou edição de imagem

A equipe deverá produzir uma peça visual de orientação relacionada a um dos casos fictícios.

- elaborar prompt com sujeito, composição, estilo, iluminação, proporção e restrições;
- gerar uma imagem nova ou editar uma imagem fornecida;
- verificar textos, símbolos, mãos, objetos e coerência visual quando aplicável;
- manter o prompt, o modelo e a data de geração;
- identificar o material como gerado ou editado por IA;
- não utilizar imagem de pessoa real sem autorização.

**Critério de aceite:** a peça deve ser revisada e acompanhada de nota de proveniência.

## RF11 — Registro e rastreabilidade

Cada execução relevante deverá produzir um registro estruturado.

- armazenar identificador da execução, data e hora, modalidade de entrada e arquivo de origem;
- registrar provedor, modelo, parâmetros e versão do prompt;
- registrar resultado, duração, erros e decisão humana;
- não armazenar a chave da API;
- permitir relacionar a saída ao caso que a originou.

**Critério de aceite:** deve ser possível reconstruir como uma saída foi obtida sem revelar segredos.

## RF12 — LGPD, privacidade e minimização

A solução deverá aplicar cuidados compatíveis com o tratamento responsável de dados.

- utilizar somente dados fictícios;
- identificar quais campos seriam dados pessoais em um cenário real;
- informar finalidade, necessidade e risco de cada campo;
- minimizar o envio de conteúdo ao provedor.

**Critério de aceite:** nenhuma evidência entregue poderá conter credencial ou dado pessoal real.

## RF13 — Avaliação de qualidade e revisão humana

A equipe deverá definir e aplicar um protocolo de avaliação.

- avaliar fidelidade, completude, formato, linguagem e segurança;
- registrar resultado esperado e resultado obtido para cada caso;
- classificar erros por gravidade;
- definir quais resultados exigem nova geração ou correção manual;
- calcular uma taxa simples de aprovação dos casos;
- registrar limitações e riscos residuais.

**Critério de aceite:** a demonstração deve incluir pelo menos um caso aprovado e um caso rejeitado ou corrigido.

---

[← Anterior: 6. Dados de entrada e cenários mínimos](06-dados-de-entrada-e-cenarios-minimos.md) · [Índice](README.md) · [Próxima: 8. Fluxo mínimo esperado →](08-fluxo-minimo-esperado.md)
