"""Estudante 2 — embeddings, índice, RAG e provedor (RF17, RF18, RF19, RF21, RF24). Nenhum teste chama a API."""

import json
import re
import shutil
import zlib
from types import SimpleNamespace

import pytest
from pypdf import PdfWriter

from src import fluxo_rag, guardrails, ingestion, metrics, nlp, rag, revisao
from src.config import RAIZ
from src.embeddings import IndiceIncompativel, IndiceVetorial
from src.entradas import ArquivoInvalido
from src.llm_client import ClienteLLM, RespostaMalformada
from src.schemas import DecisaoGuardrail, DocumentoAcervo, TrechoRecuperado
from src.tipos import Resultado
from testes import exemplos, falsos


def vetor(texto: str, dimensao: int = 64) -> list[float]:
    """Embedding falso por saco de palavras: textos com palavras em comum ficam próximos."""
    valores = [0.0] * dimensao
    for palavra in re.findall(r"\w+", texto.lower()):
        valores[zlib.crc32(palavra.encode()) % dimensao] += 1.0
    return valores if any(valores) else [1.0] + [0.0] * (dimensao - 1)


class SDKComEmbeddings(falsos.SDKFalso):
    """SDKFalso cujos embeddings dependem do texto, para a busca ter sentido sem rede."""

    def __init__(self, *argumentos, **opcoes):
        super().__init__(*argumentos, **opcoes)
        self.embeddings = SimpleNamespace(create=self._embeddings)

    def _embeddings(self, **argumentos):
        self.chamadas.append({"_operacao": "embeddings.create", **argumentos})
        return falsos.embeddings([vetor(t) for t in argumentos["input"]], tokens=10 * len(argumentos["input"]))

    def operacoes(self, nome):
        return [c for c in self.chamadas if c["_operacao"] == nome]


@pytest.fixture
def acervo(config):
    """O acervo fictício real do Desafio 2 (6 documentos, TXT e PDF), copiado para a raiz temporária."""
    shutil.copytree(RAIZ / "dados" / "acervo", config.caminho("acervo"))
    return {d.id: d for d in ingestion.ler_manifesto(config)}


@pytest.fixture
def sdk():
    return SDKComEmbeddings()


@pytest.fixture
def indice(config, sdk, acervo):
    indice = IndiceVetorial(config, ClienteLLM(config, chave="c", sdk=sdk))
    for documento in acervo.values():
        indice.indexar(documento)
    return indice


def gerador(config, *saidas):
    """Cliente de geração separado do índice: as respostas JSON são escritas depois de saber os ids dos trechos."""
    sdk = SDKComEmbeddings(respostas=[falsos.resposta(json.dumps(s, ensure_ascii=False)) for s in saidas])
    return ClienteLLM(config, chave="c", sdk=sdk), sdk


def id_de(indice, documento_id, contendo="histórico escolar"):
    """Id do trecho do documento que contém o texto, seja qual for o chunking do config."""
    dados = indice._colecao.get(where={"documento_id": documento_id}, include=["documents"])
    return next(i for i, texto in zip(dados["ids"], dados["documents"]) if contendo in texto)


def todos_no_top_k(config, indice):
    config.dados["indice"]["top_k"] = indice.contar()


def _tudo(indice):
    dados = indice._colecao.get(include=["metadatas"])
    return dados["ids"], dados["metadatas"]


# --- RF17: extração e divisão ------------------------------------------------------------------


def test_extrai_txt_em_um_bloco_e_pdf_por_pagina(config, acervo):
    [(pagina, texto)] = ingestion.extrair_texto(acervo["DOC-02"], config=config)
    assert pagina is None and "30/10/2026" in texto
    paginas = ingestion.extrair_texto(acervo["DOC-03"], config=config)
    assert [p for p, _ in paginas] == [1] and paginas[0][1].strip()


def test_extracao_recusa_arquivo_excessivo_e_pdf_sem_texto(config, acervo):
    config.dados["acervo"]["tamanho_max_mb"] = 0.0001
    with pytest.raises(ArquivoInvalido, match="passa de"):
        ingestion.extrair_texto(acervo["DOC-02"], config=config)
    config.dados["acervo"]["tamanho_max_mb"] = 5
    escritor = PdfWriter()
    escritor.add_blank_page(width=100, height=100)
    with open(config.caminho("acervo") / "vazio.pdf", "wb") as arquivo:
        escritor.write(arquivo)
    vazio = DocumentoAcervo(id="X", titulo="t", versao="1", arquivo="vazio.pdf", tema="x")
    with pytest.raises(ArquivoInvalido, match="sem texto extraível"):
        ingestion.extrair_texto(vazio, config=config)


def test_divisao_respeita_tamanho_sobreposicao_secao_e_ids_deterministicos(config, acervo):
    texto = "\n".join(f"{n}. Seção {n}\n" + " ".join(f"palavra{n}x{i}" for i in range(60)) for n in range(1, 4))
    (config.caminho("acervo") / "longo.txt").write_text(texto, encoding="utf-8")
    documento = DocumentoAcervo(id="LONGO", titulo="Longo", versao="1", arquivo="longo.txt", tema="x")
    paginas = ingestion.extrair_texto(documento, config=config)
    trechos = ingestion.dividir(documento, paginas, perfil="A", config=config)
    assert len(trechos) > 1 and all(len(t.texto) <= 800 for t in trechos)
    for anterior, seguinte in zip(trechos, trechos[1:]):
        assert seguinte.texto[:50] in anterior.texto  # sobreposição de 100 caracteres
    hash_ = trechos[0].hash_documento
    assert [t.id for t in trechos] == [f"LONGO:{hash_[:12]}:A:{n}" for n in range(len(trechos))]
    assert trechos[0].secao.startswith("1. Seção 1") and trechos[0].pagina is None and trechos[0].chunking == "A"
    assert ingestion.dividir(documento, paginas, perfil="A", config=config) == trechos
    assert len(ingestion.dividir(documento, paginas, perfil="B", config=config)) < len(trechos)


