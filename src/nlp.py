"""RF14/RF15: extração estrita, regras locais e compreensão com apoio literal.

Não gera minutas. Falhas levantam RespostaMalformada; o fluxo integrado deve
registrá-las como bloqueadas antes de recuperar fontes ou redigir respostas.
"""
from __future__ import annotations

import json
import re
from datetime import date

from pydantic import BaseModel, ConfigDict, ValidationError

from .config import Config
from .llm_client import ClienteLLM, ErroLLM, RespostaMalformada, formato_json
from .privacidade import mascarar, ocultar_segredos
from .prompts import carregar_prompt, delimitar
from .schemas import FichaCompreensao, SolicitacaoEstruturada
from .tipos import Resultado

CAMPOS = ('protocolo', 'data', 'solicitante', 'assunto', 'pedido', 'categoria')
MESES = ('janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
         'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro')
PADRAO_DATA = re.compile(r'(?<!\w)(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}|\d{1,2} de (?:' + '|'.join(MESES) + r') de \d{4})(?!\w)', re.I)


def _seguro(texto, config):
    return ocultar_segredos(mascarar(texto, config.dados['privacidade']['mascarar_antes_de_enviar'])[0], [])


def _json(texto):
    def objeto(pares):
        resultado = {}
        for chave, valor in pares:
            if chave in resultado:
                raise ValueError('JSON com chave repetida.')
            resultado[chave] = valor
        return resultado
    def constante(_):
        raise ValueError('Constante fora do padrão JSON.')
    return json.loads(texto, object_pairs_hook=objeto, parse_constant=constante)


def _erros_esquema(erro):
    # Não reenviar input/ctx: a resposta inválida também é conteúdo não confiável.
    return [{'type': e['type'], 'loc': list(e['loc'])} for e in erro.errors()]


def _data(valor):
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', valor):
        return date.fromisoformat(valor)
    if re.fullmatch(r'\d{1,2}/\d{1,2}/\d{4}', valor):
        dia, mes, ano = map(int, valor.split('/'))
        return date(ano, mes, dia)
    partes = re.fullmatch(r'(\d{1,2}) de (\w+) de (\d{4})', valor, re.I)
    if partes and partes[2].lower() in MESES:
        return date(int(partes[3]), MESES.index(partes[2].lower()) + 1, int(partes[1]))
    raise ValueError('Formato de data não reconhecido.')


def _literal(valor, texto):
    # Evita aceitar um protocolo abreviado dentro de outro, ou nome como parte de palavra.
    return bool(re.search(r'(?<!\w)' + re.escape(valor) + r'(?!\w)', texto))


def _data_rotulada(texto):
    rotulada = re.search(r'(?im)(?:^|\n|\\n)\s*Data(?: da solicitação| de matrícula| matrícula)?\s*:\s*(' + PADRAO_DATA.pattern + ')', texto)
    if rotulada is None:
        rotulada = re.search(r'protocolo\s+(?:é\s+)?\d{4}-\d{6},?\s+de\s+(' + PADRAO_DATA.pattern + ')', texto, re.I)
    return rotulada


