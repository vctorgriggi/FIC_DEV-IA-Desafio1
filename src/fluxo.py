"""Orquestração do fluxo mínimo (seção 8 do enunciado).

Entrada -> Extração -> Compreensão -> Geração -> Revisão; Acessibilidade e
Comunicação visual rodam depois, sob demanda. Cada etapa vira um evento na
auditoria, com erro quando falha.
"""

from __future__ import annotations

import json
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator

from . import audio, image_generation, vision
from .audit import Auditoria, Evento, agora_iso, novo_id
from .comparacao import comparar_com_gabarito
from .config import Config
from .entradas import ArquivoInvalido, validar_arquivo
from .extracao import extrair_campos, normalizar_extracao
from .llm_client import ClienteLLM, RespostaLLM
from .minuta import gerar_minuta
from .privacidade import mascarar
from .prompts import Prompt
from .revisao import (
    AGUARDANDO,
    CAMPOS_CRITICOS,
    STATUS_APROVADOS,
    RevisaoInvalida,
    confirmar_campos_criticos,
    gravar_metadados,
    hash_arquivo,
    ler_metadados,
)


ARQUIVO_ESTADO = "estado.json"
AGUARDANDO_CONFIRMACAO = "aguardando_confirmacao"
CONCLUIDO = "concluido"


@contextmanager
def _etapa(auditoria: Auditoria, base: dict, etapa: str) -> Iterator[Evento]:
    evento = Evento(**base, etapa=etapa)
    inicio = time.perf_counter()
    try:
        yield evento
    except BaseException as erro:
        evento.erro = f"{type(erro).__name__}: {erro}"
        raise
    finally:
        # Etapa sem chamada ao modelo (ou que falhou) registra o próprio tempo.
        if evento.duracao_s is None:
            evento.duracao_s = round(time.perf_counter() - inicio, 3)
        auditoria.registrar(evento)


def _anotar(evento: Evento, resposta: RespostaLLM | None, prompt: Prompt | None) -> None:
    if resposta is not None:
        evento.com_resposta(resposta)
    if prompt is not None:
        evento.versao_prompt = prompt.identificador
        evento.hash_prompt = prompt.hash


def _gravar_json(caminho: Path, dados: dict) -> None:
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


def _ler_gabarito(config: Config, caso: dict) -> dict | None:
    caminho = config.raiz / caso["gabarito"]
    if not caminho.is_file():
        return None
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except json.JSONDecodeError as erro:
        raise ArquivoInvalido(f"Gabarito {caso['gabarito']} não é JSON válido ({erro}).") from None


def preparar_caso(caso_id: str, *, config: Config, cliente: ClienteLLM, auditoria: Auditoria) -> dict:
    """Primeira fase: entrada, extração do texto, comparação com gabarito e compreensão.

    Grava estado.json na pasta da execução; concluir_caso continua dali, depois
    da confirmação humana (terminal ou interface).
    """
    caso = config.caso(caso_id)
    modalidade = caso["modalidade"]
    id_execucao = novo_id()
    base = {"id_execucao": id_execucao, "caso_id": caso_id, "modalidade": modalidade, "arquivo_origem": caso["arquivo"]}
    pasta = config.caminho("processados") / caso_id / id_execucao
    pasta.mkdir(parents=True, exist_ok=True)

    with _etapa(auditoria, base, "entrada") as evento:
        arquivo = validar_arquivo(config.raiz / caso["arquivo"], modalidade, config)
        evento.extra = {"sha256": arquivo.sha256, "tamanho_bytes": arquivo.tamanho_bytes, "mime_type": arquivo.mime_type}

    trechos_incertos: list[str] = []
    with _etapa(auditoria, base, "extracao_texto") as evento:
        if modalidade == "texto":
            texto = arquivo.caminho.read_text(encoding="utf-8")
        else:
            extrator = audio.transcrever if modalidade == "audio" else vision.extrair_texto
            extraido = extrator(arquivo, cliente=cliente, config=config)
            (pasta / "texto_bruto.txt").write_text(extraido.texto_bruto, encoding="utf-8")
            (pasta / "texto_revisado.txt").write_text(extraido.texto_revisado, encoding="utf-8")
            _gravar_json(pasta / "extracao_texto.json", {"trechos_incertos": extraido.trechos_incertos, "metadados": extraido.metadados})
            _anotar(evento, extraido.resposta, extraido.prompt)
            evento.saida = config.relativo(pasta)
            texto = extraido.texto_revisado
            trechos_incertos = extraido.trechos_incertos

    # RF06 e RF08: comparação com o gabarito, quando o caso já tem um.
    if modalidade != "texto" and (gabarito := _ler_gabarito(config, caso)) is not None:
        with _etapa(auditoria, base, "comparacao_gabarito") as evento:
            comparacao = comparar_com_gabarito(extraido.texto_bruto, extraido.texto_revisado, gabarito)
            if comparacao is None:
                evento.extra = {"aviso": "gabarito sem texto_referencia"}
            else:
                _gravar_json(pasta / "comparacao_gabarito.json", comparacao)
                evento.saida = config.relativo(pasta / "comparacao_gabarito.json")
                evento.extra = {
                    "similaridade_bruto": comparacao["bruto"]["similaridade"],
                    "similaridade_revisado": comparacao["revisado"]["similaridade"],
                    "dados_criticos_nao_encontrados": comparacao["dados_criticos"]["nao_encontrados"],
                }

    with _etapa(auditoria, base, "compreensao") as evento:
        enviado, mascarados = mascarar(texto, config.dados["privacidade"]["mascarar_antes_de_enviar"])
        resultado = extrair_campos(enviado, origem=caso["arquivo"], cliente=cliente, config=config)
        campos = normalizar_extracao(resultado.campos, config.dados["categorias"])
        _anotar(evento, resultado.resposta, resultado.prompt)
        evento.saida = config.relativo(pasta / "extracao.json")
        evento.extra = {"dados_mascarados": mascarados}

    estado = {
        **base,
        "texto_original": texto,
        "campos": campos,
        "dados_mascarados_no_envio": mascarados,
        "trechos_incertos": trechos_incertos,
        # RF06 e RF08: dados críticos de áudio e imagem passam por uma pessoa antes da minuta.
        "exige_confirmacao": modalidade != "texto",
        "preparado_em": agora_iso(),
        "status": AGUARDANDO_CONFIRMACAO,
    }
    _gravar_json(pasta / ARQUIVO_ESTADO, estado)
    return estado