# --- RF17 e RF24: índice persistente ----------------------------------------------------------------


def test_indice_reaberto_reutiliza_e_reindexar_nao_duplica_nem_chama_o_provedor(config, sdk, acervo, indice):
    total = indice.contar()
    assert total >= len(acervo)
    chamadas = len(sdk.operacoes("embeddings.create"))
    reaberto = IndiceVetorial(config, ClienteLLM(config, chave="c", sdk=sdk))
    assert reaberto.contar() == total
    for documento in acervo.values():
        reaberto.indexar(documento)
    assert reaberto.contar() == total and len(sdk.operacoes("embeddings.create")) == chamadas
    info = reaberto.info()
    assert info["modelo_embedding"] == config.modelo("embeddings") and info["dimensao"] == 64
    assert set(info["documentos"]) == set(acervo) and info["versao_indice"] == indice.info()["versao_indice"]


def test_busca_devolve_trechos_rastreaveis_em_ordem_de_distancia(config, indice):
    achados = indice.buscar("documentos para matrícula: identificação e histórico escolar", top_k=3)
    assert len(achados) == 3
    assert [a.distancia for a in achados] == sorted(a.distancia for a in achados)
    primeiro = achados[0].trecho
    assert primeiro.documento_id in {"DOC-01", "DOC-02"} and primeiro.hash_documento and primeiro.versao
    pdf = [a for a in indice.buscar("declaração escolar", top_k=6) if a.trecho.documento_id == "DOC-03"]
    assert pdf and pdf[0].trecho.pagina == 1


def test_consulta_vai_mascarada_ao_embedding(config, sdk, indice):
    indice.buscar("Meu CPF é 123.456.789-00, quais documentos?")
    enviado = sdk.operacoes("embeddings.create")[-1]["input"][0]
    assert "123.456.789-00" not in enviado and "[CPF removido]" in enviado


def test_arquivo_alterado_troca_os_trechos_e_aparece_como_desatualizado(config, acervo, indice):
    antigos = [i for i, m in zip(*_tudo(indice)) if m["documento_id"] == "DOC-05"]
    caminho = config.caminho("acervo") / "doc-05.txt"
    caminho.write_text(caminho.read_text(encoding="utf-8") + "\nNovo parágrafo fictício.", encoding="utf-8")
    assert indice.desatualizados(list(acervo.values())) == ["DOC-05"]
    indice.indexar(acervo["DOC-05"])
    novos = [i for i, m in zip(*_tudo(indice)) if m["documento_id"] == "DOC-05"]
    assert novos and not set(novos) & set(antigos)
    assert indice.desatualizados(list(acervo.values())) == []


def test_indice_vazio_busca_sem_chamar_o_provedor(config, sdk, acervo):
    vazio = IndiceVetorial(config, ClienteLLM(config, chave="c", sdk=sdk), chunking="B")
    assert vazio.buscar("qualquer coisa") == [] and sdk.chamadas == []
    assert vazio.desatualizados(list(acervo.values())) == sorted(acervo)


def test_outro_modelo_de_embedding_exige_reindexar(config, indice):
    config.dados["modelos"]["embeddings"] = "outro-modelo"
    with pytest.raises(IndiceIncompativel, match="Apague a pasta"):
        IndiceVetorial(config, indice.cliente)


def test_excluir_remove_o_documento_de_todas_as_colecoes(config, sdk, acervo, indice):
    indice_b = IndiceVetorial(config, ClienteLLM(config, chave="c", sdk=sdk), chunking="B")
    indice_b.indexar(acervo["DOC-05"])
    por_colecao = indice.info()["documentos"], indice_b.info()["documentos"]
    assert all("DOC-05" in d for d in por_colecao)
    removidos = indice.excluir("DOC-05")
    assert removidos >= 2
    assert all("DOC-05" not in d for d in (indice.info()["documentos"], indice_b.info()["documentos"]))
    assert all(a.trecho.documento_id != "DOC-05" for a in indice.buscar("horário de atendimento", top_k=10))


# --- RF20 e RF24: inclusão e exclusão de documento --------------------------------------------------


@pytest.fixture
def arquivo_permitido(monkeypatch):
    decisao = DecisaoGuardrail(decisao="permitir", camada="arquivo", regra="teste", motivo="teste")
    monkeypatch.setattr(guardrails, "verificar_arquivo", lambda nome, tamanho, *, config: decisao)


def test_inclusao_grava_arquivo_e_manifesto_e_audita(config, acervo, auditoria, arquivo_permitido):
    metadados = {"id": "DOC-07", "titulo": "Guia fictício novo", "versao": "1.0", "tema": "atendimento", "vigencia_inicio": ""}
    documento = ingestion.incluir_documento(config, nome_arquivo="doc-07.txt", conteudo="1. Tema\nTexto.".encode(),
                                            metadados=metadados, auditoria=auditoria)
    assert documento.id == "DOC-07" and documento.vigencia_inicio is None
    assert "DOC-07" in {d.id for d in ingestion.ler_manifesto(config)}
    [evento] = auditoria.eventos(etapa="acervo_inclusao")
    assert evento["caso_id"] == "DOC-07" and "Texto" not in json.dumps(evento)
    with pytest.raises(ArquivoInvalido, match="Já existe"):
        ingestion.incluir_documento(config, nome_arquivo="doc-07.txt", conteudo=b"outro",
                                    metadados={**metadados, "id": "DOC-08"}, auditoria=auditoria)
    assert (config.caminho("acervo") / "doc-07.txt").read_text(encoding="utf-8") == "1. Tema\nTexto."