def validar_regras(solicitacao: SolicitacaoEstruturada, texto_original: str, *, config: Config) -> list[str]:
    """Problemas bloqueiam a minuta; não corrige fatos nem preenche ausências."""
    problemas = []
    ausentes = [c for c in CAMPOS if getattr(solicitacao, c) is None]
    if set(ausentes) != set(solicitacao.campos_ausentes) or len(set(solicitacao.campos_ausentes)) != len(solicitacao.campos_ausentes):
        problemas.append('campos_ausentes: lista inconsistente com os campos null.')
    if ausentes and not solicitacao.necessita_revisao:
        problemas.append('necessita_revisao: ausências exigem revisão.')
    if solicitacao.necessita_revisao and not solicitacao.motivo_revisao.strip():
        problemas.append('motivo_revisao: obrigatório quando há revisão.')
    if solicitacao.categoria is not None and solicitacao.categoria not in config.dados['categorias']:
        problemas.append('categoria: fora da lista configurada.')
    if solicitacao.categoria == 'revisao' and not solicitacao.necessita_revisao:
        problemas.append('categoria: revisao exige necessita_revisao=true.')
    if re.match(r'^solicito (?:a )?emissão de (?:uma? )?(?:declaração|histórico|certificado|documento)\b', (solicitacao.pedido or '').casefold()) and solicitacao.categoria != 'solicitacao_documentos':
        problemas.append('categoria: pedido explícito de emissão exige solicitacao_documentos.')
    for campo in CAMPOS:
        valor = getattr(solicitacao, campo)
        if valor is None:
            continue
        if not valor.strip() or valor.strip().lower() in {'não localizado', 'null'}:
            problemas.append(f'{campo}: ausência deve ser null.')
        elif campo not in {'categoria', 'data'} and not all(parte.strip() and _literal(parte, texto_original) for parte in (valor.split(' … ') if campo == 'pedido' else [valor])):
            problemas.append(f'{campo}: valor sem suporte literal no original.')
    if solicitacao.protocolo is not None:
        if not re.fullmatch(r'\d{4}-\d{6}', solicitacao.protocolo):
            problemas.append('protocolo: formato esperado aaaa-nnnnnn ou null se ilegível.')
        elif not re.search(r'(?<![\w-])' + re.escape(solicitacao.protocolo) + r'(?![\w-])', texto_original):
            problemas.append('protocolo: valor abreviado ou inconsistente no original.')
    # Cada data declarada no original é conferida, sem confundir datas de funções diferentes.
    datas_originais = set()
    for valor in PADRAO_DATA.findall(texto_original):
        try:
            datas_originais.add(_data(valor))
        except ValueError:
            problemas.append('data: o original contém data impossível; requer conferência.')
    rotulada = _data_rotulada(texto_original)
    if rotulada and solicitacao.data is None:
        problemas.append('data: ausente na extração apesar de rotulada no original.')
    if solicitacao.data is not None:
        try:
            extraida = _data(solicitacao.data)
        except ValueError:
            problemas.append('data: inexistente ou formato inválido.')
            extraida = None
        if extraida is not None and extraida not in datas_originais:
            problemas.append('data: valor sem suporte no original.')
        try:
            data_rotulada = _data(rotulada[1]) if rotulada else None
        except ValueError:
            # A data impossível do original já foi apontada acima; a extraída não leva a culpa.
            data_rotulada = None
        # Uma data de nascimento literal não deve substituir a data do requerimento.
        if extraida is not None and data_rotulada is not None and extraida != data_rotulada:
            problemas.append('data: não corresponde à data identificada da solicitação.')
    for tipo, valores in solicitacao.entidades.model_dump().items():
        for valor in valores:
            if not valor.strip() or not _literal(valor, texto_original):
                problemas.append(f'entidades.{tipo}: entidade sem suporte literal no original.')
            if tipo == 'protocolos' and not re.fullmatch(r'\d{4}-\d{6}', valor):
                problemas.append('entidades.protocolos: identificador ilegível ou incompleto exige revisão, não extração como protocolo.')
            if tipo == 'datas':
                try:
                    _data(valor)
                except ValueError:
                    problemas.append('entidades.datas: data impossível ou formato inválido.')
    return list(dict.fromkeys(problemas))


def _entrada_extracao(texto, origem, config, prompt):
    return (prompt.texto + '\nCategorias aceitas: ' + json.dumps(config.dados['categorias'], ensure_ascii=False)
            + '\n' + delimitar(_seguro(texto, config), origem))


def _chamar(cliente, config, perfil, entrada, formato):
    geracao = config.perfil_geracao(perfil)
    return cliente.gerar(modelo=geracao['modelo'], entrada=entrada,
                         parametros=geracao.get('parametros', {}),
                         instrucao_sistema=carregar_prompt(config, 'sistema_seguro_d2', 1).texto,
                         formato_resposta=formato)


