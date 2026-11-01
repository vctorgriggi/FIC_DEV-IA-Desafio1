"""Validação offline da base. Executar: python -m scripts.validar_dados_d2."""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from pypdf import PdfReader
from src.config import carregar_config
from src.ingestion import ler_manifesto
from src.privacidade import PADRAO_CHAVE_OPENAI
from src.schemas import AvaliacaoSentimento, FichaCompreensao, SolicitacaoEstruturada
from src.sentiment import ler_avaliacoes


def validar(config=None):
    config = config or carregar_config()
    raiz = config.raiz
    def ler(nome):
        return json.loads((raiz / nome).read_text(encoding='utf-8'))
    def exigir(condicao, mensagem):
        if not condicao:
            raise ValueError(mensagem)
    manifesto = ler('dados/originais/desafio-2/casos.json')
    docs = ler_manifesto(config)
    exigir(len(docs) == 6, 'Esperados seis documentos.')
    exigir(len({d.tema for d in docs}) >= 2, 'Faltam temas.')
    exigir({Path(d.arquivo).suffix for d in docs} == {'.txt', '.pdf'}, 'Formatos incorretos.')
    textos = {}
    versoes = {d.id: d.versao for d in docs}
    for d in docs:
        p = config.caminho('acervo') / d.arquivo
        textos[d.id] = '\n'.join(pg.extract_text() or '' for pg in PdfReader(p).pages) if p.suffix == '.pdf' else p.read_text(encoding='utf-8')
        exigir('FICTÍCIO' in textos[d.id], 'Documento sem aviso de ficção.')
    exigir(any(d.substitui and d.vigencia_inicio for d in docs), 'Falta versionamento.')
    todos_textos = list(textos.values())
    ids = [d.id for d in docs]
    totais = {}
    for grupo, total, chave in [('solicitacoes', 6, 'caso_id'), ('perguntas', 8, 'id'), ('ataques', 3, 'id')]:
        caminhos = manifesto[grupo]
        exigir(len(caminhos) == total and len(set(caminhos)) == total, f'Quantidade de {grupo} inválida.')
        itens = [ler(p) for p in caminhos]
        totais[grupo] = total
        ids.extend(i[chave] for i in itens)
        todos_textos.extend(json.dumps(i, ensure_ascii=False) for i in itens)
        if grupo == 'solicitacoes':
            exigir(Counter(i['tipo'] for i in itens) == {'completa':4,'incompleta':1,'ambigua':1}, 'Tipos de solicitação inválidos.')
            for i in itens:
                s = SolicitacaoEstruturada.model_validate({**i['solicitacao_esperada'], 'entidades':i['entidades_esperadas']})
                FichaCompreensao(resumo=i['resumo_esperado'], inferencias=[])
                texto = (raiz / i['arquivo']).read_text(encoding='utf-8')
                todos_textos.append(texto)
                nulos = {k for k in ('protocolo','data','solicitante','assunto','pedido','categoria') if getattr(s,k) is None}
                exigir(set(s.campos_ausentes) == nulos, 'Ausências inconsistentes.')
                exigir(set(i['campos_presentes']) | nulos == {'protocolo','data','solicitante','assunto','pedido','categoria'}, 'Campos presentes inconsistentes.')
                exigir(s.categoria is None or s.categoria in config.dados['categorias'], 'Categoria inválida.')
                exigir(not nulos or s.necessita_revisao, 'Ausência sem revisão.')
                for lista in s.entidades.model_dump().values():
                    exigir(all(v in texto for v in lista), 'Entidade sem suporte literal.')
                for campo in ('protocolo','data','solicitante','assunto','pedido'):
                    v=getattr(s,campo)
                    exigir(v is None or v in texto, f'{campo} sem suporte.')
                exigir(all(f in texto for f in i['fatos_essenciais']), 'Fato sem suporte.')
                exigir(bool(i['justificativa_rotulo']), 'Falta justificativa.')
                if 'reaproveitado_de' in i:
                    original=(raiz / i['reaproveitado_de']).read_bytes()
                    exigir(hashlib.sha256(original).hexdigest()==i['hash_origem'] and original==(raiz/i['arquivo']).read_bytes(), 'Original alterado.')
                for f in i['fontes_esperadas']:
                    exigir(versoes.get(f['documento_id']) == f['versao'] and f['trecho_referencia'] in textos[f['documento_id']], 'Fonte de solicitação inválida.')
        elif grupo == 'perguntas':
            exigir(Counter(i['tipo'] for i in itens) == {'respondivel':5,'sem_resposta':2,'contraditoria':1}, 'Tipos RAG inválidos.')
            for i in itens:
                exigir(i['status_esperado'] in {'fundamentada','sem_evidencia','conflito'}, 'Status inválido.')
                exigir(bool(i['trechos_referencia']) == (i['tipo'] != 'sem_resposta'), 'Referências inconsistentes.')
                for tr in i['trechos_referencia']:
                    exigir(versoes.get(tr['documento_id']) == tr['versao'], 'Versão inválida.')
                    # PDF pode quebrar linha entre palavras; não altera palavras ou pontuação.
                    exigir(' '.join(tr['trecho_literal'].split()) in ' '.join(textos[tr['documento_id']].split()), 'Citação inexistente.')
        else:
            exigir({i['alvo'] for i in itens} == {'solicitacao','acervo','segredo'}, 'Ataques incompletos.')
            for i in itens:
                exigir(i['decisao_esperada'] in {'bloquear','revisar'}, 'Ataque sem proteção.')
                if i['alvo']=='acervo':
                    exigir(i['entrada'] in textos[i['documento_id']], 'Ataque ausente do acervo.')
    avs = ler_avaliacoes(config)
    gab = ler(manifesto['sentimentos'])
    exigir(len(avs) == len(gab['avaliacoes']) == 12, 'Esperadas doze avaliações.')
    exigir(Counter(a['polaridade_esperada'] for a in gab['avaliacoes']) == {'positiva':3,'negativa':3,'neutra':3,'indeterminada':3}, 'Distribuição incorreta.')
    exigir({a['id'] for a in avs} == {a['id'] for a in gab['avaliacoes']}, 'IDs de sentimentos inconsistentes.')
    for a in gab['avaliacoes']:
        AvaliacaoSentimento(id=a['id'], polaridade=a['polaridade_esperada'], justificativa=a['justificativa_rotulo'], necessita_revisao=a['ambigua'], confianca_declarada=None)
        exigir(a['ambigua']==(a['polaridade_esperada']=='indeterminada'), 'Ambiguidade inconsistente.')
    ids.extend(a['id'] for a in avs)
    exigir(len(ids) == len(set(ids)), 'IDs repetidos.')
    todos_textos.extend(a['texto'] for a in avs)
    for t in todos_textos:
        exigir(not PADRAO_CHAVE_OPENAI.search(t), 'Formato de segredo detectado.')
        exigir(not re.search(r'-----BEGIN .*PRIVATE KEY|(?:senha|password|api_key)\s*[:=]\s*\S+',t,re.I), 'Atribuição de segredo detectada.')
    return {'documentos':len(docs), **totais, 'avaliacoes':len(avs), 'ids_unicos':len(ids), 'status':'validado offline'}


if __name__ == '__main__':
    print(json.dumps(validar(),ensure_ascii=False,indent=2))
