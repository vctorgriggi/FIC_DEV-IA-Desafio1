"""RF16: guardrails locais conservadores; regras em documentacao/desafio-2/guardrails-sentimentos.md."""
from __future__ import annotations

from pathlib import Path
import re
import unicodedata

from .config import Config
from .llm_client import ErroLLM
from .privacidade import PADRAO_CHAVE_OPENAI, PADRAO_CREDENCIAL, PADROES_PESSOAIS
from .schemas import DecisaoGuardrail, RespostaRAG, TrechoRecuperado


def _normalizar(texto: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKD', texto.casefold()) if not unicodedata.combining(c))


_INJECAO = re.compile(
    r'(ignor\w*|desconsider\w*|esquec\w*).{0,60}(instruc|regr|prompt|orientac)|'
    r'(revel|mostr|exib|imprim|fornec|retorn).{0,60}(segredo|credencia|senha|chave|api.key|prompt.{0,10}sistema)|'
    r'(envie|enviar|envio|aprove|aprovar|aprovad[ao]).{0,50}(automatic|sem revis|sem aprov)|'
    r'(system\s*:|\[inst\]|<\|im_start\|>|voce agora e)|'
    r'ignore.{0,60}(instructions|rules)|reveal.{0,60}(secret|credential|password|api.key)|'
    r'send.{0,40}(automatically|without.review)', re.DOTALL)
_ABUSO = re.compile(r'\b(idiota|imbecil|incompetente|matar|ameaca|ameacar)\b')
_ESCOPO = re.compile(r'matricul|inscri|edital|curso|escol|aluno|estud|document|certific|historico|'
                     r'atendimento|secretari|protocolo|cancel|reclam|informac|seciteci|etec|vaga|prazo|selec|recurso|resultado')


def _decisao(camada, decisao, regra, motivo):
    return DecisaoGuardrail(camada=camada, decisao=decisao, regra=regra, motivo=motivo)


def _segredo(texto):
    return bool(PADRAO_CHAVE_OPENAI.search(texto) or PADRAO_CREDENCIAL.search(texto))


class LimiteExecucao(ErroLLM):
    mensagem_padrao = 'Limite de chamadas ou de tokens desta execução atingido (limites no config.json).'


def verificar_entrada(texto: str, *, config: Config) -> DecisaoGuardrail:
    if not texto.strip() or len(texto) > config.dados['limites']['max_caracteres_solicitacao']:
        return _decisao('entrada', 'bloquear', 'comprimento', 'Entrada vazia ou acima do limite de caracteres.')
    normalizado = _normalizar(texto)
    if _segredo(texto) or _INJECAO.search(normalizado):
        return _decisao('entrada', 'bloquear', 'instrucao_ou_segredo', 'Possível mudança de regras ou exposição de credenciais.')
    if _ABUSO.search(normalizado):
        return _decisao('entrada', 'revisar', 'moderacao', 'Linguagem potencialmente abusiva ou ameaça; conferir contexto.')
    if not _ESCOPO.search(normalizado):
        return _decisao('entrada', 'revisar', 'escopo', 'Escopo educacional ou administrativo não identificado pelas regras locais.')
    return _decisao('entrada', 'permitir', 'entrada_valida', 'Entrada aceita pelas regras locais.')


def verificar_arquivo(nome: str, tamanho_bytes: int, *, config: Config) -> DecisaoGuardrail:
    acervo = config.dados['acervo']
    if Path(nome).suffix.casefold() not in acervo['extensoes']:
        return _decisao('arquivo', 'bloquear', 'extensao', 'Extensão de arquivo não permitida.')
    if tamanho_bytes <= 0 or tamanho_bytes > acervo['tamanho_max_mb'] * 1024 * 1024:
        return _decisao('arquivo', 'bloquear', 'tamanho', 'Arquivo vazio ou acima do limite de tamanho.')
    return _decisao('arquivo', 'permitir', 'arquivo_valido', 'Extensão e tamanho permitidos; conteúdo depende da extração.')


def verificar_trechos(trechos: list[TrechoRecuperado], *, config: Config) -> list[DecisaoGuardrail]:
    decisoes = []
    for recuperado in trechos:
        texto = recuperado.trecho.texto
        suspeito = _segredo(texto) or _INJECAO.search(_normalizar(texto))
        decisoes.append(_decisao('trechos', 'revisar' if suspeito else 'permitir',
            'instrucao_embutida' if suspeito else 'conteudo_externo',
            'Trecho suspeito deve ser excluído do contexto de geração.' if suspeito else 'Trecho deve permanecer delimitado como dado externo.'))
    return decisoes


def verificar_saida(resposta: RespostaRAG, *, config: Config) -> DecisaoGuardrail:
    if not resposta.resposta.strip():
        return _decisao('saida', 'bloquear', 'resposta_vazia', 'Saída vazia não pode formar minuta.')
    ids = {t.trecho.id for t in resposta.trechos}
    if any(f not in ids for f in resposta.fontes()):
        return _decisao('saida', 'bloquear', 'citacao_invalida', 'Fonte citada não pertence aos trechos recuperados.')
    if resposta.status == 'fundamentada' and (not resposta.afirmacoes or any(not a.fontes for a in resposta.afirmacoes)):
        return _decisao('saida', 'bloquear', 'sem_fonte', 'Resposta fundamentada exige fonte em cada afirmação.')
    texto = '\n'.join([resposta.resposta, *(a.texto for a in resposta.afirmacoes)])
    if _segredo(texto) or any(p.search(texto) for p in PADROES_PESSOAIS.values()):
        return _decisao('saida', 'bloquear', 'dado_indevido', 'Saída contém possível credencial ou identificador pessoal.')
    sem_negacoes = re.sub(r'\b(?:nao|nunca)\s+(?:(?:foi|sera|esta|e|deve ser|pode ser)\s+)?enviad[ao]\b', '', _normalizar(texto))
    if re.search(r'(enviad[ao]|envio autorizado|aprovad[ao] automaticamente)', sem_negacoes):
        return _decisao('saida', 'bloquear', 'envio', 'Saída não pode autorizar envio ou declarar aprovação automática.')
    if resposta.necessita_revisao or resposta.status != 'fundamentada' or any(
        d.decisao != 'permitir' for d in verificar_trechos(resposta.trechos, config=config)
    ):
        return _decisao('saida', 'revisar', 'evidencia_insuficiente', 'Conferir evidência, conflito ou conteúdo suspeito antes de decidir.')
    return _decisao('saida', 'permitir', 'saida_validada', 'Citações válidas; minuta continua sujeita à decisão humana.')


class ControleRecursos:
    """Conta tentativas inclusive falhas; tokens desconhecidos não são estimados."""
    def __init__(self, config: Config):
        self.config = config
        self.chamadas = 0
        self.tokens = 0

    def antes_da_chamada(self) -> None:
        limites = self.config.dados['limites']
        if self.chamadas >= limites['max_chamadas_por_execucao'] or self.tokens >= limites['max_tokens_por_execucao']:
            raise LimiteExecucao()
        self.chamadas += 1

    def registrar(self, tokens: int | None) -> None:
        if tokens is not None:
            if tokens < 0:
                raise ValueError('Tokens não podem ser negativos.')
            self.tokens += tokens