def test_inclusao_desfeita_quando_o_texto_nao_se_extrai(config, acervo, auditoria, arquivo_permitido):
    manifesto = (config.caminho("acervo") / "acervo.json").read_text(encoding="utf-8")
    with pytest.raises(ArquivoInvalido, match="ilegível|sem texto"):
        ingestion.incluir_documento(config, nome_arquivo="ruim.pdf", conteudo=b"%PDF-1.4 sem paginas",
                                    metadados={"id": "X", "titulo": "t", "versao": "1", "tema": "x"}, auditoria=auditoria)
    assert not (config.caminho("acervo") / "ruim.pdf").exists()
    assert (config.caminho("acervo") / "acervo.json").read_text(encoding="utf-8") == manifesto


def test_inclusao_respeita_o_guardrail_de_arquivo(config, acervo, auditoria, monkeypatch):
    decisao = DecisaoGuardrail(decisao="bloquear", camada="arquivo", regra="tamanho", motivo="Arquivo excessivo.")
    monkeypatch.setattr(guardrails, "verificar_arquivo", lambda nome, tamanho, *, config: decisao)
    with pytest.raises(ArquivoInvalido, match="excessivo"):
        ingestion.incluir_documento(config, nome_arquivo="grande.txt", conteudo=b"x",
                                    metadados={"id": "X", "titulo": "t", "versao": "1", "tema": "x"}, auditoria=auditoria)
    assert not (config.caminho("acervo") / "grande.txt").exists()


def test_exclusao_remove_indice_manifesto_e_arquivo_e_conta_minutas(config, acervo, indice, auditoria):
    citante = exemplos.resposta_rag(trechos=[TrechoRecuperado(trecho=exemplos.trecho(documento_id="DOC-05"), distancia=0.1)])
    revisao.gravar_registro_rag(config, exemplos.registro("aprovada", resposta=citante))
    removido = ingestion.excluir_documento(config, "DOC-05", indice=indice, auditoria=auditoria)
    assert removido["trechos_removidos"] >= 1 and removido["minutas_que_citam"] == 1
    assert "DOC-05" not in {d.id for d in ingestion.ler_manifesto(config)}
    assert not (config.caminho("acervo") / "doc-05.txt").exists()
    assert all(a.trecho.documento_id != "DOC-05" for a in indice.buscar("horário de atendimento", top_k=10))
    [evento] = auditoria.eventos(etapa="acervo_exclusao")
    assert evento["extra"]["documento_id"] == "DOC-05"


def test_exclusao_recusa_documento_substituido_por_outro(config, acervo, indice, auditoria):
    with pytest.raises(ArquivoInvalido, match="DOC-02 substitui DOC-01"):
        ingestion.excluir_documento(config, "DOC-01", indice=indice, auditoria=auditoria)
    assert (config.caminho("acervo") / "doc-01.txt").exists() and "DOC-01" in indice.info()["documentos"]


# --- RF18: acerto de recuperação ---------------------------------------------------------------------


def test_acerto_de_recuperacao_por_pergunta_com_denominador():
    obtido = metrics.acerto_recuperacao(
        {"R1": ["a", "b"], "R2": ["c"], "R9": ["x"]}, {"R1": ["b"], "R2": ["z"], "R3": ["y"]}
    )
    assert (obtido["numerador"], obtido["denominador"], obtido["valor"]) == (1, 3, 0.333)
    assert [p["acerto"] for p in obtido["por_pergunta"]] == [True, False, False]
    assert obtido["por_pergunta"][0]["referencias_no_top_k"] == ["b"]
    assert metrics.acerto_recuperacao({}, {})["valor"] is None


# --- RF19: geração fundamentada -------------------------------------------------------------------------


def fundamentada(id_trecho, texto="Apresente documento de identificação e histórico escolar."):
    return {"status": "fundamentada", "resposta": texto, "afirmacoes": [{"texto": texto, "fontes": [id_trecho]}]}


def test_resposta_fundamentada_cita_trechos_delimitados(config, indice):
    todos_no_top_k(config, indice)
    alvo = id_de(indice, "DOC-02")
    cliente, sdk = gerador(config, fundamentada(alvo))
    resultado = rag.responder("Quais documentos levo na matrícula? CPF 123.456.789-00", indice=indice, cliente=cliente, config=config)
    assert resultado.valor.status == "fundamentada" and resultado.valor.necessita_revisao
    assert resultado.valor.fontes() == [alvo] and len(resultado.valor.trechos) < indice.contar()
    assert all(t.trecho.documento_id != 'DOC-06' for t in resultado.valor.trechos)
    assert resultado.prompt.identificador == "rag_d2_v1" and len(resultado.respostas) == 1
    [chamada] = sdk.chamadas
    assert chamada["model"] == config.perfil_geracao()["modelo"] and chamada["text"]["format"]["strict"] is True
    assert f"Trecho id={alvo}" in chamada["input"] and "substitui DOC-01" in chamada["input"]
    assert '<conteudo_externo origem="acervo/DOC-02">' in chamada["input"] and "123.456.789-00" not in chamada["input"]


