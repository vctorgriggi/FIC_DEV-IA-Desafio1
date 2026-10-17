"""Transcrição (RF06) e síntese de voz (RF07)."""

from __future__ import annotations

from pathlib import Path

from .config import Config
from .entradas import ArquivoEntrada
from .llm_client import ClienteLLM
from .tipos import PendenteDeImplementacao, TextoExtraido


def transcrever(arquivo: ArquivoEntrada, *, cliente: ClienteLLM, config: Config) -> TextoExtraido:
    """RF06 — parte: áudio.

    Esperado: texto bruto preservado, versão revisada, trechos incertos e, em
    metadados, idioma, modelo e duração do áudio. A extensão e o tamanho já foram
    validados pelo fluxo (entradas.validar_arquivo).

    Formato aceito pela Interactions API (conferido no SDK google-genai 2.31.0):
    entrada=[{"type": "text", "text": <instrução>},
             {"type": "audio", "data": <base64 de arquivo.ler_bytes()>, "mime_type": arquivo.mime_type}]
    com modelo config.modelo("transcricao"). Requisição inline vai até 20 MB no
    total; acima disso, Files API (fonte: docs oficiais Gemini API, audio, out/2026).
    """
    raise PendenteDeImplementacao("RF06", "áudio")


def sintetizar(texto_aprovado: str, destino: Path, *, cliente: ClienteLLM, config: Config) -> dict:
    """RF07 — parte: áudio. Grava o áudio em `destino` e devolve as configurações usadas.

    O fluxo só chama esta função com minuta de status "aprovada". Campos
    "não localizado" não podem ser lidos sem aviso ao ouvinte.

    Formato (fonte: docs oficiais Gemini API, speech-generation, out/2026):
    modelo config.modelo("tts"), formato_resposta={"type": "audio"},
    parametros={"speech_config": [{"voice": "Kore"}]}, saida="audio".
    resposta.bruta.output_audio.data é base64 de um WAV 24 kHz mono 16 bits,
    pronto para gravar. O tom vai numa anotação speech_metadata com `style`; o
    português consta como idioma suportado.
    """
    raise PendenteDeImplementacao("RF07", "áudio")
