"""Extração validada, regras de negócio e ficha de compreensão (RF14, RF15).

Reaproveita o fluxo de extração do Desafio 1 (extracao.py) e os prompts seguros;
o contrato de saída é schemas.SolicitacaoEstruturada, fonte única de categoria e entidades.
"""

from __future__ import annotations

from .config import Config
from .llm_client import ClienteLLM
from .schemas import FichaCompreensao, SolicitacaoEstruturada
from .tipos import PendenteDeImplementacao, Resultado


def extrair_solicitacao(
    texto: str, *, origem: str, cliente: ClienteLLM, config: Config, perfil: str | None = None
) -> Resultado[SolicitacaoEstruturada]:
    """RF14 — parte: NLP.

    Esperado:
    - modelo de config.perfil_geracao(perfil); texto já mascarado (privacidade.mascarar) dentro de prompts.delimitar;
    - saída restrita por esquema: llm_client.formato_json(SolicitacaoEstruturada.model_json_schema(), "solicitacao");
    - validar com SolicitacaoEstruturada.model_validate_json; se falhar, no máximo uma nova tentativa mostrando o
      erro ao modelo; inválida de novo, levantar llm_client.RespostaMalformada com o erro de validação;
    - ausência como null e em campos_ausentes; a interface mostra "não localizado";
    - Resultado com todas as respostas (uma ou duas) e o prompt usado.
    """
    raise PendenteDeImplementacao("RF14", "NLP")


def validar_regras(solicitacao: SolicitacaoEstruturada, texto_original: str, *, config: Config) -> list[str]:
    """RF14 — parte: NLP.

    Esperado: lista de problemas de regra de negócio (vazia se nenhum), que bloqueiam a minuta:
    data inexistente ou impossível, categoria fora de config["categorias"], protocolo ou nome que não aparece
    no texto original, campo marcado como ausente mas preenchido, e o contrário. Sem chamada ao modelo.
    """
    raise PendenteDeImplementacao("RF14", "NLP")


def comparar_sintatico_e_esquema(
    texto: str, *, origem: str, cliente: ClienteLLM, config: Config, perfil: str | None = None
) -> dict:
    """RF14 — parte: NLP.

    Esperado: no mesmo caso, uma saída pedida só como JSON e outra restrita por esquema; para cada uma, se o JSON
    é válido, e os erros de esquema (pydantic.ValidationError.errors()) separados em chaves extras
    ("extra_forbidden"), tipo incorreto (tipos terminados em "_type" ou "_parsing") e campo obrigatório ausente
    ("missing").
    """
    raise PendenteDeImplementacao("RF14", "NLP")


def compreender(
    texto: str,
    solicitacao: SolicitacaoEstruturada,
    *,
    origem: str,
    cliente: ClienteLLM,
    config: Config,
    perfil: str | None = None,
) -> Resultado[FichaCompreensao]:
    """RF15 — parte: NLP.

    Esperado: resumo de até 100 palavras sem dado inventado, e as inferências separadas do que está escrito,
    cada uma com justificativa. Categoria e entidades ficam na `solicitacao`; a ficha mostrada na interface
    é solicitação + ficha.
    """
    raise PendenteDeImplementacao("RF15", "NLP")
