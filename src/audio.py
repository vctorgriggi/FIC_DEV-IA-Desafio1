"""RF06/RF07: áudio local validado, chamadas só pelo ClienteLLM.

Revisão conservadora: apenas espaços/quebras, nunca correção factual por palpite.
A autorização oficial de TTS pertence a fluxo.sintetizar_minuta, não a esta primitiva.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import io
import json
import math
import re
import shutil
import subprocess
import wave
from pathlib import Path

from .config import Config
from .entradas import ArquivoEntrada, ArquivoInvalido, validar_arquivo
from .llm_client import ClienteLLM, RespostaMalformada, RespostaVazia, formato_json, ler_json
from .prompts import carregar_prompt
from .revisao import RevisaoInvalida
from .tipos import TextoExtraido

AVISO_LACUNAS = 'Os campos identificados como não localizado representam informações ausentes no documento.'
VERSAO_LOCUCAO = 'markdown_conservador_v1'
ESQUEMA_TRANSCRICAO = {
    'type': 'object',
    'properties': {
        'texto_bruto': {'type': 'string'},
        'idioma': {'type': 'string'},
        'trechos_incertos': {'type': 'array', 'items': {
            'type': 'object', 'properties': {'trecho': {'type': 'string'}, 'motivo': {'type': 'string'}},
            'required': ['trecho', 'motivo'],
        }},
    },
    'required': ['texto_bruto', 'idioma', 'trechos_incertos'],
}
FORMATOS = {'.mp3': {'mp3'}, '.wav': {'wav'}, '.m4a': {'mov', 'mp4', 'm4a'},
            '.ogg': {'ogg'}, '.flac': {'flac'}}


def gabarito_validado(gabarito: dict | None) -> bool:
    """Áudio só compara com referência humana explicitamente validada."""
    return (isinstance(gabarito, dict) and gabarito.get('validado_por_humano') is True
            and all(isinstance(gabarito.get(k), str) and gabarito[k].strip()
                    for k in ('texto_referencia', 'elaborado_por', 'elaborado_em'))
            and isinstance(gabarito.get('dados_criticos'), list)
            and all(isinstance(v, str) and v.strip() for v in gabarito['dados_criticos']))


def inspecionar_audio(caminho: Path, config: Config) -> dict:
    """ffprobe lê todos os frames; stderr de erro também reprova leitura parcial."""
    executavel = shutil.which('ffprobe')
    if executavel is None:
        raise ArquivoInvalido('ffprobe não encontrado. Instale FFmpeg e disponibilize ffprobe no PATH (Aula 05).')
    try:
        processo = subprocess.run(
            [executavel, '-v', 'error', '-count_frames', '-show_entries',
             'format=format_name,duration:stream=codec_type,codec_name,nb_read_frames',
             '-of', 'json', str(caminho.resolve())],
            capture_output=True, text=True, check=True,
            timeout=config.dados.get('audio', {}).get('timeout_inspecao_s', 30),
        )
        dados = json.loads(processo.stdout)
        duracao = float(dados['format']['duration'])
        formatos = set(dados['format']['format_name'].split(','))
        streams = dados['streams']
        audios = [s for s in streams if s.get('codec_type') == 'audio']
        if (processo.stderr.strip() or not math.isfinite(duracao) or duracao <= 0
                or not audios or any(int(s.get('nb_read_frames', 0)) <= 0 for s in audios)
                or not formatos.intersection(FORMATOS.get(caminho.suffix.lower(), set()))):
            raise ValueError
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError):
        # Não repassar stderr/caminhos/conteúdo potencialmente sensível do decodificador.
        raise ArquivoInvalido('Áudio inválido, corrompido, incompatível com a extensão ou inspeção excedeu o tempo limite.') from None
    return {'duracao_audio_s': duracao, 'medicao_duracao': 'ffprobe -count_frames',
            'formato_detectado': dados['format']['format_name'],
            'codecs': [s.get('codec_name', 'desconhecido') for s in audios]}


def revisar_transcricao(bruto: str) -> str:
    """Normaliza apresentação, preservando todas as palavras e números."""
    linhas = [re.sub(r'[^\S\n]+', ' ', l).strip() for l in bruto.splitlines()]
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(linhas)).strip()


def transcrever(arquivo: ArquivoEntrada, *, cliente: ClienteLLM, config: Config) -> TextoExtraido:
    arquivo_atual = validar_arquivo(arquivo.caminho, 'audio', config)
    if arquivo.modalidade != 'audio' or arquivo_atual.sha256 != arquivo.sha256:
        raise ArquivoInvalido('O arquivo de áudio mudou desde a validação ou possui modalidade incorreta.')
    info = inspecionar_audio(arquivo.caminho, config)
    conteudo_original = arquivo.ler_bytes()
    if hashlib.sha256(conteudo_original).hexdigest() != arquivo.sha256:
        raise ArquivoInvalido('O áudio mudou durante a inspeção. Valide e processe novamente.')
    tarefa = carregar_prompt(config, 'transcricao', 1)
    sistema = carregar_prompt(config, 'sistema_seguro', 1)
    entrada = [{'type': 'text', 'text': tarefa.texto},
               {'type': 'audio', 'data': base64.b64encode(conteudo_original).decode('ascii'),
                'mime_type': arquivo_atual.mime_type}]
    # Reserva para envelope, esquema, parâmetros e cabeçalhos; sem Files API implícita.
    tamanho = len(json.dumps({'input': entrada, 'system_instruction': sistema.texto,
                             'response_format': formato_json(ESQUEMA_TRANSCRICAO)},
                            ensure_ascii=False).encode('utf-8')) + 65536
    if tamanho > 20_000_000:
        raise ArquivoInvalido('Áudio excede o limite seguro de 20 MB da requisição inline. Use um arquivo menor; upload não implementado.')
    resposta = cliente.gerar(modelo=config.modelo('transcricao'), entrada=entrada,
                            instrucao_sistema=sistema.texto,
                            formato_resposta=formato_json(ESQUEMA_TRANSCRICAO))
    dados = ler_json(resposta)
    bruto, idioma, incertos = (dados.get(k) for k in ('texto_bruto', 'idioma', 'trechos_incertos'))
    if not isinstance(bruto, str) or not isinstance(idioma, str) or not idioma.strip() or not isinstance(incertos, list):
        raise RespostaMalformada('Transcrição fora do esquema esperado.')
    if not bruto.strip():
        raise RespostaVazia('Nenhuma fala transcrita. Confira se o áudio contém fala inteligível.')
    if any(not isinstance(i, dict) or not isinstance(i.get('trecho'), str)
           or not i['trecho'].strip() or not isinstance(i.get('motivo'), str)
           or not i['motivo'].strip() for i in incertos):
        raise RespostaMalformada('Trechos incertos fora do esquema esperado.')
    return TextoExtraido(
        texto_bruto=bruto, texto_revisado=revisar_transcricao(bruto),
        trechos_incertos=[f"{i['trecho']} — {i['motivo']}" for i in incertos],
        metadados={**info, 'idioma': idioma.strip(), 'modelo': resposta.modelo,
                   'duracao_requisicao_s': resposta.duracao_s, 'sha256_original': arquivo.sha256,
                   'revisao': 'espaços e quebras de linha; sem alteração de palavras',
                   'prompt_sistema': sistema.identificador, 'hash_prompt_sistema': sistema.hash},
        resposta=resposta, prompt=tarefa,
    )


def preparar_locucao(texto: str) -> str:
    """Remove só marcadores de apresentação; mantém rótulos, fontes e destinos.

    Não interpreta HTML, tabelas, código, escapes ou comandos vocais do TTS.
    Esses formatos precisam ser preparados e aprovados como texto simples.
    """
    if not isinstance(texto, str) or not texto.strip():
        raise RevisaoInvalida('A minuta não contém texto para locução.')
    if any(c in texto for c in ('<', '>', '|', '\\')) or '```' in texto or '~~~' in texto:
        raise RevisaoInvalida('Marcação complexa na minuta: prepare texto simples e submeta à revisão antes de sintetizar.')
    if 'não localizado' in texto.casefold() and AVISO_LACUNAS.casefold() not in texto.casefold():
        raise RevisaoInvalida('Inclua o aviso de informações ausentes na minuta e aprove novamente antes de sintetizar: ' + AVISO_LACUNAS)
    linhas = []
    for linha in texto.splitlines():
        if re.fullmatch(r'\s*(?:-{3,}|_{3,}|\*{3,})\s*', linha):
            continue
        linha = re.sub(r'^\s{0,3}#{1,6}\s+', '', linha)
        linha = re.sub(r'^\s*[-*+]\s+', '', linha)
        # Destinos continuam audíveis: não omitir fontes, links ou conteúdo aprovado.
        linha = re.sub(r'!?\[([^\[\]]+)\]\(([^()]+)\)', r'\1 (\2)', linha)
        linha = re.sub(r'(?<!\w)\*\*([^*\n]+)\*\*(?!\w)', r'\1', linha)
        linha = re.sub(r'(?<!\S)__([^_\n]+)__(?!\w)', r'\1', linha)
        linha = re.sub(r'`([^`\n]+)`', r'\1', linha)
        linha = re.sub(r'(?<!\w)\*([^*\n]+)\*(?!\w)', r'\1', linha)
        linhas.append(linha)
    resultado = revisar_transcricao('\n'.join(linhas))
    if not resultado:
        raise RevisaoInvalida('A minuta não contém texto para locução.')
    return resultado


def validar_wav(conteudo: bytes) -> dict:
    """Exige RIFF/WAVE PCM com frames completos, sem aceitar só cabeçalho."""
    try:
        if conteudo[:4] != b'RIFF' or conteudo[8:12] != b'WAVE':
            raise ValueError
        if int.from_bytes(conteudo[4:8], 'little') + 8 != len(conteudo):
            raise ValueError
        with wave.open(io.BytesIO(conteudo), 'rb') as leitor:
            canais, largura, taxa, frames, compressao, _ = leitor.getparams()
            if compressao != 'NONE' or canais < 1 or largura not in (1, 2, 3, 4) or taxa <= 0 or frames <= 0:
                raise ValueError
            dados = leitor.readframes(frames)
            if len(dados) != frames * canais * largura:
                raise ValueError
    except (wave.Error, EOFError, ValueError):
        raise RespostaMalformada('O provedor não retornou um WAV PCM válido e completo.') from None
    return {'duracao_audio_s': frames / taxa, 'taxa_amostragem_hz': taxa,
            'canais': canais, 'bits_por_amostra': largura * 8}


def sintetizar(texto_aprovado: str, destino: Path, *, cliente: ClienteLLM, config: Config) -> dict:
    """Primitiva TTS; produção oficial deve entrar por fluxo.sintetizar_minuta."""
    texto = preparar_locucao(texto_aprovado)
    if destino.suffix.lower() != '.wav' or destino.exists():
        raise RevisaoInvalida('O destino deve ser WAV novo; um áudio anterior não será sobrescrito.')
    opcoes = config.dados.get('audio', {})
    voz, estilo = opcoes.get('voz'), opcoes.get('estilo')
    if not all(isinstance(v, str) and v.strip() for v in (voz, estilo)):
        raise ArquivoInvalido('Configure audio.voz e audio.estilo com valores não vazios em config.json.')
    entrada = [{'type': 'user_input', 'content': [{'type': 'text', 'text': texto,
                'annotations': [{'type': 'speech_metadata', 'style': estilo}]}]}]
    resposta = cliente.gerar(modelo=config.modelo('tts'), entrada=entrada,
                            formato_resposta={'type': 'audio'},
                            parametros={'speech_config': [{'voice': voz}]}, saida='audio')
    saida = getattr(resposta.bruta, 'output_audio', None)
    dados = getattr(saida, 'data', None)
    if not dados:
        raise RespostaVazia('O provedor não retornou áudio inline para gravação.')
    try:
        conteudo = base64.b64decode(dados, validate=True)
    except (binascii.Error, ValueError, TypeError):
        raise RespostaMalformada('O áudio retornado não possui base64 válido.') from None
    formato = validar_wav(conteudo)
    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        # Modo exclusivo: nenhuma sobrescrita silenciosa de evidência anterior.
        with destino.open('xb') as arquivo:
            arquivo.write(conteudo)
    except OSError:
        raise ArquivoInvalido('Não foi possível salvar o arquivo WAV no destino configurado.') from None
    return {'modelo': resposta.modelo, 'voz': voz, 'estilo': estilo, 'formato': 'wav',
            'idioma_locucao': 'pt-BR', 'preparacao': VERSAO_LOCUCAO,
            'sha256_minuta': hashlib.sha256(texto_aprovado.encode('utf-8')).hexdigest(),
            'sha256_texto_falado': hashlib.sha256(texto.encode('utf-8')).hexdigest(),
            'sha256_audio': hashlib.sha256(conteudo).hexdigest(),
            'arquivo': config.relativo(destino), **formato,
            'duracao_requisicao_s': resposta.duracao_s,
            'tokens_entrada': resposta.tokens_entrada, 'tokens_saida': resposta.tokens_saida,
            'custo_estimado_usd': resposta.custo_estimado_usd, 'parametros': resposta.parametros}
