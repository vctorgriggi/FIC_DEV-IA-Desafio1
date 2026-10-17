"""Geração ou edição da peça visual de orientação (RF10)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import Config
from .llm_client import ClienteLLM, RespostaLLM
from .tipos import PendenteDeImplementacao


@dataclass
class PecaVisual:
    caminho: Path
    prompt: str
    modelo: str
    data_geracao: str
    nota_proveniencia: str
    resposta: RespostaLLM | None = None


def gerar_peca(
    especificacao: dict,
    destino: Path,
    *,
    imagem_base: Path | None,
    cliente: ClienteLLM,
    config: Config,
) -> PecaVisual:
    """RF10 — parte: imagem.

    `especificacao` traz sujeito, composição, estilo, iluminação, proporção e
    restrições. Com `imagem_base`, edita a imagem; sem ela, gera uma nova. A peça
    sai identificada como gerada/editada por IA, com nota de proveniência.

    Formato (fonte: docs oficiais Gemini API, image-generation, out/2026):
    modelo config.modelo("imagem"), formato_resposta={"type": "image", "aspect_ratio": "4:5"},
    saida="imagem"; resposta.bruta.output_image.data é base64. Para editar,
    inclua {"type": "image", "data": <base64>, "mime_type": "image/png"} na entrada.
    As imagens geradas levam marca d'água SynthID. Geração de imagem não tem
    cota gratuita: cada chamada é cobrada (preço por imagem em config.json).
    """
    raise PendenteDeImplementacao("RF10", "imagem")
