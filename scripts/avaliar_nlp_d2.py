"""Evidências de RF14/RF15: offline por padrão; --real requer chave e usa só S01/S02.

python -m scripts.avaliar_nlp_d2 [--real] [--saida caminho.json]
Nenhum gabarito é alterado. Respostas simuladas não medem qualidade de modelo.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from src.config import carregar_config, carregar_chave
from src.llm_client import ClienteLLM, ErroLLM
from src.metrics import acuracia_categorias
from src.nlp import compreender, comparar_sintatico_e_esquema, extrair_solicitacao, validar_regras
from src.privacidade import mascarar, ocultar_segredos
from scripts.validar_dados_d2 import validar


def avaliar(*, real=False):
    config=carregar_config()
    chave=carregar_chave() if real else None
    relatorio={'modo':'real' if real else 'simulado', 'executado_em':datetime.now(timezone.utc).isoformat(),
               'dados':validar(config),'casos':[], 'limitacoes':[]}
    if real and not chave:
        relatorio.update(status='bloqueado', motivo='OPENAI_API_KEY indisponível; nenhuma chamada real realizada.')
        return relatorio
    if not real:
        from testes.falsos import SDKFalso, resposta
        from testes.referencias_nlp import RESUMOS
        relatorio['limitacoes'].append('SDK falso alimentado por referências prévias; mede integração e validações, não qualidade de um modelo.')
    ids=[f'D2-S{i:02}' for i in range(1,3 if real else 7)]
    obtidas={}
    esperadas={}
    for id in ids:
        g=json.loads((config.raiz/f'dados/gabaritos/{id}.json').read_text(encoding='utf-8'))
        if g['solicitacao_esperada']['categoria'] is not None:
            esperadas[id]=g['solicitacao_esperada']['categoria']
    for id in ids:
        g=json.loads((config.raiz/f'dados/gabaritos/{id}.json').read_text(encoding='utf-8'))
        texto=(config.raiz/g['arquivo']).read_text(encoding='utf-8')
        esperado={**g['solicitacao_esperada'],'entidades':g['entidades_esperadas']}
        cliente=ClienteLLM(config,chave=chave) if real else ClienteLLM(config,chave='simulacao',sdk=SDKFalso(respostas=[resposta(json.dumps(esperado,ensure_ascii=False)),resposta(json.dumps({'resumo':RESUMOS[id],'inferencias':[]},ensure_ascii=False))]))
        caso={'id':id}
        try:
            s=extrair_solicitacao(texto,origem=id,cliente=cliente,config=config)
            ficha=compreender(texto,s.valor,origem=id,cliente=cliente,config=config)
            obtidas[id]=s.valor.categoria
            resumo=ficha.valor.resumo
            entidades_omitidas={};entidades_incorretas={}
            for tipo, valores in g['entidades_esperadas'].items():
                atuais=getattr(s.valor.entidades,tipo)
                entidades_omitidas[tipo]=sorted(set(valores)-set(atuais))
                entidades_incorretas[tipo]=sorted(set(atuais)-set(valores))
            respostas=s.respostas+ficha.respostas
            caso.update(status='valido',solicitacao=s.valor.model_dump(), ficha=ficha.valor.model_dump(),
                palavras_resumo=len(resumo.split()), regras=validar_regras(s.valor,texto,config=config),
                fatos_essenciais_omitidos=[f for f in g['fatos_essenciais'] if f.casefold() not in resumo.casefold()],
                entidades_omitidas=entidades_omitidas, entidades_incorretas=entidades_incorretas,
                fatos_sem_suporte='Passagens não literais recusadas por código; seleção e contexto exigem revisão humana.',
                abstencao_categoria_correta=(s.valor.categoria is None and esperado['categoria'] is None),
                chamadas=len(respostas), tokens_entrada=sum(r.tokens_entrada or 0 for r in respostas),
                tokens_saida=sum(r.tokens_saida or 0 for r in respostas),
                custo_estimado_usd=sum(r.custo_estimado_usd or 0 for r in respostas),
                duracao_s=sum(r.duracao_s for r in respostas),
                prompts=[{'id':r.prompt.identificador,'hash':r.prompt.hash} for r in [s,ficha]])
        except ErroLLM as erro:
            caso.update(status='bloqueado',erro=type(erro).__name__,mensagem=str(erro))
            relatorio['casos'].append(caso)
            if real:
                relatorio['limitacoes'].append('Execução real interrompida na primeira falha para evitar consumo repetitivo.')
                break
            raise
        relatorio['casos'].append(caso)
    if not real:
        esperado,texto_esperado = esperado, texto
        invalido={**esperado,'necessita_revisao':'true','extra':'indevida'}
        del invalido['pedido']
        cliente=ClienteLLM(config,chave='simulacao',sdk=SDKFalso(respostas=[resposta(json.dumps(invalido)),resposta(json.dumps(esperado))]))
        relatorio['comparacao_json_esquema']=comparar_sintatico_e_esquema(texto_esperado,origem=ids[-1],cliente=cliente,config=config)
    elif relatorio['casos'] and all(c['status']=='valido' for c in relatorio['casos']):
        try:
            relatorio['comparacao_json_esquema']=comparar_sintatico_e_esquema(texto,origem=ids[-1],cliente=cliente,config=config)
        except ErroLLM as erro:
            relatorio['comparacao_json_esquema']={'status':'bloqueado','erro':type(erro).__name__}
    relatorio['acuracia_categorias']=acuracia_categorias(obtidas,esperadas)
    relatorio['cobertura_categorias']={'com_rotulo_definido':len(esperadas),'casos_planejados':len(ids),'casos_executados':len(relatorio['casos'])}
    relatorio['limitacoes'].append('Caso ambíguo usa categoria null e revisão; não entra na acurácia de categorias definidas. A abstenção é avaliada separadamente.')
    relatorio['status']='concluido' if all(c['status']=='valido' for c in relatorio['casos']) else 'bloqueado'
    return relatorio


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--real',action='store_true')
    parser.add_argument('--saida',type=Path)
    args=parser.parse_args()
    config=carregar_config()
    resultado=avaliar(real=args.real)
    caminho=args.saida or config.caminho('metricas')/('integrante-1-real.json' if args.real else 'integrante-1-simulado.json')
    caminho.parent.mkdir(parents=True,exist_ok=True)
    seguro=ocultar_segredos(mascarar(json.dumps(resultado,ensure_ascii=False,indent=2),config.dados['privacidade']['mascarar_antes_de_enviar'])[0],[])
    caminho.write_text(seguro+'\n',encoding='utf-8')
    print(f"{resultado['modo']}: {resultado['status']}; evidência: {caminho}")


if __name__=='__main__':
    main()