def ler_estado(config: Config, id_execucao: str) -> tuple[dict, Path]:
    for caminho in config.caminho("processados").glob(f"*/{id_execucao}/{ARQUIVO_ESTADO}"):
        return json.loads(caminho.read_text(encoding="utf-8")), caminho.parent
    raise RevisaoInvalida(f"Nenhuma execução preparada com id {id_execucao}.")


def pendentes_de_confirmacao(config: Config) -> list[dict]:
    pendentes = []
    for caminho in sorted(config.caminho("processados").glob(f"*/*/{ARQUIVO_ESTADO}")):
        estado = json.loads(caminho.read_text(encoding="utf-8"))
        if estado["status"] == AGUARDANDO_CONFIRMACAO and estado["exige_confirmacao"]:
            pendentes.append(estado)
    return sorted(pendentes, key=lambda e: e["preparado_em"], reverse=True)


def concluir_caso(
    id_execucao: str,
    *,
    campos_confirmados: dict | None,
    revisor: str | None = None,
    config: Config,
    cliente: ClienteLLM,
    auditoria: Auditoria,
) -> dict:
    """Segunda fase: registra a confirmação humana (áudio e imagem) e gera a minuta."""
    estado, pasta = ler_estado(config, id_execucao)
    if estado["status"] != AGUARDANDO_CONFIRMACAO:
        raise RevisaoInvalida(f"A execução {id_execucao} já foi concluída.")
    base = {k: estado[k] for k in ("id_execucao", "caso_id", "modalidade", "arquivo_origem")}
    campos = dict(estado["campos"])
    corrigidos: list[str] = []

    if estado["exige_confirmacao"]:
        if campos_confirmados is None:
            raise RevisaoInvalida("Confirme os dados críticos antes de gerar a minuta.")
        with _etapa(auditoria, base, "confirmacao_campos_criticos") as evento:
            for campo in CAMPOS_CRITICOS:
                valor = str(campos_confirmados.get(campo) or "").strip()
                if valor and valor != campos.get(campo):
                    campos[campo] = valor
                    corrigidos.append(campo)
            evento.decisao_humana = "corrigido" if corrigidos else "confirmado"
            evento.revisor = revisor
            evento.extra = {"campos_corrigidos": corrigidos, "trechos_incertos_exibidos": estado["trechos_incertos"]}

    _gravar_json(
        pasta / "extracao.json",
        {
            "caso_id": estado["caso_id"],
            "id_execucao": id_execucao,
            "texto_original": estado["texto_original"],
            "campos": campos,
            "dados_mascarados_no_envio": estado["dados_mascarados_no_envio"],
            "campos_corrigidos_por_humano": corrigidos,
        },
    )

    with _etapa(auditoria, base, "geracao_minuta") as evento:
        minuta = gerar_minuta(campos, fontes=[estado["arquivo_origem"]], cliente=cliente, config=config)
        arquivo_minuta = config.caminho("minutas") / f"{id_execucao}.md"
        arquivo_minuta.write_text(minuta.texto, encoding="utf-8")
        _anotar(evento, minuta.resposta, minuta.prompt)
        evento.saida = config.relativo(arquivo_minuta)

    metadados = {
        **base,
        "extracao": config.relativo(pasta / "extracao.json"),
        "arquivo_minuta": config.relativo(arquivo_minuta),
        "arquivo_renderizado": minuta.arquivo_renderizado,
        "campos_ausentes": minuta.campos_ausentes,
        "fontes": minuta.fontes,
        "gerada_em": agora_iso(),
        "status": AGUARDANDO,
    }
    gravar_metadados(config, metadados)
    _gravar_json(pasta / ARQUIVO_ESTADO, {**estado, "status": CONCLUIDO})
    return metadados