def test_sem_trecho_abstem_sem_chamar_o_modelo(config, sdk, acervo):
    vazio = IndiceVetorial(config, ClienteLLM(config, chave="c", sdk=sdk))
    cliente, chamadas = gerador(config)
    resultado = rag.responder("Qual o valor da bolsa?", indice=vazio, cliente=cliente, config=config)
    assert resultado.valor.status == "sem_evidencia" and resultado.valor.necessita_revisao
    assert resultado.valor.afirmacoes == [] and chamadas.chamadas == []


def test_fonte_fora_dos_trechos_tem_uma_correcao(config, indice):
    todos_no_top_k(config, indice)
    alvo = id_de(indice, "DOC-02")
    cliente, sdk = gerador(config, fundamentada("DOC-99:inventado:A:0"), fundamentada(alvo))
    resultado = rag.responder("Quais documentos levo na matrícula?", indice=indice, cliente=cliente, config=config)
    assert resultado.valor.fontes() == [alvo] and len(resultado.respostas) == 2
    assert "fora dos trechos recuperados" in sdk.chamadas[1]["input"] and "DOC-99" not in sdk.chamadas[1]["input"]


@pytest.mark.parametrize(
    "saida",
    [
        {"status": "fundamentada", "resposta": "O prazo termina em 15/12/2026.", "afirmacoes": []},
        {"status": "sem_evidencia", "resposta": "O prazo é de 45 dias.", "afirmacoes": []},
        {"status": "conflito", "resposta": "Há divergência.", "afirmacoes": [{"texto": "Há divergência.", "fontes": []}]},
        {"status": "fundamentada", "resposta": "ok", "afirmacoes": [], "extra": 1},
    ],
    ids=["fundamentada_sem_fonte", "prazo_inventado", "conflito_sem_fonte", "chave_extra"],
)
def test_resposta_sem_fundamento_conferivel_e_rejeitada(config, indice, saida):
    cliente, _ = gerador(config, saida, saida)
    with pytest.raises(RespostaMalformada, match="RF19") as erro:
        rag.responder("Qual o prazo?", indice=indice, cliente=cliente, config=config)
    assert len(erro.value.respostas) == 2 and erro.value.prompt.identificador == "rag_d2_v1"


def test_sem_evidencia_pode_citar_o_trecho_que_diz_que_nao_ha_regra(config, indice):
    todos_no_top_k(config, indice)
    alvo = id_de(indice, "DOC-02", "valores de bolsas")
    saida = {"status": "sem_evidencia", "resposta": "O acervo não define valores de bolsas; o caso segue para o operador.",
             "afirmacoes": [{"texto": "Não estão definidos valores de bolsas.", "fontes": [alvo]}]}
    cliente, _ = gerador(config, saida)
    resultado = rag.responder("Qual o valor da bolsa?", indice=indice, cliente=cliente, config=config)
    assert resultado.valor.status == "sem_evidencia" and resultado.valor.necessita_revisao


def test_minuta_separa_caso_e_acervo_e_nao_envia_o_original(config, indice):
    todos_no_top_k(config, indice)
    alvo = id_de(indice, "DOC-02")
    texto = "Protocolo 2026-000001: apresente documento de identificação e histórico escolar."
    cliente, sdk = gerador(config, fundamentada(alvo, texto))
    original = "Texto original com telefone (65) 99999-1234 e protocolo 2026-000001."
    resultado = rag.minuta_fundamentada(exemplos.solicitacao(necessita_revisao=True, motivo_revisao="conferir"), original,
                                        indice=indice, cliente=cliente, config=config)
    assert resultado.valor.status == "fundamentada" and resultado.valor.necessita_revisao
    enviado = sdk.chamadas[0]["input"]
    assert '<conteudo_externo origem="solicitacao">' in enviado and "Texto original" not in enviado
    assert resultado.prompt.identificador == "minuta_rag_d2_v1"


def test_minuta_com_fato_do_caso_sem_fonte_passa_sem_correcao(config, indice):
    todos_no_top_k(config, indice)
    alvo = id_de(indice, "DOC-02")
    orientacao = "Apresente documento de identificação e histórico escolar."
    cliente, sdk = gerador(config, {"status": "fundamentada", "resposta": "Recebemos seu pedido de matrícula. " + orientacao,
                                    "afirmacoes": [{"texto": "O pedido é de matrícula.", "fontes": []},
                                                   {"texto": orientacao, "fontes": [alvo]}]})
    resultado = rag.minuta_fundamentada(exemplos.solicitacao(), "x", indice=indice, cliente=cliente, config=config)
    assert resultado.valor.status == "fundamentada" and len(resultado.respostas) == 1


def test_minuta_sem_assunto_nem_pedido_nao_consulta_nem_gera(config, sdk, indice):
    antes = len(sdk.chamadas)
    cliente, gerado = gerador(config)
    resultado = rag.minuta_fundamentada(exemplos.solicitacao(assunto=None, pedido=None), "x",
                                        indice=indice, cliente=cliente, config=config)
    assert resultado.valor.status == "sem_evidencia" and "esclarecimento" in resultado.valor.resposta
    assert gerado.chamadas == [] and len(sdk.chamadas) == antes


def test_troca_de_perfil_de_geracao_preserva_o_indice(config, sdk, indice):
    todos_no_top_k(config, indice)
    antes = indice.info()
    cliente, gerado = gerador(config, fundamentada(id_de(indice, "DOC-02")))
    rag.responder("Quais documentos levo na matrícula?", indice=indice, cliente=cliente, config=config, perfil="alternativo")
    assert gerado.chamadas[0]["model"] == config.perfil_geracao("alternativo")["modelo"]
    assert indice.info() == antes
    assert len(sdk.operacoes("embeddings.create")[-1]["input"]) == 1  # só a consulta, nada reindexado