def extrair_solicitacao(texto: str, *, origem: str, cliente: ClienteLLM, config: Config,
                        perfil: str | None = None) -> Resultado[SolicitacaoEstruturada]:
    """Saída estrita e no máximo um reparo; incoerência persistente é erro controlado."""
    prompt = carregar_prompt(config, 'solicitacao_d2', 4)
    entrada = _entrada_extracao(texto, origem, config, prompt)
    formato = formato_json(SolicitacaoEstruturada.model_json_schema(), 'solicitacao')
    respostas = []
    erros = []
    for tentativa in range(2):
        instrucao = '' if not tentativa else ('\nCorrija uma única vez estes erros locais:\n'
            + delimitar(_seguro(json.dumps(erros, ensure_ascii=False), config), 'diagnostico_validacao'))
        try:
            resposta = _chamar(cliente, config, perfil, entrada + instrucao, formato)
        except ErroLLM as erro:
            erro.respostas, erro.prompt = respostas, prompt
            raise
        respostas.append(resposta)
        try:
            _json(resposta.texto)
            solicitacao = SolicitacaoEstruturada.model_validate_json(resposta.texto)
            erros = validar_regras(solicitacao, _seguro(texto, config), config=config)
            if not erros:
                return Resultado(solicitacao, respostas, prompt)
        except ValidationError as erro:
            erros = _erros_esquema(erro)
        except ValueError:
            erros = ['JSON sintaticamente inválido ou com chaves repetidas.']
    erro = RespostaMalformada('RF14: extração inválida após uma tentativa de reparo.', detalhe=_seguro(json.dumps(erros, ensure_ascii=False), config))
    # Permite ao fluxo auditar custo/latência também quando a validação bloqueia.
    erro.respostas, erro.prompt = respostas, prompt
    raise erro


def _diagnosticar(texto):
    resultado = dict(json_valido=False, esquema_valido=False, campos_obrigatorios_ausentes=[],
                     tipos_incorretos=[], campos_extras=[], outros_erros=[])
    try:
        _json(texto)
    except ValueError:
        resultado['outros_erros'] = [{'type':'json_invalid', 'loc':[]}]
        return resultado
    resultado['json_valido'] = True
    try:
        SolicitacaoEstruturada.model_validate_json(texto)
        resultado['esquema_valido'] = True
    except ValidationError as erro:
        for e in _erros_esquema(erro):
            tipo = e['type']
            grupo = ('campos_obrigatorios_ausentes' if tipo == 'missing' else
                     'campos_extras' if tipo == 'extra_forbidden' else
                     'tipos_incorretos' if tipo.endswith(('_type', '_parsing')) else 'outros_erros')
            resultado[grupo].append(e)
    return resultado


def comparar_sintatico_e_esquema(texto: str, *, origem: str, cliente: ClienteLLM,
                                 config: Config, perfil: str | None = None) -> dict:
    """Duas chamadas independentes, sem reparo, para comparar as saídas iniciais."""
    prompt = carregar_prompt(config, 'solicitacao_d2', 4)
    entrada = _entrada_extracao(texto, origem, config, prompt)
    resultado = {'origem':origem, 'prompt':prompt.identificador, 'hash_prompt':prompt.hash, 'abordagens':{}}
    for nome, formato in [('json_livre', None), ('esquema', formato_json(SolicitacaoEstruturada.model_json_schema(), 'solicitacao'))]:
        # JSON livre recebe a descrição dos mesmos campos, sem restrição do provedor.
        instrucao = entrada + '\nRetorne somente JSON conforme este contrato: ' + json.dumps(SolicitacaoEstruturada.model_json_schema(), ensure_ascii=False)
        resposta = _chamar(cliente, config, perfil, instrucao, formato)
        resultado['abordagens'][nome] = {**_diagnosticar(resposta.texto),
            'saida':_seguro(resposta.texto, config), 'modelo':resposta.modelo,
            'tokens_entrada':resposta.tokens_entrada, 'tokens_saida':resposta.tokens_saida,
            'duracao_s':resposta.duracao_s, 'custo_estimado_usd':resposta.custo_estimado_usd}
    return resultado


class _ChecagemResumo(BaseModel):
    """Contrato interno do verificador; não modifica a ficha compartilhada."""
    model_config = ConfigDict(extra='forbid', strict=True)
    fiel: bool
    evidencias: list[str]
    fatos_sem_suporte: list[str]
    justificativa: str


