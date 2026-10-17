"""Validação dos arquivos de entrada (fluxo, etapa Entrada; RF06 e RF08)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from .config import Config

TIPOS_MIME = {
    ".txt": "text/plain",
    ".mp3": "audio/mp3",
    ".wav": "audio/wav",
    ".m4a": "audio/m4a",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


class ArquivoInvalido(ValueError):
    pass


@dataclass(frozen=True)
class ArquivoEntrada:
    caminho: Path
    modalidade: str
    extensao: str
    mime_type: str
    tamanho_bytes: int
    sha256: str

    def ler_bytes(self) -> bytes:
        return self.caminho.read_bytes()


def validar_arquivo(caminho: Path, modalidade: str, config: Config) -> ArquivoEntrada:
    regras = config.dados["entradas"].get(modalidade)
    if regras is None:
        raise ArquivoInvalido(f"Modalidade desconhecida: {modalidade}.")
    if not caminho.is_file():
        raise ArquivoInvalido(f"Arquivo não encontrado: {caminho}.")

    extensao = caminho.suffix.lower()
    if extensao not in regras["extensoes"]:
        permitidas = ", ".join(regras["extensoes"])
        raise ArquivoInvalido(f"Extensão {extensao or '(nenhuma)'} não aceita para {modalidade}. Aceitas: {permitidas}.")

    tamanho = caminho.stat().st_size
    if tamanho == 0:
        raise ArquivoInvalido(f"Arquivo vazio: {caminho.name}.")
    limite = regras["tamanho_max_mb"] * 1024 * 1024
    if tamanho > limite:
        raise ArquivoInvalido(f"{caminho.name} tem {tamanho / 1_048_576:.1f} MB; o limite para {modalidade} é {regras['tamanho_max_mb']} MB.")

    conteudo = caminho.read_bytes()
    if modalidade == "texto":
        try:
            conteudo.decode("utf-8")
        except UnicodeDecodeError:
            raise ArquivoInvalido(f"{caminho.name} não está em UTF-8.") from None
    return ArquivoEntrada(
        caminho=caminho,
        modalidade=modalidade,
        extensao=extensao,
        mime_type=TIPOS_MIME[extensao],
        tamanho_bytes=tamanho,
        sha256=hashlib.sha256(conteudo).hexdigest(),
    )
