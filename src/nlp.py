"""Extração validada, regras de negócio e ficha de compreensão (RF14, RF15).

Reaproveita o fluxo de extração do Desafio 1 (extracao.py) e os prompts seguros;
o contrato de saída é schemas.SolicitacaoEstruturada.
"""

from __future__ import annotations

from .config import Config
from .llm_client import ClienteLLM
from .schemas import FichaCompreensao, SolicitacaoEstruturada
from .tipos import PendenteDeImplementacao


def extrair_solicitacao(texto: str, *, origem: str, cliente: ClienteLLM, config: Config) -> SolicitacaoEstruturada:
    """RF14 — parte: NLP.

    Esperado:
    - saída restrita por esquema (llm_client.formato_json) a partir de SolicitacaoEstruturada;
    - validar o JSON com o modelo Pydantic; se falhar, no máximo uma nova tentativa com o erro; inválida de novo, rejeitar;
    - texto já mascarado (privacidade.mascarar) e dentro de prompts.delimitar;
    - ausência como null e em campos_ausentes; a interface mostra "não localizado".
    """
    raise PendenteDeImplementacao("RF14", "NLP")


def validar_regras(solicitacao: SolicitacaoEstruturada, texto_original: str, *, config: Config) -> list[str]:
    """RF14 — parte: NLP.

    Esperado: lista de problemas de regra de negócio (vazia se nenhum), que bloqueiam a minuta:
    data inexistente ou impossível, categoria fora de config["categorias"], protocolo ou nome que não aparece
    no texto original, campo marcado como ausente mas preenchido, e o contrário.
    """
    raise PendenteDeImplementacao("RF14", "NLP")


def comparar_sintatico_e_esquema(texto: str, *, origem: str, cliente: ClienteLLM, config: Config) -> dict:
    """RF14 — parte: NLP.

    Esperado: no mesmo caso, uma saída pedida só como JSON e outra restrita por esquema; para cada uma, se o JSON
    é válido, e os erros de esquema separados em chaves extras, tipo incorreto e campo obrigatório ausente.
    """
    raise PendenteDeImplementacao("RF14", "NLP")


def compreender(texto: str, *, origem: str, cliente: ClienteLLM, config: Config) -> FichaCompreensao:
    """RF15 — parte: NLP.

    Esperado: resumo de até 100 palavras sem dado inventado, categoria documentada (incluindo "outros" ou
    "revisão"), entidades literais do texto e, separadas, as inferências com justificativa.
    """
    raise PendenteDeImplementacao("RF15", "NLP")
