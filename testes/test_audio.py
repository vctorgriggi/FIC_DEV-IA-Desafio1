"""Testes simulados RF06/RF07: SDK falso e ffprobe mockado, nunca inferência real.

Compatíveis com pytest e também com unittest da biblioteca padrão.
"""
import base64
import copy
import io
import json
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

from src import audio, fluxo
from src.audit import Auditoria
from src.config import Config, RAIZ
from src.comparacao import comparar_com_gabarito
from src.entradas import ArquivoInvalido, validar_arquivo
from src.llm_client import ClienteLLM, RespostaMalformada, RespostaVazia, ServicoIndisponivel
from src.revisao import registrar_decisao, RevisaoInvalida, ler_metadados
from testes.falsos import SDKFalso, interacao


def wav_teste():
    destino = io.BytesIO()
    with wave.open(destino, 'wb') as w:
        w.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
        w.writeframes(b'\x00\x01' * 2400)
    return destino.getvalue()


def probe(duracao='0.1', formato='wav', frames='2400', stderr=''):
    return SimpleNamespace(stdout=json.dumps({'format': {'duration': duracao, 'format_name': formato},
        'streams': [{'codec_type': 'audio', 'codec_name': 'pcm_s16le', 'nb_read_frames': frames}]}), stderr=stderr)


class AudioSimuladoTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.raiz = Path(self.tmp.name)
        dados = json.loads((RAIZ / 'config.json').read_text())
        self.config = Config(copy.deepcopy(dados), self.raiz)
        for nome in dados['caminhos'].values():
            (self.raiz / nome).mkdir(parents=True, exist_ok=True)
        for p in (RAIZ / 'prompts').glob('*'):
            (self.raiz / 'prompts' / p.name).write_bytes(p.read_bytes())
        self.entrada = self.raiz / 'dados/originais/voz.wav'
        self.entrada.write_bytes(wav_teste())
        self.config.caso('audio-01')['arquivo'] = 'dados/originais/voz.wav'
        self.auditoria = Auditoria(self.config, segredos=[])
        self.sdk = SDKFalso()
        self.cliente = ClienteLLM(self.config, chave='credencial-ficticia', sdk=self.sdk)

    def transcrever(self, dados=None):
        if dados is None:
            dados = {'texto_bruto': '  Nome  Fictício\nProtocolo 2026-000001, data 01/10/2026.\n',
                     'idioma': 'pt', 'trechos_incertos': [{'trecho': 'Fictício', 'motivo': 'ruído'}]}
        self.sdk._resposta = interacao(texto=json.dumps(dados, ensure_ascii=False))
        return audio.transcrever(validar_arquivo(self.entrada, 'audio', self.config), cliente=self.cliente, config=self.config)

    def sintetizar(self, texto='Comunicado fictício.'):
        return audio.sintetizar(texto, self.raiz / 'resultados/audios/voz.wav', cliente=self.cliente, config=self.config)

    def test_inspecao_duracao_e_argumentos(self):
        with patch('src.audio.shutil.which', return_value='/ffprobe'), patch('src.audio.subprocess.run', return_value=probe()) as executar:
            info = audio.inspecionar_audio(self.entrada, self.config)
        self.assertEqual(info['duracao_audio_s'], 0.1)
        self.assertIn('-count_frames', executar.call_args.args[0])
        self.assertEqual(executar.call_args.kwargs['timeout'], 30)

    def test_ffprobe_ausente(self):
        with patch('src.audio.shutil.which', return_value=None):
            with self.assertRaisesRegex(ArquivoInvalido, 'ffprobe não encontrado'):
                self.transcrever()
        self.assertFalse(self.sdk.chamadas)

    def test_ffprobe_falhas(self):
        for erro in (FileNotFoundError(), subprocess.TimeoutExpired('probe', 30), subprocess.CalledProcessError(1, 'probe')):
            with self.subTest(erro=type(erro).__name__), patch('src.audio.shutil.which', return_value='/probe'), patch('src.audio.subprocess.run', side_effect=erro):
                with self.assertRaises(ArquivoInvalido):
                    self.transcrever()
        self.assertFalse(self.sdk.chamadas)

    def test_ffprobe_invalido_ou_corrompido(self):
        casos = [probe('nan'), probe('0'), probe('-1'), probe(formato='mp3'), probe(frames='0'),
                 probe(stderr='erro de decodificação com dado privado'), SimpleNamespace(stdout='{}', stderr=''),
                 SimpleNamespace(stdout='não json', stderr='')]
        for caso in casos:
            with self.subTest(caso=caso.stdout), patch('src.audio.shutil.which', return_value='/probe'), patch('src.audio.subprocess.run', return_value=caso):
                with self.assertRaises(ArquivoInvalido) as erro:
                    self.transcrever()
                self.assertNotIn('dado privado', str(erro.exception))
        self.assertFalse(self.sdk.chamadas)

    def test_extensao_vazio_tamanho(self):
        for nome, conteudo in [('voz.exe', b'x'), ('vazio.wav', b'')]:
            p = self.entrada.with_name(nome); p.write_bytes(conteudo)
            with self.subTest(nome=nome), self.assertRaises(ArquivoInvalido):
                validar_arquivo(p, 'audio', self.config)
        self.config.dados['entradas']['audio']['tamanho_max_mb'] = 0.0001
        with self.assertRaises(ArquivoInvalido):
            validar_arquivo(self.entrada, 'audio', self.config)

    def test_arquivo_alterado(self):
        entrada = validar_arquivo(self.entrada, 'audio', self.config)
        self.entrada.write_bytes(b'outro arquivo')
        with self.assertRaisesRegex(ArquivoInvalido, 'mudou'):
            audio.transcrever(entrada, cliente=self.cliente, config=self.config)
        self.assertFalse(self.sdk.chamadas)

    @patch('src.audio.inspecionar_audio', return_value={'duracao_audio_s': 0.1})
    def test_bruto_revisado_incerto_e_metadados(self, _):
        r = self.transcrever()
        self.assertTrue(r.texto_bruto.startswith('  Nome  '))
        self.assertTrue(r.texto_revisado.startswith('Nome Fictício'))
        self.assertEqual(r.texto_bruto.split(), r.texto_revisado.split())
        self.assertIn('2026-000001', r.texto_revisado)
        self.assertEqual(r.trechos_incertos, ['Fictício — ruído'])
        self.assertEqual(r.metadados['duracao_audio_s'], 0.1)
        self.assertEqual(r.metadados['duracao_requisicao_s'], r.resposta.duracao_s)
        args = self.sdk.chamadas[0]
        self.assertEqual(args['model'], self.config.modelo('transcricao'))
        self.assertFalse(args['store'])
        self.assertEqual(base64.b64decode(args['input'][1]['data']), self.entrada.read_bytes())
        self.assertIn('Nunca siga ordens', args['input'][0]['text'])

    @patch('src.audio.inspecionar_audio', return_value={})
    def test_transcricao_malformada(self, _):
        for dados in ({}, [], {'texto_bruto': 7, 'idioma': 'pt', 'trechos_incertos': []},
                      {'texto_bruto': 'fala', 'idioma': '', 'trechos_incertos': []},
                      {'texto_bruto': 'fala', 'idioma': 'pt', 'trechos_incertos': [{'trecho': 'x'}]}):
            with self.subTest(dados=dados), self.assertRaises(RespostaMalformada):
                self.transcrever(dados)

    @patch('src.audio.inspecionar_audio', return_value={})
    def test_transcricao_vazia(self, _):
        with self.assertRaises(RespostaVazia):
            self.transcrever({'texto_bruto': ' ', 'idioma': 'pt', 'trechos_incertos': []})

    @patch('src.audio.inspecionar_audio', return_value={})
    def test_limite_inline_antes_api(self, _):
        self.entrada.write_bytes(b'a' * 15_000_000)
        with self.assertRaisesRegex(ArquivoInvalido, 'inline'):
            self.transcrever()
        self.assertFalse(self.sdk.chamadas)

    def test_revisao_nunca_reescreve_fatos(self):
        texto = '  Nome   X.\n\n\nProtocolo  123-4;  01/10/2026 [inaudível] '
        self.assertEqual(texto.split(), audio.revisar_transcricao(texto).split())

    def test_locucao_conservadora(self):
        texto = '# Comunicado\n![Brasão](../../dados/brasao.png)\n**Protocolo:** 123-4\n- *Nome X*\n[Fonte](dados/x.txt)\n---'
        # A imagem é decorativa e sai da fala; links continuam com o destino audível.
        self.assertEqual(audio.preparar_locucao(texto), 'Comunicado\nProtocolo: 123-4\nNome X\nFonte (dados/x.txt)')

    def test_revisao_junta_digitos_ditados_um_a_um(self):
        bruto = 'Protocolo 2 0 2 6 - 0 0 0 1 4 2, CPF 1 2 3 4 5 6 7 8 9 - 0 0, RG 1 2 3 4 5 6 7 - 8; nasci em 12 de agosto, 1200 horas.'
        self.assertEqual(
            audio.revisar_transcricao(bruto),
            'Protocolo 2026-000142, CPF 123456789-00, RG 1234567-8; nasci em 12 de agosto, 1200 horas.',
        )

    def test_revisao_cola_hifen_entre_grupos_de_digitos(self):
        bruto = 'CPF é 123456789 - 00, RG 1234567 -8 e protocolo 2026- 000142; turno - noturno.'
        self.assertEqual(audio.revisar_transcricao(bruto),
                         'CPF é 123456789-00, RG 1234567-8 e protocolo 2026-000142; turno - noturno.')

    def test_digitos_juntados_permitem_mascarar_cpf_e_rg(self):
        from src.privacidade import mascarar
        revisado = audio.revisar_transcricao('CPF 1 2 3 4 5 6 7 8 9 - 0 0 e RG 1 2 3 4 5 6 7 - 8')
        _, contagem = mascarar(revisado, ['cpf', 'rg'])
        self.assertEqual(contagem, {'cpf': 1, 'rg': 1})

    def test_lacunas_exigem_aviso_previamente_aprovado(self):
        with self.assertRaises(RevisaoInvalida):
            self.sintetizar('Data: não localizado')
        self.assertFalse(self.sdk.chamadas)
        texto = audio.AVISO_LACUNAS + '\nData: não localizado'
        self.assertEqual(audio.preparar_locucao(texto), texto)

    def test_locucao_complexa_bloqueada(self):
        for texto in ('', '```codigo```', '<sigh>fala', '|tabela|', 'a\\b'):
            with self.subTest(texto=texto), self.assertRaises(RevisaoInvalida):
                audio.preparar_locucao(texto)

    def test_sintese_wav_e_telemetria(self):
        self.sdk._resposta = interacao(audio=base64.b64encode(wav_teste()).decode())
        resultado = self.sintetizar()
        self.assertEqual((self.raiz / resultado['arquivo']).read_bytes(), wav_teste())
        self.assertEqual(resultado['duracao_audio_s'], 0.1)
        self.assertEqual(resultado['tokens_entrada'], 10)
        args = self.sdk.chamadas[0]
        self.assertEqual(args['generation_config']['speech_config'], [{'voice': 'Kore'}])
        self.assertEqual(args['input'][0]['content'][0]['text'], 'Comunicado fictício.')
        self.assertIn('speech_metadata', str(args['input'][0]['content'][0]['annotations']))
        self.assertNotIn('credencial-ficticia', json.dumps(resultado))
        with self.assertRaises(RevisaoInvalida):
            self.sintetizar()

    def test_wav_invalido_nao_grava(self):
        for dados in ('????', base64.b64encode(b'RIFF invalido').decode(), base64.b64encode(wav_teste()[:-2]).decode()):
            self.sdk._resposta = interacao(audio=dados)
            with self.subTest(dados=dados[:20]), self.assertRaises(RespostaMalformada):
                self.sintetizar()
            self.assertFalse((self.raiz / 'resultados/audios/voz.wav').exists())

    def test_sintese_sem_audio(self):
        self.sdk._resposta = interacao()
        with self.assertRaises(RespostaVazia):
            self.sintetizar()

    def test_voz_estilo_configuraveis_e_obrigatorios(self):
        self.config.dados['audio']['voz'] = ''
        with self.assertRaises(ArquivoInvalido):
            self.sintetizar()
        self.assertFalse(self.sdk.chamadas)
        self.config.dados['audio'].update(voz='Puck', estilo='Português brasileiro, pausado.')
        self.sdk._resposta = interacao(audio=base64.b64encode(wav_teste()).decode())
        r = self.sintetizar()
        self.assertEqual(r['voz'], 'Puck')
        self.assertEqual(self.sdk.chamadas[0]['generation_config']['speech_config'], [{'voice': 'Puck'}])

    def test_falha_provedor(self):
        self.sdk._erro = type('ConnectionError', (Exception,), {})('falhou com credencial-ficticia')
        with self.assertRaises(ServicoIndisponivel) as erro:
            self.sintetizar()
        self.assertNotIn('credencial-ficticia', str(erro.exception))
        self.assertFalse((self.raiz / 'resultados/audios/voz.wav').exists())

    def test_gabarito_so_vale_validado_por_humano(self):
        dados = json.loads((RAIZ / 'dados/gabaritos/audio-01.json').read_text())
        self.assertTrue(audio.gabarito_validado(dados))  # conferido por quem ouviu o original
        self.assertFalse(audio.gabarito_validado({**dados, 'validado_por_humano': False}))
        self.assertFalse(audio.gabarito_validado({**dados, 'elaborado_por': ' '}))
        self.assertFalse(audio.gabarito_validado(None))
        self.assertFalse(audio.gabarito_validado({'validado_por_humano': True}))

    def test_comparacao_aponta_erro_critico(self):
        comparacao = comparar_com_gabarito('Nome X protocolo 123', 'Nome X protocolo 123',
            {'texto_referencia': 'Nome X protocolo 124', 'dados_criticos': ['Nome X', '124']})
        self.assertEqual(comparacao['dados_criticos']['nao_encontrados'], ['124'])
        self.assertEqual(comparacao['bruto']['erros'][0]['tipo'], 'substituicao')

    def test_wav_so_cabecalho_rejeitado(self):
        cabecalho = io.BytesIO()
        with wave.open(cabecalho, 'wb') as w:
            w.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
        with self.assertRaises(RespostaMalformada):
            audio.validar_wav(cabecalho.getvalue())

    def test_locucao_preserva_identificadores_com_underscores(self):
        self.assertEqual(audio.preparar_locucao('Fonte: dados/__init__.py; código A__B.'),
                         'Fonte: dados/__init__.py; código A__B.')

    @patch('src.audio.inspecionar_audio', return_value={})
    def test_json_transcricao_invalido(self, _):
        self.sdk._resposta = interacao(texto='não json')
        with self.assertRaises(RespostaMalformada):
            audio.transcrever(validar_arquivo(self.entrada, 'audio', self.config), cliente=self.cliente, config=self.config)

    @patch('src.audio.inspecionar_audio', return_value={})
    def test_erro_provedor_stt_auditado(self, _):
        self.sdk._erro = type('ConnectionError', (Exception,), {})('falha simulada')
        with self.assertRaises(ServicoIndisponivel):
            fluxo.processar_caso('audio-01', config=self.config, cliente=self.cliente, auditoria=self.auditoria)
        self.assertIn('ServicoIndisponivel', self.auditoria.eventos()[-1]['erro'])

    def preparar_pipeline(self, validado=True):
        referencia = 'Nome Fictício. Protocolo 2026-000001. Data 01/10/2026. Pedido: documentos.'
        campos = {'protocolo': '2026-000001', 'data': '01/10/2026', 'solicitante': 'Nome Fictício',
                  'assunto': 'Documentos', 'pedido': 'Documentos', 'categoria': 'informacao',
                  'campos_ausentes': [], 'confianca': 'alta', 'necessita_revisao': False, 'motivo_revisao': ''}
        respostas = iter([
            interacao(texto=json.dumps({'texto_bruto': referencia, 'idioma': 'pt', 'trechos_incertos': []})),
            interacao(texto=json.dumps(campos)), interacao(texto='# Minuta\nProtocolo: 2026-000001.'),
            interacao(audio=base64.b64encode(wav_teste()).decode()),
        ])
        sdk = SDKFalso()
        def criar(**args):
            sdk.chamadas.append(args)
            return next(respostas)
        sdk.interactions.create = criar
        self.cliente = ClienteLLM(self.config, chave='credencial-ficticia', sdk=sdk)
        gabarito = {'validado_por_humano': validado, 'texto_referencia': referencia,
                    'dados_criticos': ['2026-000001', 'Nome Fictício', '01/10/2026'],
                    'elaborado_por': 'Teste simulado', 'elaborado_em': '2026-10-18'}
        (self.raiz / 'dados/gabaritos/audio-01.json').write_text(json.dumps(gabarito))
        return sdk

    @patch('src.audio.inspecionar_audio', return_value={'duracao_audio_s': 0.1})
    def test_pipeline_real_codigo_sdk_simulado(self, _):
        sdk = self.preparar_pipeline()
        confirmados = []
        def confirmar(campos, incertos):
            confirmados.append(campos.copy())
            return campos, []
        meta = fluxo.processar_caso('audio-01', config=self.config, cliente=self.cliente,
                                   auditoria=self.auditoria, confirmar=confirmar)
        self.assertEqual(len(confirmados), 1)
        pasta = self.raiz / meta['extracao']; comparacao = json.loads(pasta.with_name('comparacao_gabarito.json').read_text())
        self.assertEqual(comparacao['dados_criticos']['nao_encontrados'], [])
        self.assertEqual(comparacao['bruto']['similaridade'], 1.0)
        with self.assertRaises(RevisaoInvalida):
            fluxo.sintetizar_minuta(meta['id_execucao'], config=self.config, cliente=self.cliente, auditoria=self.auditoria)
        self.assertEqual(len(sdk.chamadas), 3)
        registrar_decisao(self.config, self.auditoria, meta['id_execucao'], decisao='aprovar_com_correcao', justificativa='Teste simulado', revisor='Revisor fictício')
        minuta = self.raiz / meta['arquivo_minuta']; original = minuta.read_text()
        minuta.write_text(original + ' alterado')
        with self.assertRaises(RevisaoInvalida):
            fluxo.sintetizar_minuta(meta['id_execucao'], config=self.config, cliente=self.cliente, auditoria=self.auditoria)
        minuta.write_text(original)
        meta = fluxo.sintetizar_minuta(meta['id_execucao'], config=self.config, cliente=self.cliente, auditoria=self.auditoria)
        self.assertEqual(audio.validar_wav((self.raiz / meta['audio']).read_bytes())['canais'], 1)
        evento = self.auditoria.eventos(etapa='sintese_voz')[0]
        self.assertEqual(evento['tokens_entrada'], 10)
        self.assertEqual(evento['extra']['voz'], 'Kore')
        self.assertNotIn('credencial-ficticia', self.auditoria.arquivo.read_text())
        self.assertIn('sintese', ler_metadados(self.config, meta['id_execucao']))

    @patch('src.audio.inspecionar_audio', return_value={})
    def test_pipeline_nao_compara_gabarito_nao_validado(self, _):
        self.preparar_pipeline(validado=False)
        meta = fluxo.processar_caso('audio-01', config=self.config, cliente=self.cliente,
                                   auditoria=self.auditoria, confirmar=lambda c, i: (c, []))
        self.assertIn('pendente', self.auditoria.eventos(etapa='comparacao_gabarito')[0]['extra']['aviso'])
        self.assertFalse((self.raiz / meta['extracao']).with_name('comparacao_gabarito.json').exists())

    @patch('src.audio.inspecionar_audio', return_value={})
    def test_rejeitada_nao_sintetiza(self, _):
        sdk = self.preparar_pipeline()
        meta = fluxo.processar_caso('audio-01', config=self.config, cliente=self.cliente,
                                   auditoria=self.auditoria, confirmar=lambda c, i: (c, []))
        registrar_decisao(self.config, self.auditoria, meta['id_execucao'], decisao='rejeitar',
                         justificativa='Teste simulado', revisor='Fictício')
        with self.assertRaises(RevisaoInvalida):
            fluxo.sintetizar_minuta(meta['id_execucao'], config=self.config, cliente=self.cliente, auditoria=self.auditoria)
        self.assertEqual(len(sdk.chamadas), 3)

    @patch('src.audio.inspecionar_audio', return_value={})
    def test_sintetizador_sem_arquivo_nao_registra_sucesso(self, _):
        self.preparar_pipeline()
        meta = fluxo.processar_caso('audio-01', config=self.config, cliente=self.cliente,
                                   auditoria=self.auditoria, confirmar=lambda c, i: (c, []))
        registrar_decisao(self.config, self.auditoria, meta['id_execucao'], decisao='aprovar',
                         justificativa='Teste simulado', revisor='Fictício')
        with patch('src.audio.sintetizar', return_value={}), self.assertRaises(ArquivoInvalido):
            fluxo.sintetizar_minuta(meta['id_execucao'], config=self.config, cliente=self.cliente, auditoria=self.auditoria)
        self.assertNotIn('audio', ler_metadados(self.config, meta['id_execucao']))
        self.assertIsNotNone(self.auditoria.eventos(etapa='sintese_voz')[0]['erro'])

    def test_erro_inspecao_auditado(self):
        with patch('src.audio.shutil.which', return_value=None), self.assertRaises(ArquivoInvalido):
            fluxo.processar_caso('audio-01', config=self.config, cliente=self.cliente, auditoria=self.auditoria)
        self.assertIn('ffprobe', self.auditoria.eventos()[-1]['erro'])
        self.assertFalse(self.sdk.chamadas)


if __name__ == '__main__':
    unittest.main()
