import json
import shutil

import pytest

from src.audit import Auditoria
from src.config import RAIZ, Config


@pytest.fixture
def config(tmp_path) -> Config:
    """config.json real, com raiz num diretório temporário e entradas fictícias mínimas."""
    dados = json.loads((RAIZ / "config.json").read_text(encoding="utf-8"))
    shutil.copytree(RAIZ / "prompts", tmp_path / "prompts")
    originais = tmp_path / "dados" / "originais"
    originais.mkdir(parents=True)
    (originais / "entrada_texto.txt").write_text(
        "Protocolo: 2026-000001\nData: 01/10/2026\nCPF 123.456.789-00, e-mail fulano@exemplo.com\nPedido fictício.",
        encoding="utf-8",
    )
    (originais / "entrada_audio.mp3").write_bytes(b"ID3 audio ficticio")
    (originais / "entrada_pdf-imagem.pdf").write_bytes(b"%PDF-1.5 documento ficticio")
    (tmp_path / "dados" / "processados").mkdir()
    for pasta in ("minutas", "audios", "imagens", "logs"):
        (tmp_path / "resultados" / pasta).mkdir(parents=True)
    return Config(dados=dados, raiz=tmp_path)


@pytest.fixture
def auditoria(config) -> Auditoria:
    return Auditoria(config, segredos=[])