def processar_caso(
    caso_id: str,
    *,
    config: Config,
    cliente: ClienteLLM,
    auditoria: Auditoria,
    confirmar: Callable[[dict, list[str]], tuple[dict, list[str]]] = confirmar_campos_criticos,
) -> dict:
    """As duas fases em sequência, com a confirmação pelo terminal; devolve os metadados da minuta."""
    estado = preparar_caso(caso_id, config=config, cliente=cliente, auditoria=auditoria)
    confirmados = None
    if estado["exige_confirmacao"]:
        confirmados, _ = confirmar(estado["campos"], estado["trechos_incertos"])
    return concluir_caso(
        estado["id_execucao"], campos_confirmados=confirmados, config=config, cliente=cliente, auditoria=auditoria
    )


def sintetizar_minuta(id_execucao: str, *, config: Config, cliente: ClienteLLM, auditoria: Auditoria) -> dict:
    """RF07: só minuta aprovada, e só se o texto não mudou desde a aprovação."""
    metadados = ler_metadados(config, id_execucao)
    if metadados["status"] not in STATUS_APROVADOS:
        raise RevisaoInvalida(f"Só minuta aprovada vira áudio (status atual: {metadados['status']}).")
    arquivo_minuta = config.raiz / metadados["arquivo_minuta"]
    if hash_arquivo(arquivo_minuta) != metadados["revisao"]["sha256_minuta"]:
        raise RevisaoInvalida("A minuta foi alterada depois da aprovação; gere e revise de novo.")

    base = {k: metadados[k] for k in ("id_execucao", "caso_id", "modalidade", "arquivo_origem")}
    destino = config.caminho("audios") / f"{id_execucao}.wav"
    with _etapa(auditoria, base, "sintese_voz") as evento:
        configuracao = audio.sintetizar(arquivo_minuta.read_text(encoding="utf-8"), destino, cliente=cliente, config=config)
        evento.modelo = config.modelo("tts")
        evento.parametros = configuracao
        evento.saida = config.relativo(destino)

    metadados["audio"] = config.relativo(destino)
    gravar_metadados(config, metadados)
    return metadados


def gerar_peca_visual(
    caso_id: str,
    especificacao: dict,
    *,
    imagem_base: Path | None,
    config: Config,
    cliente: ClienteLLM,
    auditoria: Auditoria,
) -> image_generation.PecaVisual:
    caso = config.caso(caso_id)
    id_execucao = novo_id()
    base = {"id_execucao": id_execucao, "caso_id": caso_id, "modalidade": caso["modalidade"], "arquivo_origem": caso["arquivo"]}
    destino = config.caminho("imagens") / f"{id_execucao}.png"
    with _etapa(auditoria, base, "comunicacao_visual") as evento:
        peca = image_generation.gerar_peca(especificacao, destino, imagem_base=imagem_base, cliente=cliente, config=config)
        _anotar(evento, peca.resposta, None)
        evento.saida = config.relativo(peca.caminho)
        # RF10: prompt, modelo, data e proveniência ficam ao lado da imagem.
        _gravar_json(
            destino.with_suffix(".json"),
            {
                "id_execucao": id_execucao,
                "caso_id": caso_id,
                "imagem": config.relativo(peca.caminho),
                "ilustracao_original": peca.ilustracao_original and config.relativo(peca.ilustracao_original),
                "prompt": peca.prompt,
                "especificacao": especificacao,
                "imagem_base": imagem_base and config.relativo(imagem_base),
                "modelo": peca.modelo,
                "data_geracao": peca.data_geracao,
                "nota_proveniencia": peca.nota_proveniencia,
                "status": AGUARDANDO,
            },
        )
        evento.extra = {"metadados": config.relativo(destino.with_suffix(".json"))}
    return peca
