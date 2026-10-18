import json

import pytest

from src import fluxo
from src.extracao import ResultadoExtracao
from src.minuta import Minuta
from src.image_generation import PecaVisual
from src.revisao import (
    RevisaoInvalida,
    confirmar_campos_criticos,
    ler_metadados,
    perguntar_decisao,
    registrar_decisao,
    resumo_revisoes,
)
from src.tipos import PendenteDeImplementacao, TextoExtraido

CAMPOS = {"protocolo": "2026-000001", "data": "01/10/2026", "solicitante": "Pessoa Fictícia", "assunto": "Matrícula", "pedido": "Documentos", "categoria": "x"}


@pytest.fixture
def partes_falsas(monkeypatch):
    """Substitui as partes ainda pendentes; registra o texto que seguiria ao provedor."""
    enviados = []

    def extrair(texto, **_):
        enviados.append(texto)
        return ResultadoExtracao(campos=dict(CAMPOS))

    def minuta(campos, *, fontes, **_):
        return Minuta(texto=f"Minuta do protocolo {campos['protocolo']}", campos_ausentes=[], fontes=fontes)

    monkeypatch.setattr(fluxo, "extrair_campos", extrair)
    monkeypatch.setattr(fluxo, "gerar_minuta", minuta)
    return enviados


def etapas(auditoria, id_execucao):
    return [e["etapa"] for e in auditoria.eventos(id_execucao=id_execucao)]


def test_texto_chega_a_minuta_aguardando_revisao(config, auditoria, partes_falsas):
    meta = fluxo.processar_caso("texto-01", config=config, cliente=None, auditoria=auditoria)

    assert meta["status"] == "aguardando_revisao"
    assert (config.raiz / meta["arquivo_minuta"]).read_text(encoding="utf-8") == "Minuta do protocolo 2026-000001"
    eventos = auditoria.eventos(id_execucao=meta["id_execucao"])
    assert [e["etapa"] for e in eventos] == ["entrada", "extracao_texto", "compreensao", "geracao_minuta"]
    assert all(e["duracao_s"] is not None for e in eventos)

    # RF12: provedor recebe o texto mascarado; RF05: o original fica preservado localmente.
    assert "123.456.789-00" not in partes_falsas[0] and "fulano@exemplo.com" not in partes_falsas[0]
    extracao = json.loads((config.raiz / meta["extracao"]).read_text(encoding="utf-8"))
    assert "123.456.789-00" in extracao["texto_original"]
    assert extracao["dados_mascarados_no_envio"] == {"cpf": 1, "email": 1}


def test_audio_passa_por_confirmacao_humana_antes_da_minuta(config, auditoria, partes_falsas, monkeypatch):
    monkeypatch.setattr(
        fluxo.audio,
        "transcrever",
        lambda arquivo, **_: TextoExtraido(texto_bruto="bruto", texto_revisado="revisado", trechos_incertos=["0001 — ruído"]),
    )
    exibidos = []

    def confirmar(campos, trechos):
        exibidos.extend(trechos)
        return {**campos, "protocolo": "2026-000002"}, ["protocolo"]

    meta = fluxo.processar_caso(
        "audio-01",
        config=config,
        cliente=None,
        auditoria=auditoria,
        confirmar=confirmar,
    )
    assert exibidos == ["0001 — ruído"]
    assert etapas(auditoria, meta["id_execucao"]) == [
        "entrada", "extracao_texto", "compreensao", "confirmacao_campos_criticos", "geracao_minuta"
    ]
    assert "2026-000002" in (config.raiz / meta["arquivo_minuta"]).read_text(encoding="utf-8")
    pasta = config.raiz / meta["extracao"].rsplit("/", 1)[0]
    assert (pasta / "texto_bruto.txt").read_text(encoding="utf-8") == "bruto"


def test_parte_pendente_fica_registrada_como_erro(config, auditoria):
    with pytest.raises(PendenteDeImplementacao, match="RF05"):
        fluxo.processar_caso("texto-01", config=config, cliente=None, auditoria=auditoria)
    ultimo = auditoria.eventos()[-1]
    assert ultimo["etapa"] == "compreensao"
    assert "RF05" in ultimo["erro"]


def test_revisao_exige_justificativa_e_so_acontece_uma_vez(config, auditoria, partes_falsas):
    meta = fluxo.processar_caso("texto-01", config=config, cliente=None, auditoria=auditoria)
    id_execucao = meta["id_execucao"]
    with pytest.raises(RevisaoInvalida, match="justificativa"):
        registrar_decisao(config, auditoria, id_execucao, decisao="aprovar", justificativa=" ", revisor="Servidor A")

    registrar_decisao(config, auditoria, id_execucao, decisao="rejeitar", justificativa="Tom inadequado", revisor="Servidor A")
    assert ler_metadados(config, id_execucao)["status"] == "rejeitada"
    assert auditoria.eventos(etapa="revisao")[0]["decisao_humana"] == "rejeitar"
    with pytest.raises(RevisaoInvalida, match="já foi revisada"):
        registrar_decisao(config, auditoria, id_execucao, decisao="aprovar", justificativa="ok", revisor="Servidor A")