# --- RF19 e RF21: fluxo integrado ----------------------------------------------------------------------


def permitir(camada):
    return DecisaoGuardrail(decisao="permitir", camada=camada, regra="teste", motivo="teste")


@pytest.fixture
def partes(monkeypatch):
    """Guardrails e NLP das outras partes substituídos por exemplos válidos; cada teste muda o que precisa."""
    resposta_nlp = falsos.resposta("{}", entrada=100, saida=50)
    from src.llm_client import RespostaLLM

    chamada = RespostaLLM(texto="{}", modelo="gpt-6.1-terra", duracao_s=0.1, tokens_entrada=100, tokens_saida=50,
                          custo_estimado_usd=0.001)
    estado = SimpleNamespace(entrada=permitir("entrada"), trechos="permitir", saida=permitir("saida"), resposta=resposta_nlp)
    monkeypatch.setattr(guardrails, "verificar_entrada", lambda texto, *, config: estado.entrada)
    monkeypatch.setattr(guardrails, "verificar_trechos", lambda trechos, *, config: [
        DecisaoGuardrail(decisao=estado.trechos, camada="trechos", regra="teste", motivo="teste") for _ in trechos])
    monkeypatch.setattr(guardrails, "verificar_saida", lambda resposta, *, config: estado.saida)
    monkeypatch.setattr(nlp, "extrair_solicitacao", lambda texto, **_: Resultado(exemplos.solicitacao(), [chamada, chamada]))
    monkeypatch.setattr(nlp, "validar_regras", lambda solicitacao, texto, *, config: [])
    monkeypatch.setattr(nlp, "compreender", lambda texto, solicitacao, **_: Resultado(exemplos.ficha(), [chamada]))
    return estado


def processar(config, indice, auditoria, cliente, texto="Pedido fictício de matrícula. CPF 123.456.789-00."):
    return fluxo_rag.processar_solicitacao(texto, origem="teste", config=config, cliente=cliente, indice=indice, auditoria=auditoria)


def test_fluxo_grava_minuta_pendente_e_audita_cada_etapa(config, indice, auditoria, partes):
    todos_no_top_k(config, indice)
    alvo = id_de(indice, "DOC-02")
    cliente, _ = gerador(config, fundamentada(alvo))
    registro = processar(config, indice, auditoria, cliente)
    assert registro.status == "pendente" and registro.resposta.fontes() == [alvo] and registro.decisao is None
    assert "123.456.789-00" not in registro.entrada
    assert revisao.ler_registro_rag(config, registro.id_execucao) == registro
    eventos = auditoria.eventos(id_execucao=registro.id_execucao)
    assert [e["etapa"] for e in eventos] == ["d2_entrada", "d2_extracao", "d2_compreensao", "d2_recuperacao_geracao", "d2_registro"]
    extracao, geracao = eventos[1], eventos[3]
    assert extracao["tokens_entrada"] == 200 and extracao["parametros"]["chamadas"] == 2
    assert geracao["versao_prompt"] == "minuta_rag_d2_v1" and geracao["extra"]["esquema_versao"] == "2.0"
    assert geracao["extra"]["ids_recuperados"] and geracao["extra"]["indice"]["versao_indice"] == indice.info()["versao_indice"]
    assert geracao["extra"]["perfil_geracao"] == "principal" and geracao["extra"]["tokens_embedding"] == 10
    assert "123.456.789-00" not in auditoria.arquivo.read_text(encoding="utf-8")


def test_entrada_bloqueada_para_antes_de_qualquer_chamada(config, indice, auditoria, partes):
    partes.entrada = DecisaoGuardrail(decisao="bloquear", camada="entrada", regra="segredo", motivo="Pede credencial.")
    cliente, gerado = gerador(config)
    registro = processar(config, indice, auditoria, cliente)
    assert registro.status == "bloqueada" and registro.solicitacao is None and gerado.chamadas == []
    assert [e["etapa"] for e in auditoria.eventos(id_execucao=registro.id_execucao)] == ["d2_entrada", "d2_registro"]


def test_estrutura_invalida_bloqueia_antes_da_minuta(config, indice, auditoria, partes, monkeypatch):
    def invalida(texto, **_):
        erro = RespostaMalformada("RF14: extração inválida após uma tentativa de reparo.", detalhe='["data: impossível"]')
        erro.respostas, erro.prompt = [], None
        raise erro

    monkeypatch.setattr(nlp, "extrair_solicitacao", invalida)
    cliente, gerado = gerador(config)
    registro = processar(config, indice, auditoria, cliente)
    assert registro.status == "bloqueada" and registro.resposta is None and gerado.chamadas == []
    assert registro.problemas_validacao == ["RF14: extração inválida após uma tentativa de reparo.", "data: impossível"]
    assert auditoria.eventos(id_execucao=registro.id_execucao, etapa="d2_extracao")[0]["erro"].startswith("RF14")


def test_saida_bloqueada_nao_grava_a_minuta(config, indice, auditoria, partes):
    todos_no_top_k(config, indice)
    partes.saida = DecisaoGuardrail(decisao="bloquear", camada="saida", regra="fonte", motivo="Fonte inválida.")
    cliente, _ = gerador(config, fundamentada(id_de(indice, "DOC-02")))
    registro = processar(config, indice, auditoria, cliente)
    assert registro.status == "bloqueada" and registro.resposta is None and registro.ficha is not None