def _conferir_resumo(ficha, original, solicitacao, *, cliente, config, perfil, respostas):
    normalizado = ' '.join(original.split())
    # Passagens literais mantêm o caminho local. Paráfrases seguem para verificação semântica.
    partes = ficha.resumo.split(' … ')
    if all(parte.strip() and ' '.join(parte.split()) in normalizado for parte in partes):
        return []
    # Protocolos inexistentes também são bloqueados por código, antes da checagem semântica.
    for protocolo in re.findall(r'\b\d{4}-\d{6}\b', ficha.resumo):
        if protocolo not in original:
            return ['resumo: protocolo sem suporte no original.']
    prompt = carregar_prompt(config, 'verificar_resumo_d2', 1)
    entrada = (prompt.texto + '\n' + delimitar(original, 'original') + '\n'
               + delimitar(_seguro(solicitacao.model_dump_json(), config), 'solicitacao') + '\n'
               + delimitar(ficha.resumo, 'resumo'))
    resposta = _chamar(cliente, config, perfil, entrada,
                       formato_json(_ChecagemResumo.model_json_schema(), 'verificacao_resumo'))
    respostas.append(resposta)
    resposta.parametros.update(prompt_id=prompt.identificador, prompt_hash=prompt.hash)
    _json(resposta.texto)
    checagem = _ChecagemResumo.model_validate_json(resposta.texto)
    if not checagem.fiel or checagem.fatos_sem_suporte:
        return ['resumo: verificação semântica identificou afirmação sem suporte.']
    if not checagem.justificativa.strip() or not checagem.evidencias:
        return ['resumo: verificação sem evidências suficientes.']
    if any(not trecho.strip() or ' '.join(trecho.split()) not in normalizado for trecho in checagem.evidencias):
        return ['resumo: evidência do verificador ausente no original.']
    return []


def compreender(texto: str, solicitacao: SolicitacaoEstruturada, *, origem: str,
                cliente: ClienteLLM, config: Config, perfil: str | None = None) -> Resultado[FichaCompreensao]:
    """Resumo de até 100 palavras; paráfrases verificadas e inferências separadas.

    Trechos sem suporte são recusados; revisão humana ainda verifica seleção,
    negações e fatos essenciais. Categoria e entidades nunca são regeneradas.
    """
    problemas = validar_regras(solicitacao, _seguro(texto, config), config=config)
    if problemas:
        raise RespostaMalformada('RF15: solicitação incoerente; compreensão bloqueada.',
                                 detalhe=json.dumps(problemas, ensure_ascii=False))
    prompt = carregar_prompt(config, 'compreensao_d2', 3)
    original = _seguro(texto, config)
    entrada = (prompt.texto + '\n' + delimitar(original, origem) + '\n'
               + delimitar(_seguro(solicitacao.model_dump_json(), config), 'solicitacao_estruturada'))
    resposta = _chamar(cliente, config, perfil, entrada,
                       formato_json(FichaCompreensao.model_json_schema(), 'compreensao'))
    erros = []
    respostas = [resposta]
    try:
        _json(resposta.texto)
        ficha = FichaCompreensao.model_validate_json(resposta.texto)
        if not ficha.resumo.strip():
            erros.append('resumo: não pode ser vazio.')
        for inferencia in ficha.inferencias:
            if not all(v.strip() for v in (inferencia.campo, inferencia.valor, inferencia.justificativa)):
                erros.append('inferencias: campo, valor e justificativa precisam estar preenchidos.')
            if inferencia.campo.lower() in {*CAMPOS, 'entidades'}:
                erros.append('inferencias: não podem substituir campos da solicitação.')
        if _seguro(resposta.texto, config) != resposta.texto:
            erros.append('compreensao: dado pessoal ou segredo indevidamente reproduzido.')
        if not erros:
            erros.extend(_conferir_resumo(ficha, original, solicitacao, cliente=cliente, config=config, perfil=perfil, respostas=respostas))
        if not erros:
            return Resultado(ficha, respostas, prompt)
    except ValidationError as erro:
        erros = _erros_esquema(erro)
    except ValueError:
        erros = ['JSON inválido.']
    except ErroLLM as erro:
        erro.respostas, erro.prompt = respostas, prompt
        raise
    erro = RespostaMalformada('RF15: ficha inválida; requer revisão humana.',
                             detalhe=_seguro(json.dumps(erros, ensure_ascii=False), config))
    erro.respostas, erro.prompt = respostas, prompt
    raise erro