def test_audio_so_de_minuta_aprovada_e_inalterada(config, auditoria, partes_falsas, monkeypatch):
    sintetizados = []

    def sintetizar(texto, destino, **_):
        sintetizados.append(texto)
        return {"voz": "Kore"}

    monkeypatch.setattr(fluxo.audio, "sintetizar", sintetizar)
    meta = fluxo.processar_caso("texto-01", config=config, cliente=None, auditoria=auditoria)
    id_execucao = meta["id_execucao"]

    with pytest.raises(RevisaoInvalida, match="aprovada"):
        fluxo.sintetizar_minuta(id_execucao, config=config, cliente=None, auditoria=auditoria)

    registrar_decisao(config, auditoria, id_execucao, decisao="aprovar", justificativa="Conferida", revisor="Servidor A")
    arquivo_minuta = config.raiz / meta["arquivo_minuta"]
    original = arquivo_minuta.read_text(encoding="utf-8")
    arquivo_minuta.write_text(original + " acréscimo", encoding="utf-8")
    with pytest.raises(RevisaoInvalida, match="alterada"):
        fluxo.sintetizar_minuta(id_execucao, config=config, cliente=None, auditoria=auditoria)

    arquivo_minuta.write_text(original, encoding="utf-8")
    meta = fluxo.sintetizar_minuta(id_execucao, config=config, cliente=None, auditoria=auditoria)
    assert sintetizados == [original]
    assert meta["audio"] == f"resultados/audios/{id_execucao}.wav"


def test_perguntas_do_terminal_repetem_ate_resposta_valida():
    respostas = iter(["x", "a", "", "Dados conferidos", "Servidor A"])
    assert perguntar_decisao(lambda _: next(respostas)) == ("aprovar", "Dados conferidos", "Servidor A")

    respostas = iter(["", "2026-000009", ""])
    perguntas, exibido = [], []

    def perguntar(pergunta):
        perguntas.append(pergunta)
        return next(respostas)

    campos, corrigidos = confirmar_campos_criticos(
        {**CAMPOS, "protocolo": "2024-000001"},
        ["2024 — dígito rasurado"],
        perguntar=perguntar,
        mostrar=exibido.append,
    )
    assert "  - 2024 — dígito rasurado" in exibido
    assert "ATENÇÃO" in perguntas[0] and "ATENÇÃO" not in perguntas[1]
    assert corrigidos == ["data"]
    assert campos["data"] == "2026-000009" and campos["protocolo"] == "2024-000001"


def test_taxa_de_aprovacao(config, auditoria, partes_falsas):
    assert resumo_revisoes(config)["taxa_aprovacao_sem_correcao"] is None
    decisoes = ["aprovar", "aprovar_com_correcao", "rejeitar", None]
    for decisao in decisoes:
        meta = fluxo.processar_caso("texto-01", config=config, cliente=None, auditoria=auditoria)
        if decisao:
            registrar_decisao(config, auditoria, meta["id_execucao"], decisao=decisao, justificativa="j", revisor="r")
    resumo = resumo_revisoes(config)
    assert resumo["revisadas"] == 3
    assert resumo["por_status"]["aguardando_revisao"] == 1
    assert resumo["taxa_aprovacao_sem_correcao"] == pytest.approx(1 / 3, abs=1e-3)
    assert resumo["taxa_aprovacao_com_correcao"] == pytest.approx(2 / 3, abs=1e-3)


def test_peca_visual_guarda_prompt_modelo_data_e_proveniencia(config, auditoria, monkeypatch):
    def gerar(especificacao, destino, **_):
        destino.write_bytes(b"png")
        return PecaVisual(
            caminho=destino, prompt="cartaz", modelo="gemini-3.1-flash-lite-image",
            data_geracao="2026-10-17", nota_proveniencia="Imagem gerada por IA",
        )

    monkeypatch.setattr(fluxo.image_generation, "gerar_peca", gerar)
    peca = fluxo.gerar_peca_visual(
        "texto-01", {"sujeito": "cartaz"}, imagem_base=None, config=config, cliente=None, auditoria=auditoria
    )
    metadados = json.loads(peca.caminho.with_suffix(".json").read_text(encoding="utf-8"))
    assert metadados["prompt"] == "cartaz"
    assert metadados["modelo"] == "gemini-3.1-flash-lite-image"
    assert metadados["data_geracao"] == "2026-10-17"
    assert metadados["nota_proveniencia"] == "Imagem gerada por IA"
    assert metadados["especificacao"] == {"sujeito": "cartaz"}