def test_trecho_marcado_para_revisao_marca_a_minuta(config, indice, auditoria, partes):
    todos_no_top_k(config, indice)
    partes.trechos = "revisar"
    cliente, _ = gerador(config, fundamentada(id_de(indice, "DOC-02")))
    registro = processar(config, indice, auditoria, cliente)
    assert registro.status == "pendente" and registro.resposta.necessita_revisao


def test_falha_do_provedor_e_auditada_e_levantada(config, indice, auditoria, partes):
    from src.llm_client import ServicoIndisponivel

    erro = type("APIStatusError", (Exception,), {"status_code": 503})("indisponível")
    cliente = ClienteLLM(config, chave="c", sdk=falsos.SDKFalso(erro=erro))
    with pytest.raises(ServicoIndisponivel):
        processar(config, indice, auditoria, cliente)
    [evento] = auditoria.eventos(etapa="d2_recuperacao_geracao")
    assert evento["erro"].startswith("ServicoIndisponivel") and evento["extra"]["indice"]["chunking"] == config.dados["indice"]["chunking_ativo"]
    assert list(config.caminho("minutas_rag").glob("*.json")) == []


# --- RF20: botões do assistente ----------------------------------------------------------------------------


@pytest.fixture
def app_indice(config, acervo, monkeypatch):
    """Assistente com o acervo real e o SDK falso no lugar do OpenAI: os botões rodam sem rede."""
    from streamlit.testing.v1 import AppTest

    saida = {"status": "sem_evidencia", "resposta": "O acervo não traz a informação.", "afirmacoes": []}
    falso = SDKComEmbeddings(falsos.resposta(json.dumps(saida, ensure_ascii=False)))
    monkeypatch.setattr("src.config.carregar_config", lambda: config)
    monkeypatch.setattr("src.llm_client.carregar_chave", lambda: "sk-teste-sem-rede")
    monkeypatch.setattr("openai.OpenAI", lambda **_: falso)
    return AppTest.from_file(str(RAIZ / "src" / "app.py"), default_timeout=30)


def clicar(app, rotulo):
    next(b for b in app.button if b.label == rotulo).click().run()


def test_indexar_pela_interface_nao_soma_o_teto_entre_documentos(config, app_indice):
    config.dados["limites"]["max_chamadas_por_execucao"] = 1
    app = app_indice.run()
    app.sidebar.radio[0].set_value("Acervo e índice").run()
    clicar(app, "Indexar o acervo")
    assert not app.exception and not app.error
    assert sum("trechos no índice" in m.value for m in app.markdown) == len(ingestion.ler_manifesto(config))


def test_botoes_de_indice_e_consulta_funcionam_pela_interface(app_indice):
    app = app_indice.run()
    app.sidebar.radio[0].set_value("Acervo e índice").run()
    assert any("desatualizado" in a.value for a in app.warning)
    clicar(app, "Indexar o acervo")
    assert not app.exception and not app.error
    app.sidebar.radio[0].set_value("Consulta ao acervo").run()
    app.text_input[0].input("Quais documentos?").run()
    clicar(app, "Buscar trechos")
    assert not app.exception and not app.error and app.dataframe
    clicar(app, "Responder com fontes")
    assert not app.exception and not app.error


def test_botao_de_exclusao_remove_pela_interface(app_indice, config):
    app = app_indice.run()
    app.sidebar.radio[0].set_value("Acervo e índice").run()
    next(s for s in app.selectbox if s.label.startswith("Documento a excluir")).set_value("DOC-06").run()
    clicar(app, "Excluir documento")
    assert not app.exception and any("DOC-06 excluído" in s.value for s in app.success)
    assert "DOC-06" not in {d.id for d in ingestion.ler_manifesto(config)}


# --- Correções da revisão: checagem de números, chunking, exclusão, consulta e casos do Desafio 1 --------


def _recuperado(id_trecho, documento_id, texto):
    trecho = exemplos.trecho(id=id_trecho, documento_id=documento_id, hash_documento="c7e6dd7ecc2b", texto=texto)
    return TrechoRecuperado(trecho=trecho, distancia=0.3)


SEM_PRAZO = _recuperado("DOC-05:c7e6dd7ecc2b:B:0", "DOC-05", "O prazo de resposta de reclamações não está definido.")
PRAZO_ANTIGO = _recuperado("DOC-01:4cf44a695a2c:B:1", "DOC-01", "O prazo de matrícula termina em 20/10/2026.")


@pytest.mark.parametrize(
    ("resposta", "afirmacao", "caso"),
    [
        ("É de 7 dias.", "O prazo é de 7 dias.", "Qual o prazo?"),  # dígito do hash no id do trecho
        ("São 45 dias.", "O prazo é de 45 dias.", "Ouvi que são 45 dias?"),  # número plantado na pergunta
        ("Termina em 20/10/2026.", "Reclamações têm regra própria.", "Qual o prazo?"),  # número de trecho não citado
    ],
    ids=["hash_do_id", "numero_da_pergunta", "trecho_nao_citado"],
)
def test_prazo_sem_fonte_citada_e_rejeitado(resposta, afirmacao, caso):
    gerada = rag.RespostaGerada(status="fundamentada", resposta=resposta,
                                afirmacoes=[{"texto": afirmacao, "fontes": [SEM_PRAZO.trecho.id]}])
    assert rag._problemas(gerada, [SEM_PRAZO, PRAZO_ANTIGO], caso=caso, modo="pergunta")


def test_data_da_pergunta_e_numero_citado_passam():
    gerada = rag.RespostaGerada(status="fundamentada", resposta="Em 15/10/2026, o prazo termina em 20/10/2026.",
                                afirmacoes=[{"texto": "O prazo termina em 20/10/2026.", "fontes": [PRAZO_ANTIGO.trecho.id]}])
    assert rag._problemas(gerada, [PRAZO_ANTIGO], caso="Qual o prazo em 15/10/2026?", modo="pergunta") == []


