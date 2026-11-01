"""Teto persistente desta avaliação, inclusive reparos e repetições de transporte.

O ledger contém somente metadados; todas as gerações passam por ClienteLLM.
Falha sem usage conserva a reserva superior em vez de assumir custo zero.
"""
import json
from pathlib import Path

from src.llm_client import ClienteLLM, ErroLLM


class OrcamentoEsgotado(ErroLLM):
    mensagem_padrao = 'Orçamento ou limite de chamadas desta validação atingido.'


class ClienteOrcamentado(ClienteLLM):
    def __init__(self, config, *, arquivo: Path, limite=1.0, sdk=None, chave=None):
        self.arquivo = arquivo
        self.ledger = json.loads(arquivo.read_text(encoding='utf-8')) if arquivo.exists() else {'limite_usd':limite,'chamadas':[]}
        self.limite = min(limite, self.ledger['limite_usd'])
        self.reserva = None
        self.contexto = 'preparacao'
        super().__init__(config, sdk=sdk, chave=chave, controle=self)

    def _salvar(self):
        self.arquivo.parent.mkdir(parents=True,exist_ok=True)
        self.arquivo.write_text(json.dumps(self.ledger,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

    @property
    def gasto(self):
        return sum(c['custo_contabilizado_usd'] for c in self.ledger['chamadas'])

    def antes_da_chamada(self):
        if self.reserva is None or self.gasto + self.reserva > self.limite or len(self.ledger['chamadas']) >= 40:
            raise OrcamentoEsgotado()
        self.ledger['chamadas'].append({'contexto':self.contexto,'modelo':self.modelo_atual,
            'custo_contabilizado_usd':self.reserva,'custo_estimado_usd':None,
            'status':'reserva_conservadora_sem_usage'})
        self._salvar()

    def registrar(self, tokens):
        # O método gerar recebe a divisão entrada/saída logo após este gancho.
        pass

    def gerar(self, **argumentos):
        modelo=argumentos['modelo']
        precos=self.config.dados['precos_usd_por_milhao_tokens'].get(modelo,{})
        if any(precos.get(k) is None for k in ('entrada','saida')):
            raise OrcamentoEsgotado('Modelo sem preços conhecidos; chamada bloqueada.')
        parametros={**self.config.dados.get('parametros_geracao',{}),**argumentos.get('parametros',{})}
        teto=parametros.get('max_output_tokens')
        if not isinstance(teto,int) or teto <= 0:
            raise OrcamentoEsgotado('Limite de saída ausente; chamada bloqueada.')
        # Bytes UTF-8 superestimam tokens de entrada; margem cobre estrutura do protocolo.
        entrada=len(json.dumps(argumentos,ensure_ascii=False).encode('utf-8'))+4096
        self.reserva=(entrada*precos['entrada'] + teto*precos['saida'])/1_000_000
        self.modelo_atual=modelo
        antes=len(self.ledger['chamadas'])
        try:
            resposta=super().gerar(**argumentos)
        except ErroLLM as erro:
            if len(self.ledger['chamadas']) > antes:
                self.ledger['chamadas'][-1]['erro']=type(erro).__name__
                self._salvar()
            raise
        registro=self.ledger['chamadas'][-1]
        registro.update(tokens_entrada=resposta.tokens_entrada,tokens_saida=resposta.tokens_saida,
            duracao_s=resposta.duracao_s,custo_estimado_usd=resposta.custo_estimado_usd,
            status='medido' if resposta.custo_estimado_usd is not None else 'reserva_conservadora_sem_usage')
        if resposta.custo_estimado_usd is not None:
            registro['custo_contabilizado_usd']=resposta.custo_estimado_usd
        self._salvar()
        return resposta
