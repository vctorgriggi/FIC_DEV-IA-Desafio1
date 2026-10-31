# 7. Requisitos funcionais obrigatórios

Os requisitos RF14 a RF24 continuam a numeração do Desafio 01. Implemente, teste e demonstre cada um. Não há exigência de marca, versão comercial ou contratação: use API disponível ou modelo aberto equivalente, registrando capacidades e limitações. A adequação ao esquema não garante a veracidade dos valores.

| Requisito | Título |
|---|---|
| [RF14](#rf14--extração-estruturada-e-validação) | Extração estruturada e validação |
| [RF15](#rf15--sumarização-classificação-e-entidades) | Sumarização classificação e entidades |
| [RF16](#rf16--guardrails-moderação-e-limites) | Guardrails moderação e limites |
| [RF17](#rf17--embeddings-e-índice-vetorial) | Embeddings e índice vetorial |
| [RF18](#rf18--chunking-e-recuperação) | Chunking e recuperação |
| [RF19](#rf19--geração-fundamentada-com-rag) | Geração fundamentada com RAG |
| [RF20](#rf20--assistente-de-documentos-em-streamlit) | Assistente de documentos em Streamlit |
| [RF21](#rf21--provedor-configurável-e-auditoria) | Provedor configurável e auditoria |
| [RF22](#rf22--classificação-de-sentimentos) | Classificação de sentimentos |
| [RF23](#rf23--avaliação-integrada-e-regressão) | Avaliação integrada e regressão |
| [RF24](#rf24--privacidade-e-revisão-humana) | Privacidade e revisão humana |

---

## RF14 — Extração estruturada e validação

Converter cada solicitação em um contrato de dados versionado.

- Definir JSON Schema ou Pydantic com protocolo, data, solicitante fictício, assunto, pedido, categoria, entidades, campos ausentes e necessidade de revisão.
- Usar saída restrita por esquema quando suportada. Caso contrário, validar localmente, admitir no máximo uma tentativa de correção e rejeitar a saída ainda inválida.
- Comparar, em um mesmo caso, JSON apenas sintático e saída validada por esquema. Diferenciar chaves extras, tipo incorreto e campo obrigatório ausente.
- Representar ausências com null e lista de campos ausentes; apresentar “não localizado” na interface. Conferir datas, categorias e coerência com o original por regras de negócio.

**Critério de aceite:** Uma estrutura inválida ou incoerente deve ser bloqueada antes de gerar a minuta; preservar entrada, erro e decisão.

## RF15 — Sumarização classificação e entidades

Produzir uma ficha de compreensão de cada solicitação.

- Gerar resumo de até 100 palavras sem inventar dados e preservar os fatos essenciais definidos no gabarito.
- Classificar em categorias documentadas, incluindo “outros” ou “revisão”; extrair pessoas fictícias, órgãos, locais, datas e protocolos presentes.
- Separar extração literal e informação inferida; não completar entidades ausentes por suposição.
- Comparar resultados com gabarito, calcular acurácia da categoria e registrar omissões, entidades incorretas e fatos sem suporte.

**Critério de aceite:** As seis solicitações devem ter resumo, categoria e entidades conferidos, com erros e correções registrados.

## RF16 — Guardrails moderação e limites

Controlar entrada, conteúdo recuperado e saída em camadas.

- Validar tipo e tamanho de arquivo, comprimento da entrada e escopo do atendimento. Aplicar moderação por serviço ou regras documentadas, com decisão permitir, bloquear ou revisar.
- Tratar instruções contidas em documentos como conteúdo não confiável; delimitar contexto e nunca incluir segredos no prompt.
- Validar esquema da saída, verificar citações e filtrar dados indevidos; não depender apenas da frase “ignore instruções maliciosas”.
- Configurar timeout, no máximo uma repetição por falha transitória e teto de chamadas ou tokens por execução. Registrar o motivo dos bloqueios sem reproduzir segredos.

**Critério de aceite:** Os três ataques devem ser bloqueados ou encaminhados para revisão, sem mudar regras, revelar credenciais ou autorizar envio.

## RF17 — Embeddings e índice vetorial

Criar uma base de recuperação persistente do acervo.

- Extrair texto, gerar embeddings e armazenar vetores em Chroma, FAISS com metadados persistidos ou equivalente.
- Associar cada vetor a documento, versão, hash, página quando disponível, seção e identificador do trecho.
- Registrar modelo e dimensão; reutilizar o índice após reinício e impedir duplicação ao reindexar o mesmo documento.
- Disponibilizar busca top-k configurável e exibir trechos e valores de similaridade ou distância, explicando seu sentido. Mudança de modelo de embedding exige reindexação.

**Critério de aceite:** Uma consulta deve recuperar trechos rastreáveis após reiniciar a aplicação; reindexar o mesmo acervo não deve aumentar duplicatas.

## RF18 — Chunking e recuperação

Avaliar a divisão do acervo e sua influência na busca.

- Comparar duas configurações de tamanho e sobreposição de chunks, declarando a unidade usada e preservando metadados.
- Executar as mesmas cinco perguntas respondíveis em ambos os índices, com o mesmo embedding e top-k.
- Calcular acerto de recuperação: perguntas com ao menos um trecho de referência no top-k divididas pelas cinco perguntas.
- Selecionar e justificar a configuração pelo resultado e pela preservação de contexto; registrar falhas e ajustes.

**Critério de aceite:** Entregar os parâmetros, resultados por pergunta, taxa de acerto e justificativa da configuração escolhida.

## RF19 — Geração fundamentada com RAG

Gerar respostas e minutas com base nos trechos recuperados.

- Integrar perguntas, recuperação, contexto delimitado e geração; separar dados do cidadão e orientações do acervo.
- Retornar resposta, identificadores das fontes e status, fundamentada, sem evidência suficiente ou conflito de fontes.
- Citar documento, versão, trecho e página ou seção; permitir conferir a passagem original que sustenta cada afirmação institucional.
- Abster-se nas perguntas sem resposta; em conflito não resolvido, apresentar a divergência e encaminhar à revisão. Não inventar prazo, autoridade ou fundamento.

**Critério de aceite:** Executar as oito perguntas de avaliação e impedir que ausência de evidência resulte em resposta institucional inventada.

## RF20 — Assistente de documentos em Streamlit

Oferecer uma interface local para o fluxo integrado.

- Disponibilizar seleção ou inclusão de documentos, indexação, entrada da solicitação, consulta e visualização dos trechos recuperados.
- Exibir ficha estruturada, resumo, categoria, minuta e fontes; registrar aprovação, rejeição ou pedido de revisão com justificativa.
- Informar carregamento, falhas, índice desatualizado e ausência de evidência com mensagens compreensíveis.
- Permitir consultar evidências e painel sem exigir memória conversacional; cada consulta pode ser independente.

**Critério de aceite:** Um operador deve executar o fluxo e registrar a revisão pela interface.

## RF21 — Provedor configurável e auditoria

Separar o serviço de geração da recuperação e manter evidências.

- Centralizar provedor, modelo e parâmetros em configuração e isolar a chamada em um adaptador.
- Demonstrar uma segunda configuração de geração compatível; pode usar adaptador simulado identificado como tal quando não houver outro serviço disponível. Não alegar equivalência de qualidade nesse caso.
- Registrar identificador, horários, versões do esquema e prompt, consulta, IDs recuperados, versão do índice, resultado, erros, latência e decisão humana.
- Registrar tokens e custo estimado quando disponíveis; em execução local, informar indisponibilidade da métrica e tempo medido. Mascarar identificadores nos logs.

**Critério de aceite:** A troca de geração não deve reconstruir o índice; a evidência deve permitir conferir a origem de uma minuta sem expor credenciais.

## RF22 — Classificação de sentimentos

Classificar avaliações fictícias do atendimento.

- Para cada avaliação, retornar ID, polaridade positiva, negativa, neutra ou indeterminada, justificativa curta e necessidade de revisão.
- Definir regra para mensagens mistas, ironia e falta de contexto; admitir indeterminação em vez de forçar rótulo.
- Tratar confiança declarada pelo modelo como estimativa não calibrada; não usá-la como probabilidade de acerto ou medida do sentimento da população.
- Separar texto avaliado e instruções. Não inferir personalidade, diagnóstico ou características sensíveis dos autores.

**Critério de aceite:** As 12 avaliações devem possuir saída válida, rótulo conferido com gabarito e indicação explícita dos casos incertos.

## RF23 — Avaliação integrada e regressão

Avaliar a evolução sem perder o fluxo do Desafio 01.

- Executar a matriz da seção 11 com entradas, esperado, obtido, situação e evidência.
- Calcular a acurácia de categorias, acerto de recuperação e proporção de respostas institucionais com todas as afirmações sustentadas. Informar numerador e denominador.
- Medir abstenção correta nas duas perguntas sem resposta e registrar separadamente o caso contraditório. Avaliar sentimentos contra o gabarito e explicitar ambiguidades.
- Reexecutar um caso textual e um caso de áudio ou OCR do desafio anterior; corrigir falhas críticas ou declarar pendências.

**Critério de aceite:** Entregar os resultados medidos, falhas, correções e riscos residuais; a avaliação não pode se resumir a “funcionou”.

## RF24 — Privacidade e revisão humana

Manter governança e segurança no fluxo ampliado.

- Usar apenas acervo, solicitações e avaliações fictícias; minimizar conteúdo enviado ao provedor e não registrar credenciais.
- Definir retenção, exclusão de documentos, vetores e resultados derivados; excluir um documento e demonstrar que seus trechos deixam de ser recuperados.
- Exigir revisão humana antes de considerar a minuta aprovada; identificar a participação da IA e preservar a decisão do operador.

**Critério de aceite:** Demonstrar exclusão do índice e ao menos uma minuta aprovada e outra rejeitada ou enviada para revisão.

---

[← Anterior: 6. Dados de entrada e cenários mínimos](06-dados-de-entrada-e-cenarios-minimos.md) · [Índice](README.md) · [Próxima: 8. Correspondência entre aulas e requisitos funcionais →](08-correspondencia-entre-aulas-e-requisitos.md)
