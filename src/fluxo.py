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
    STATUS_APROVADOS,
    RevisaoInvalida,
    confirmar_campos_criticos,
    gravar_metadados,
    hash_arquivo,
    ler_metadados,
)


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


def processar_caso(
    caso_id: str,
    *,
    config: Config,
    cliente: ClienteLLM,
    auditoria: Auditoria,
    confirmar: Callable[[dict, list[str]], tuple[dict, list[str]]] = confirmar_campos_criticos,
) -> dict:
    """Processa um caso do config.json até a minuta aguardando revisão; devolve os metadados."""
    caso = config.caso(caso_id)
    modalidade = caso["modalidade"]
    id_execucao = novo_id()
    base = {"id_execucao": id_execucao, "caso_id": caso_id, "modalidade": modalidade, "arquivo_origem": caso["arquivo"]}
    pasta = config.caminho("processados") / caso_id / id_execucao
    pasta.mkdir(parents=True, exist_ok=True)

    with _etapa(auditoria, base, "entrada") as evento:
        arquivo = validar_arquivo(config.raiz / caso["arquivo"], modalidade, config)
        evento.extra = {"sha256": arquivo.sha256, "tamanho_bytes": arquivo.tamanho_bytes, "mime_type": arquivo.mime_type}

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

    corrigidos: list[str] = []
    if modalidade != "texto":
        with _etapa(auditoria, base, "confirmacao_campos_criticos") as evento:
            campos, corrigidos = confirmar(campos, extraido.trechos_incertos)
            evento.decisao_humana = "corrigido" if corrigidos else "confirmado"
            evento.extra = {"campos_corrigidos": corrigidos, "trechos_incertos_exibidos": extraido.trechos_incertos}

    _gravar_json(
        pasta / "extracao.json",
        {
            "caso_id": caso_id,
            "id_execucao": id_execucao,
            "texto_original": texto,
            "campos": campos,
            "dados_mascarados_no_envio": mascarados,
            "campos_corrigidos_por_humano": corrigidos,
        },
    )

    with _etapa(auditoria, base, "geracao_minuta") as evento:
        minuta = gerar_minuta(campos, fontes=[caso["arquivo"]], cliente=cliente, config=config)
        arquivo_minuta = config.caminho("minutas") / f"{id_execucao}.md"
        arquivo_minuta.write_text(minuta.texto, encoding="utf-8")
        _anotar(evento, minuta.resposta, minuta.prompt)
        evento.saida = config.relativo(arquivo_minuta)

    metadados = {
        "id_execucao": id_execucao,
        "caso_id": caso_id,
        "modalidade": modalidade,
        "arquivo_origem": caso["arquivo"],
        "extracao": config.relativo(pasta / "extracao.json"),
        "arquivo_minuta": config.relativo(arquivo_minuta),
        "arquivo_renderizado": minuta.arquivo_renderizado,
        "campos_ausentes": minuta.campos_ausentes,
        "fontes": minuta.fontes,
        "gerada_em": agora_iso(),
        "status": AGUARDANDO,
    }
    gravar_metadados(config, metadados)
    return metadados


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
