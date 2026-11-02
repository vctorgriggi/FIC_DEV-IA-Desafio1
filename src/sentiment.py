"""Classificação de sentimentos das avaliações de atendimento (RF22)."""

from __future__ import annotations

import json

from pydantic import ValidationError

from .config import Config
from .audit import Auditoria, Evento, novo_id
from .guardrails import ControleRecursos
from .entradas import ArquivoInvalido
from .llm_client import ClienteLLM, ErroLLM, RespostaMalformada, formato_json
from .privacidade import mascarar, ocultar_segredos
from .prompts import carregar_prompt, delimitar
from .schemas import AvaliacaoSentimento
from .tipos import Resultado

ARQUIVO_AVALIACOES = "avaliacoes.json"


def ler_avaliacoes(config: Config) -> list[dict]:
    """Avaliações de dados/avaliacoes/avaliacoes.json como [{"id", "texto"}], com ids únicos e texto não vazio."""
    caminho = config.caminho("avaliacoes") / ARQUIVO_AVALIACOES
    if not caminho.is_file():
        return []
    try:
        avaliacoes = json.loads(caminho.read_text(encoding="utf-8"))
    except json.JSONDecodeError as erro:
        raise ArquivoInvalido(f"{config.relativo(caminho)} não é JSON válido ({erro}).") from None
    if not isinstance(avaliacoes, list) or not all(
        isinstance(a, dict) and isinstance(a.get("id"), str) and a['id'].strip() and isinstance(a.get("texto"), str) and a["texto"].strip()
        for a in avaliacoes
    ):
        raise ArquivoInvalido(f"{config.relativo(caminho)} precisa ser uma lista de {{\"id\", \"texto\"}} preenchidos.")
    ids = [a["id"] for a in avaliacoes]
    if len(ids) != len(set(ids)):
        raise ArquivoInvalido(f"{config.relativo(caminho)} tem id de avaliação repetido.")
    return avaliacoes


def classificar(
    id_avaliacao: str, texto: str, *, cliente: ClienteLLM, config: Config, perfil: str | None = None
) -> Resultado[AvaliacaoSentimento]:
    """RF22 — parte: sentimentos.

    Esperado:
    - texto da avaliação dentro de prompts.delimitar, separado das instruções; saída restrita por
      llm_client.formato_json(AvaliacaoSentimento.model_json_schema(), "sentimento"), modelo do perfil;
    - polaridade em config["sentimentos"]["polaridades"]; mista, irônica ou sem contexto vira "indeterminada"
      ou pede revisão, segundo regra escrita no prompt e na documentação;
    - justificativa curta sobre o texto, nunca sobre a pessoa (sem personalidade, diagnóstico ou traço sensível).
    """
    if not id_avaliacao.strip() or not texto.strip():
        raise ValueError('ID e texto da avaliação são obrigatórios.')
    if len(texto) > config.dados['limites']['max_caracteres_solicitacao']:
        raise ValueError('Avaliação acima do limite de caracteres.')
    prompt = carregar_prompt(config, 'sentimento', 1)
    seguro, _ = mascarar(texto, config.dados['privacidade']['mascarar_antes_de_enviar'])
    seguro = ocultar_segredos(seguro, [])
    resposta = cliente.gerar(
        modelo=config.perfil_geracao(perfil)['modelo'], instrucao_sistema=prompt.texto,
        entrada=delimitar(json.dumps({'id': id_avaliacao, 'texto': seguro}, ensure_ascii=False), 'avaliacao'),
        formato_resposta=formato_json(AvaliacaoSentimento.model_json_schema(), 'sentimento'),
    )
    def recusar(mensagem):
        erro = RespostaMalformada(mensagem)
        erro.respostas, erro.prompt = [resposta], prompt
        raise erro

    try:
        valor = AvaliacaoSentimento.model_validate_json(resposta.texto)
    except ValidationError:
        recusar('Classificação de sentimento fora do esquema.')
    if valor.id != id_avaliacao or valor.polaridade not in config.dados['sentimentos']['polaridades']:
        recusar('ID ou polaridade da classificação inválidos.')
    if not valor.justificativa.strip() or len(valor.justificativa) > 500:
        recusar('Justificativa deve ser curta e preenchida.')
    if valor.polaridade == 'indeterminada':
        valor.necessita_revisao = True
    valor.justificativa = ocultar_segredos(mascarar(valor.justificativa,
        config.dados['privacidade']['mascarar_antes_de_enviar'])[0], [])
    return Resultado(valor, respostas=[resposta], prompt=prompt)


def classificar_lote(
    avaliacoes: list[dict], *, cliente: ClienteLLM, config: Config, perfil: str | None = None
) -> list[Resultado[AvaliacaoSentimento]]:
    """RF22 — parte: sentimentos.

    Esperado: `classificar` para cada avaliação de ler_avaliacoes; falha de uma avaliação fica registrada e não
    interrompe as outras; o laço mora aqui, não na interface.
    """
    resultados = []
    auditoria = Auditoria(config)
    for avaliacao in avaliacoes:
        falha = None
        try:
            resultado = classificar(avaliacao['id'], avaliacao['texto'],
                cliente=cliente.nova_execucao(ControleRecursos(config)), config=config, perfil=perfil)
        except (ErroLLM, ValueError) as erro:
            falha = type(erro).__name__
            resultado = Resultado(AvaliacaoSentimento(
                id=avaliacao['id'], polaridade='indeterminada', necessita_revisao=True,
                justificativa='Falha na classificação automática; requer revisão humana.', confianca_declarada=None,
            ), respostas=getattr(erro, 'respostas', []), prompt=getattr(erro, 'prompt', None))
        resultados.append(resultado)
        evento = Evento(id_execucao=novo_id(), caso_id=avaliacao['id'], etapa='sentimento',
            extra={'polaridade': resultado.valor.polaridade,
                   'necessita_revisao': resultado.valor.necessita_revisao,
                   'falha': falha is not None}, erro=falha,
            versao_prompt=resultado.prompt.identificador if resultado.prompt else None,
            hash_prompt=resultado.prompt.hash if resultado.prompt else None)
        if resultado.respostas:
            evento.com_resposta(resultado.respostas[-1])
        auditoria.registrar(evento)
    caminho = config.caminho('metricas') / 'sentimentos.json'
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps([r.valor.model_dump() for r in resultados], ensure_ascii=False, indent=2), encoding='utf-8')
    return resultados


def ler_resultados(config: Config) -> list[AvaliacaoSentimento]:
    """Último lote persistido; painel disponível após reiniciar e sem provedor."""
    caminho = config.caminho('metricas') / 'sentimentos.json'
    if not caminho.is_file():
        return []
    try:
        return [AvaliacaoSentimento.model_validate(a) for a in json.loads(caminho.read_text(encoding='utf-8'))]
    except (ValueError, TypeError):
        raise ArquivoInvalido('Resultados de sentimentos inválidos; execute a classificação novamente.') from None


def ler_gabarito(config: Config) -> dict[str, str]:
    caminho = config.caminho('gabaritos') / 'D2-sentimentos.json'
    if not caminho.is_file():
        return {}
    try:
        dados = json.loads(caminho.read_text(encoding='utf-8'))['avaliacoes']
        esperado = {a['id']: a['polaridade_esperada'] for a in dados}
        if len(esperado) != len(dados) or any(p not in config.dados['sentimentos']['polaridades'] for p in esperado.values()):
            raise ValueError()
        return esperado
    except (ValueError, KeyError, TypeError):
        raise ArquivoInvalido('Gabarito de sentimentos inválido.') from None
