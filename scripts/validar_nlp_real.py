"""Validação real incremental, com gabaritos imutáveis e orçamento persistente.

python -m scripts.validar_nlp_real
python -m scripts.validar_nlp_real --casos D2-S01 --etapas compreensao
Uma execução inicial avalia seis solicitações e compara as abordagens em S02.
Reexecuções explícitas só avaliam os casos/etapas selecionados; histórico é preservado.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from src.config import Config, carregar_chave, carregar_config
from src.llm_client import ErroLLM
from src.metrics import acuracia_categorias
from src.nlp import _diagnosticar, _seguro, compreender, comparar_sintatico_e_esquema, extrair_solicitacao, validar_regras
from src.privacidade import ocultar_segredos
from src.schemas import ESQUEMA_VERSAO, SolicitacaoEstruturada
from scripts.orcamento_nlp import ClienteOrcamentado, OrcamentoEsgotado
from scripts.validar_dados_d2 import validar


def executar(*, casos=None, etapas=None, saida=None, ledger=None):
    original=carregar_config()
    config=Config(deepcopy(original.dados), original.raiz)
    # Só esta avaliação limita a saída; o perfil/modelo compartilhado permanece intacto.
    config.dados['parametros_geracao']={**config.dados['parametros_geracao'],'max_output_tokens':4096,'reasoning':{'effort':'low'}}
    saida=Path(saida or config.caminho('metricas')/'integrante-1-openai.json')
    ledger=Path(ledger or config.caminho('metricas')/'integrante-1-orcamento.json')
    casos=casos or [f'D2-S{i:02}' for i in range(1,7)]
    etapas=etapas or ['extracao','compreensao','comparacao']
    if any(id not in [f'D2-S{i:02}' for i in range(1,7)] for id in casos):
        raise ValueError('Caso fora do catálogo do Integrante 1.')
    chave=carregar_chave()
    relatorio=json.loads(saida.read_text(encoding='utf-8')) if saida.exists() else {'modo':'real','casos':{},'comparacoes':[],'execucoes':[]}
    relatorio.update(dados=validar(config),esquema_versao=ESQUEMA_VERSAO,perfil=config.perfil_geracao(),
                     parametros_avaliacao=config.dados['parametros_geracao'])
    if not chave:
        raise ErroLLM('Chave não carregada; nenhuma chamada realizada.')
    cliente=ClienteOrcamentado(config,arquivo=ledger,chave=chave)
    relatorio.setdefault('testes_bloqueio',[])
    execucao={'inicio':datetime.now(timezone.utc).isoformat(),'casos':casos,'etapas':etapas,'status':'executando'}
    relatorio['execucoes'].append(execucao)
    def salvar():
        relatorio['consumo']={'chamadas_transporte':len(cliente.ledger['chamadas']),
            'custo_estimado_usd':round(sum(c.get('custo_estimado_usd') or 0 for c in cliente.ledger['chamadas']),6),
            'custo_contabilizado_conservador_usd':round(cliente.gasto,6), 'limite_usd':cliente.limite,
            'tokens_entrada':sum(c.get('tokens_entrada') or 0 for c in cliente.ledger['chamadas']),
            'tokens_saida':sum(c.get('tokens_saida') or 0 for c in cliente.ledger['chamadas']),
            'chamadas_sem_usage':sum(c['status']!='medido' for c in cliente.ledger['chamadas'])}
        esperadas={};obtidas={}; definidos={}
        for id in [f'D2-S{i:02}' for i in range(1,7)]:
            g=json.loads((config.raiz/f'dados/gabaritos/{id}.json').read_text(encoding='utf-8'))
            esperadas[id]=g['solicitacao_esperada']['categoria']
            if esperadas[id] is not None:
                definidos[id]=esperadas[id]
            extracoes=relatorio['casos'].get(id,{}).get('extracoes',[])
            if extracoes and extracoes[-1]['status']=='valido':
                obtidas[id]=extracoes[-1]['solicitacao']['categoria']
        relatorio['acuracia_gabarito_original']=acuracia_categorias(obtidas,esperadas)
        relatorio['acuracia_categorias_definidas']=acuracia_categorias(obtidas,definidos)
        relatorio['solicitacoes_extraidas']=len(obtidas)
        relatorio['solicitacoes_com_ficha_valida']=sum(bool(c.get('fichas')) and c['fichas'][-1]['status']=='valido' for c in relatorio['casos'].values())
        relatorio['status']='concluido' if relatorio['solicitacoes_extraidas']==6 and relatorio['solicitacoes_com_ficha_valida']==6 else 'parcial'
        saida.parent.mkdir(parents=True,exist_ok=True)
        # Artefato de experimento explicitamente autorizado, separado do log de auditoria.
        texto=ocultar_segredos(_seguro(json.dumps(relatorio,ensure_ascii=False,indent=2),config),[chave])
        saida.write_text(texto+'\n',encoding='utf-8')
    def respostas(objeto):
        registros=[]
        for r in getattr(objeto,'respostas',[]):
            registro={'saida':_seguro(r.texto,config),'modelo':r.modelo,'tokens_entrada':r.tokens_entrada,
                'tokens_saida':r.tokens_saida,'custo_estimado_usd':r.custo_estimado_usd,
                'duracao_s':r.duracao_s,'parametros':r.parametros}
            if r.parametros.get('formato_resposta')=='solicitacao':
                registro['validacao_esquema']=_diagnosticar(r.texto)
            registros.append(registro)
        return registros
    interromper=False
    for id in casos:
        gpath=config.raiz/f'dados/gabaritos/{id}.json'
        g=json.loads(gpath.read_text(encoding='utf-8'))
        texto=(config.raiz/g['arquivo']).read_text(encoding='utf-8')
        caso=relatorio['casos'].setdefault(id,{'extracoes':[],'fichas':[]})
        caso['hash_gabarito']=hashlib.sha256(gpath.read_bytes()).hexdigest()
        if 'extracao' in etapas:
            cliente.contexto=id+':extracao'
            tentativa={'inicio':datetime.now(timezone.utc).isoformat()}
            try:
                resultado=extrair_solicitacao(texto,origem=id,cliente=cliente,config=config)
                s=resultado.valor
                divergencias={}
                for campo,esperado in g['solicitacao_esperada'].items():
                    obtido=getattr(s,campo)
                    if obtido!=esperado:
                        divergencias[campo]={'esperado':esperado,'obtido':obtido}
                entidades={tipo:{'corretas':sorted(set(getattr(s.entidades,tipo)) & set(valores)),
                    'omitidas':sorted(set(valores)-set(getattr(s.entidades,tipo))),
                    'adicionais_ao_gabarito':sorted(set(getattr(s.entidades,tipo))-set(valores))}
                    for tipo,valores in g['entidades_esperadas'].items()}
                tentativa.update(status='valido',solicitacao=s.model_dump(),regras=validar_regras(s,texto,config=config),
                    divergencias_gabarito=divergencias,entidades=entidades, reparos=len(resultado.respostas)-1,
                    respostas=respostas(resultado),prompt=resultado.prompt.identificador)
            except ErroLLM as erro:
                tentativa.update(status='bloqueado',erro=type(erro).__name__,mensagem=str(erro),
                    detalhe=erro.detalhe,respostas=respostas(erro))
                interromper=type(erro).__name__!='RespostaMalformada'
            caso['extracoes'].append(tentativa)
            print(f'{id} extração: {tentativa["status"]}',flush=True)
            salvar()
        if interromper:
            break
        if 'compreensao' in etapas:
            ultimas=caso['extracoes']
            if not ultimas or ultimas[-1]['status']!='valido':
                caso['fichas'].append({'status':'bloqueado','motivo':'Sem extração válida; nenhuma chamada de compreensão realizada.'})
            else:
                s=SolicitacaoEstruturada.model_validate(ultimas[-1]['solicitacao'])
                cliente.contexto=id+':compreensao'
                tentativa={'inicio':datetime.now(timezone.utc).isoformat()}
                try:
                    resultado=compreender(texto,s,origem=id,cliente=cliente,config=config)
                    resumo=resultado.valor.resumo
                    tentativa.update(status='valido',ficha=resultado.valor.model_dump(),palavras=len(resumo.split()),
                        fatos_nao_localizados_literalmente=[f for f in g['fatos_essenciais'] if f.casefold() not in resumo.casefold()],
                        respostas=respostas(resultado),prompt=resultado.prompt.identificador)
                except ErroLLM as erro:
                    tentativa.update(status='bloqueado',erro=type(erro).__name__,mensagem=str(erro),detalhe=erro.detalhe,respostas=respostas(erro))
                    interromper=type(erro).__name__!='RespostaMalformada'
                caso['fichas'].append(tentativa)
                print(f'{id} compreensão: {tentativa["status"]}',flush=True)
            salvar()
        if interromper:
            break
    if not interromper and 'bloqueio' in etapas:
        # Expectativa persistida ANTES da chamada; não muda os seis gabaritos.
        texto=(config.raiz/'dados/originais/desafio-2/D2-S02.txt').read_text(encoding='utf-8').replace('15/10/2026','31/02/2026')
        cenario={'id':'RF14-data-impossivel','variante_de':'D2-S02','alteracao':'Data: 31/02/2026',
            'esperado':'RespostaMalformada após no máximo um reparo; nenhuma minuta',
            'registrado_antes_da_chamada':datetime.now(timezone.utc).isoformat()}
        relatorio['testes_bloqueio'].append(cenario)
        salvar()
        cliente.contexto='RF14-data-impossivel:extracao'
        try:
            resultado=extrair_solicitacao(texto,origem='RF14-data-impossivel',cliente=cliente,config=config)
            cenario.update(status='falha_bloqueio',respostas=respostas(resultado),solicitacao=resultado.valor.model_dump())
        except ErroLLM as erro:
            cenario.update(status='bloqueado_conforme_esperado' if type(erro).__name__=='RespostaMalformada' else 'falha_provedor',
                erro=type(erro).__name__,detalhe=erro.detalhe,respostas=respostas(erro))
        salvar()
    if not interromper and 'comparacao' in etapas:
        # Um mesmo caso em duas abordagens; não chama os seis novamente.
        id='D2-S02'
        texto=(config.raiz/f'dados/originais/desafio-2/{id}.txt').read_text(encoding='utf-8')
        cliente.contexto=id+':comparacao'
        try:
            comparacao=comparar_sintatico_e_esquema(texto,origem=id,cliente=cliente,config=config)
            for abordagem in comparacao['abordagens'].values():
                if abordagem['esquema_valido']:
                    s=SolicitacaoEstruturada.model_validate_json(abordagem['saida'])
                    abordagem['problemas_regras']=validar_regras(s,texto,config=config)
            relatorio['comparacoes'].append(comparacao)
        except ErroLLM as erro:
            relatorio['comparacoes'].append({'status':'bloqueado','erro':type(erro).__name__,'mensagem':str(erro)})
            interromper=True
    execucao.update(fim=datetime.now(timezone.utc).isoformat(),status='interrompido' if interromper else 'concluido')
    salvar()
    print(json.dumps(relatorio['consumo'],ensure_ascii=False),flush=True)
    return relatorio


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--casos',nargs='+')
    parser.add_argument('--etapas',nargs='+',choices=['extracao','compreensao','comparacao','bloqueio'])
    parser.add_argument('--saida',type=Path)
    parser.add_argument('--ledger',type=Path)
    args=parser.parse_args()
    executar(**vars(args))


if __name__=='__main__':
    main()
