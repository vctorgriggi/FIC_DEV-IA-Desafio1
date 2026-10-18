import { useEffect, useState } from "react";
import { api, urlArquivo, type Painel as DadosPainel } from "../api";
import { Carregando, dataHora, Erro, ROTULOS_MODALIDADE, ROTULOS_STATUS, Status } from "../comum";

const TEMPO_ESTIMADO: Record<string, string> = { texto: "cerca de 30 s", audio: "cerca de 40 s", imagem: "cerca de 30 s" };

export function Painel({ ir }: { ir: (rota: string) => void }) {
  const [dados, setDados] = useState<DadosPainel | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState<string | null>(null);

  const carregar = () => api.painel().then(setDados).catch((e: Error) => setErro(e.message));
  useEffect(() => {
    carregar();
  }, []);

  async function processar(caso: string, modalidade: string) {
    setErro(null);
    setOcupado(`Processando ${caso}: leitura e extração dos campos, ${TEMPO_ESTIMADO[modalidade]}…`);
    try {
      const resultado = await api.processar(caso);
      ir(resultado.confirmacao ? `/confirmar/${resultado.confirmacao}` : `/minuta/${resultado.minuta}`);
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setOcupado(null);
    }
  }

  async function gerarPeca(caso: string) {
    if (!window.confirm("Gerar a peça visual usa o modelo de imagem pago (cerca de US$ 0,03). Continuar?")) return;
    setErro(null);
    setOcupado("Gerando a peça visual…");
    try {
      const { peca } = await api.gerarPeca(caso);
      ir(`/peca/${peca}`);
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setOcupado(null);
    }
  }

  if (!dados) return erro ? <Erro mensagem={erro} /> : <Carregando texto="Carregando…" />;
  const { resumo } = dados;
  const porcentagem = (valor: number | null) => (valor === null ? "—" : `${Math.round(valor * 100)}%`);

  return (
    <div className="pagina">
      <Erro mensagem={erro} />
      {ocupado && <Carregando texto={ocupado} />}

      <section className="indicadores" aria-label="Indicadores">
        <div className="indicador">
          <span className="indicador__valor">{resumo.por_status.aguardando_revisao ?? 0}</span>
          <span className="indicador__rotulo">minutas aguardando revisão</span>
        </div>
        <div className="indicador">
          <span className="indicador__valor">{resumo.revisadas}</span>
          <span className="indicador__rotulo">minutas revisadas</span>
        </div>
        <div className="indicador">
          <span className="indicador__valor">{porcentagem(resumo.taxa_aprovacao_sem_correcao)}</span>
          <span className="indicador__rotulo">aprovação sem correção</span>
        </div>
        <div className="indicador">
          <span className="indicador__valor">{porcentagem(resumo.taxa_aprovacao_com_correcao)}</span>
          <span className="indicador__rotulo">aprovação com correção</span>
        </div>
      </section>

      {dados.pendentes.length > 0 && (
        <section className="bloco bloco--destaque">
          <h2>Aguardando sua confirmação</h2>
          <p className="bloco__ajuda">Dados críticos lidos de áudio ou imagem precisam ser conferidos antes da minuta.</p>
          <ul className="lista">
            {dados.pendentes.map((p) => (
              <li key={p.id_execucao} className="lista__item">
                <span>
                  <strong>{p.caso_id}</strong> · {ROTULOS_MODALIDADE[p.modalidade]} · {dataHora(p.preparado_em)}
                </span>
                <button className="botao botao--primario" onClick={() => ir(`/confirmar/${p.id_execucao}`)}>
                  Conferir
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="bloco">
        <h2>Casos</h2>
        <div className="grade">
          {dados.casos.map((caso) => (
            <article key={caso.id} className="cartao">
              <span className={`selo selo--${caso.modalidade}`}>{ROTULOS_MODALIDADE[caso.modalidade]}</span>
              <h3>{caso.id}</h3>
              <p className="cartao__arquivo">{caso.arquivo}</p>
              <div className="cartao__acoes">
                <button className="botao botao--primario" disabled={!!ocupado} onClick={() => processar(caso.id, caso.modalidade)}>
                  Processar
                </button>
                <button className="botao" disabled={!!ocupado} onClick={() => gerarPeca(caso.id)}>
                  Gerar peça visual
                </button>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="bloco">
        <h2>Minutas</h2>
        {dados.minutas.length === 0 ? (
          <p className="vazio">Nenhuma minuta ainda. Processe um caso.</p>
        ) : (
          <table className="tabela">
            <thead>
              <tr>
                <th>Caso</th>
                <th>Gerada em</th>
                <th>Situação</th>
                <th>Conferência com o gabarito</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {dados.minutas.map((m) => (
                <tr key={m.id_execucao}>
                  <td>
                    <strong>{m.caso_id}</strong>
                    <span className="tabela__id">{m.id_execucao}</span>
                  </td>
                  <td>{dataHora(m.gerada_em)}</td>
                  <td>
                    <Status valor={m.status} />
                  </td>
                  <td>
                    {m.falhas === null || m.falhas === undefined ? (
                      <span className="neutro">sem gabarito</span>
                    ) : m.falhas.length === 0 ? (
                      <span className="ok">confere</span>
                    ) : (
                      <span className="alerta">{m.falhas.length} divergência(s)</span>
                    )}
                  </td>
                  <td className="tabela__acao">
                    <button className="botao" onClick={() => ir(`/minuta/${m.id_execucao}`)}>
                      {m.status === "aguardando_revisao" ? "Revisar" : "Ver"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="bloco">
        <h2>Peças visuais</h2>
        {dados.pecas.length === 0 ? (
          <p className="vazio">Nenhuma peça ainda. Use "Gerar peça visual" em um caso.</p>
        ) : (
          <div className="grade">
            {dados.pecas.map((p) => (
              <button key={p.id_execucao} className="miniatura" onClick={() => ir(`/peca/${p.id_execucao}`)}>
                <img src={urlArquivo(p.imagem)} alt={`Peça visual do caso ${p.caso_id}`} />
                <span className="miniatura__legenda">
                  <strong>{p.caso_id}</strong>
                  <span>{ROTULOS_STATUS[p.status] ?? p.status}</span>
                </span>
              </button>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