def test_minuta_aceita_numero_do_caso_so_fora_das_afirmacoes_institucionais():
    caso = '{"pedido": "curso de 1200 horas", "protocolo": "2026-000142"} texto original'
    fato = rag.RespostaGerada(status="fundamentada", resposta="Seu curso de 1200 horas, protocolo 2026-000142.",
                              afirmacoes=[{"texto": "O curso tem 1200 horas.", "fontes": []},
                                          {"texto": "O prazo termina em 20/10/2026.", "fontes": [PRAZO_ANTIGO.trecho.id]}])
    assert rag._problemas(fato, [PRAZO_ANTIGO], caso=caso, modo="minuta") == []
    regra = rag.RespostaGerada(status="fundamentada", resposta="O prazo é de 1200 horas.",
                               afirmacoes=[{"texto": "O prazo é de 1200 horas.", "fontes": [PRAZO_ANTIGO.trecho.id]}])
    assert any("afirmação 1" in p for p in rag._problemas(regra, [PRAZO_ANTIGO], caso=caso, modo="minuta"))


def test_mudar_parametros_do_chunking_exige_reindexar(config, indice):
    config.dados["indice"]["chunking"][indice.chunking]["tamanho"] += 20
    with pytest.raises(IndiceIncompativel, match="chunking"):
        IndiceVetorial(config, indice.cliente)


def test_falha_do_provedor_na_reindexacao_mantem_os_trechos_antigos(config, acervo, indice):
    antes = [i for i, m in zip(*_tudo(indice)) if m["documento_id"] == "DOC-05"]
    caminho = config.caminho("acervo") / "doc-05.txt"
    caminho.write_text(caminho.read_text(encoding="utf-8") + "\nNovo parágrafo.", encoding="utf-8")
    erro = type("APIConnectionError", (Exception,), {})("sem rede")
    quebrado = IndiceVetorial(config, ClienteLLM(config, chave="c", sdk=falsos.SDKFalso(erro=erro)))
    from src.llm_client import ServicoIndisponivel

    with pytest.raises(ServicoIndisponivel):
        quebrado.indexar(acervo["DOC-05"])
    assert [i for i, m in zip(*_tudo(indice)) if m["documento_id"] == "DOC-05"] == antes


def test_indice_persiste_em_outro_processo(config, indice):
    import subprocess
    import sys

    codigo = (
        "import json, sys; from pathlib import Path; from src.config import Config; "
        "from src.embeddings import IndiceVetorial; "
        "i = IndiceVetorial(Config(json.loads(sys.argv[2]), Path(sys.argv[1])), None); "
        "print(json.dumps([i.contar(), i.info()['versao_indice']]))"
    )
    saida = subprocess.run([sys.executable, "-c", codigo, str(config.raiz), json.dumps(config.dados)],
                           cwd=RAIZ, capture_output=True, text=True, check=True).stdout
    assert json.loads(saida.strip().splitlines()[-1]) == [indice.contar(), indice.info()["versao_indice"]]


def test_exclusao_conta_so_quem_cita_tira_o_texto_e_tolera_minuta_ilegivel(config, acervo, indice, auditoria):
    do_doc = TrechoRecuperado(trecho=exemplos.trecho(id="DOC-05:x:B:0", documento_id="DOC-05", texto="Horário fictício."), distancia=0.1)
    citada = exemplos.resposta_rag(trechos=[do_doc], afirmacoes=[{"texto": "Atende de dia.", "fontes": ["DOC-05:x:B:0"]}])
    so_recuperada = exemplos.resposta_rag(trechos=[do_doc, TrechoRecuperado(trecho=exemplos.trecho(), distancia=0.2)])
    revisao.gravar_registro_rag(config, exemplos.registro("aprovada", id_execucao="citada000001", resposta=citada))
    revisao.gravar_registro_rag(config, exemplos.registro("pendente", id_execucao="recuperada01", resposta=so_recuperada))
    (config.caminho("minutas_rag") / "quebrada.json").write_text("{", encoding="utf-8")
    removido = ingestion.excluir_documento(config, "DOC-05", indice=indice, auditoria=auditoria)
    assert removido["minutas_que_citam"] == 1 and removido["minutas_com_texto_removido"] == 2
    assert removido["minutas_ilegiveis"] == ["resultados/minutas_rag/quebrada.json"]
    registro = revisao.ler_registro_rag(config, "citada000001")
    assert registro.status == "aprovada" and registro.resposta.afirmacoes[0].fontes == ["DOC-05:x:B:0"]
    assert registro.resposta.trechos[0].trecho.texto.startswith("[texto removido: DOC-05")
    assert "Horário fictício" not in (config.caminho("minutas_rag") / "recuperada01.json").read_text(encoding="utf-8")
    assert auditoria.eventos(etapa="acervo_exclusao")


def test_trecho_bloqueado_nao_chega_ao_modelo(config, indice, auditoria, partes, monkeypatch):
    todos_no_top_k(config, indice)
    monkeypatch.setattr(guardrails, "verificar_trechos", lambda trechos, *, config: [
        DecisaoGuardrail(decisao="bloquear" if t.trecho.documento_id == "DOC-06" else "permitir", camada="trechos",
                         regra="instrucao_no_acervo", motivo="teste") for t in trechos])
    cliente, sdk = gerador(config, fundamentada(id_de(indice, "DOC-02")))
    registro = processar(config, indice, auditoria, cliente)
    assert registro.status == "pendente" and registro.resposta.necessita_revisao
    assert "DOC-06" not in sdk.operacoes('responses.create')[0]["input"]
    assert all(t.trecho.documento_id != "DOC-06" for t in registro.resposta.trechos)
    [evento] = auditoria.eventos(id_execucao=registro.id_execucao, etapa="d2_recuperacao_geracao")
    assert any(i.startswith("DOC-06") for i in evento["extra"]["ids_recuperados"])
    assert not any(i.startswith("DOC-06") for i in evento["extra"]["ids_enviados_ao_modelo"])


def test_falha_do_provedor_no_meio_da_etapa_guarda_tokens_na_auditoria(config, indice, auditoria, partes, monkeypatch):
    from src.llm_client import RespostaLLM, ServicoIndisponivel

    def falha(texto, **_):
        erro = ServicoIndisponivel()
        erro.respostas = [RespostaLLM(texto="{}", modelo="gpt-6.1-terra", duracao_s=0.1, tokens_entrada=70,
                                      tokens_saida=5, custo_estimado_usd=0.0001)]
        erro.prompt = None
        raise erro

    monkeypatch.setattr(nlp, "extrair_solicitacao", falha)
    cliente, _ = gerador(config)
    with pytest.raises(ServicoIndisponivel):
        processar(config, indice, auditoria, cliente)
    [evento] = auditoria.eventos(etapa="d2_extracao")
    assert evento["tokens_entrada"] == 70 and evento["erro"].startswith("ServicoIndisponivel")


def test_consulta_vira_registro_pendente_auditado_com_modelo(config, indice, auditoria, partes):
    todos_no_top_k(config, indice)
    cliente, _ = gerador(config, fundamentada(id_de(indice, "DOC-02")))
    registro = fluxo_rag.consultar("Quais documentos levo na matrícula? CPF 123.456.789-00", config=config,
                                   cliente=cliente, indice=indice, auditoria=auditoria)
    assert registro.status == "pendente" and registro.origem == "consulta" and registro.solicitacao is None
    assert "123.456.789-00" not in registro.entrada and revisao.ler_registro_rag(config, registro.id_execucao) == registro
    assert [e["etapa"] for e in auditoria.eventos(id_execucao=registro.id_execucao)] == [
        "d2_entrada", "d2_recuperacao_geracao", "d2_registro"]
    assert fluxo_rag.modelo_da_minuta(auditoria, registro.id_execucao) == config.perfil_geracao()["modelo"]


def test_caso_de_audio_do_desafio_1_entra_no_mesmo_fluxo_e_marca_incerteza(config, indice, auditoria, partes, monkeypatch):
    from src import audio
    from src.tipos import TextoExtraido

    todos_no_top_k(config, indice)
    vistos = []

    def transcrever(arquivo, *, cliente, config):
        vistos.append(arquivo.modalidade)
        return TextoExtraido(texto_bruto="bruto", texto_revisado="Quero saber os documentos da matrícula.",
                             trechos_incertos=["2026-000142 — número pouco audível"])

    monkeypatch.setattr(audio, "transcrever", transcrever)
    cliente, _ = gerador(config, fundamentada(id_de(indice, "DOC-02")))
    registro = fluxo_rag.processar_caso("audio-01", config=config, cliente=cliente, indice=indice, auditoria=auditoria)
    assert vistos == ["audio"] and registro.origem == "audio-01" and registro.status == "pendente"
    assert registro.entrada == "Quero saber os documentos da matrícula." and registro.resposta.necessita_revisao
    assert any(d.regra == "transcricao_incerta" and d.decisao == "revisar" for d in registro.guardrails)
    etapas = [e["etapa"] for e in auditoria.eventos(id_execucao=registro.id_execucao)]
    assert etapas[0] == "d2_extracao_texto" and etapas[-1] == "d2_registro"


def test_consulta_pela_interface_mostra_passagens_marca_de_ia_e_decisao(app_indice, monkeypatch):
    monkeypatch.setattr(guardrails, "verificar_entrada", lambda texto, *, config: permitir("entrada"))
    monkeypatch.setattr(guardrails, "verificar_trechos", lambda trechos, *, config: [permitir("trechos") for _ in trechos])
    monkeypatch.setattr(guardrails, "verificar_saida", lambda resposta, *, config: permitir("saida"))
    monkeypatch.setattr(guardrails.ControleRecursos, "antes_da_chamada", lambda self: None)
    monkeypatch.setattr(guardrails.ControleRecursos, "registrar", lambda self, tokens: None)
    app = app_indice.run()
    app.sidebar.radio[0].set_value("Acervo e índice").run()
    clicar(app, "Indexar o acervo")
    app.sidebar.radio[0].set_value("Consulta ao acervo").run()
    app.text_input[0].input("Qual o valor da bolsa?").run()
    app.slider[0].set_value(1).run()
    clicar(app, "Responder com fontes")
    assert not app.exception and not app.error
    assert len(app.session_state['consulta'].resposta.trechos) == 1
    assert any("Texto gerado por IA" in c.value for c in app.caption)
    assert any(b.label == "Registrar decisão" for b in app.button)
    next(r for r in app.radio if r.label == 'Decisão').set_value('rejeitar')
    next(t for t in app.text_area if t.label == 'Justificativa').input('Conferência simulada da consulta.')
    next(t for t in app.text_input if t.label == 'Revisor').input('Operador fictício')
    clicar(app, 'Registrar decisão')
    assert not app.exception and app.session_state['consulta'].status == 'rejeitada'
    assert not any(b.label == 'Registrar decisão' for b in app.button)
