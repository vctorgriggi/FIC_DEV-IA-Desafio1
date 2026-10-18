import { useEffect, useState } from "react";
import { api, urlArquivo, type MinutaDetalhe } from "../api";
import { Carregando, dataHora, Erro, Markdown, ROTULOS_CAMPO, ROTULOS_DECISAO, Status, useRevisor, VisualizadorOriginal } from "../comum";

const AJUDA_DECISAO: Record<string, string> = {
  aprovar: "O texto está correto como está.",
  aprovar_com_correcao: "Você corrige o texto aqui e aprova a versão corrigida.",
  rejeitar: "Erro grave: dado errado ou inventado, instrução indevida obedecida.",
  nova_geracao: "Descarta esta minuta e pede outra ao modelo.",
};

export function RevisaoMinuta({ id, ir }: { id: string; ir: (rota: string) => void }) {
  const [minuta, setMinuta] = useState<MinutaDetalhe | null>(null);
  const [decisao, setDecisao] = useState("");
  const [justificativa, setJustificativa] = useState("");
  const [textoCorrigido, setTextoCorrigido] = useState("");
  const [revisor, setRevisor] = useRevisor();
  const [erro, setErro] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  const carregar = () =>
    api
      .minuta(id)
      .then((m) => {
        setMinuta(m);
        setTextoCorrigido(m.texto);
      })
      .catch((e: Error) => setErro(e.message));
  useEffect(() => {
    carregar();
  }, [id]);

  async function decidir(evento: React.FormEvent) {
    evento.preventDefault();
    setErro(null);
    setOcupado("Registrando a decisão…");
    try {
      await api.decidirMinuta(id, {
        decisao,
        justificativa,
        revisor,
        ...(decisao === "aprovar_com_correcao" ? { texto_corrigido: textoCorrigido } : {}),
      });
      await carregar();
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setOcupado(null);
    }
  }

  async function gerarAudio() {
    setErro(null);
    setOcupado("Gerando o áudio da minuta…");
    try {
      await api.audio(id);
      await carregar();
      setAviso("Áudio gerado.");
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setOcupado(null);
    }
  }

  async function processarDeNovo() {
    if (!minuta) return;
    setErro(null);
    setOcupado(`Processando ${minuta.caso_id} de novo…`);
    try {
      const r = await api.processar(minuta.caso_id);
      ir(r.confirmacao ? `/confirmar/${r.confirmacao}` : `/minuta/${r.minuta}`);
    } catch (e) {
      setErro((e as Error).message);
      setOcupado(null);
    }
  }

  if (!minuta) return erro ? <Erro mensagem={erro} /> : <Carregando texto="Carregando…" />;
  const aguardando = minuta.status === "aguardando_revisao";
  const aprovada = minuta.status === "aprovada" || minuta.status === "aprovada_com_correcao";

  return (
    <div className="pagina">
      <h1 className="titulo">
        Minuta <span className="titulo__sub">{minuta.caso_id}</span> <Status valor={minuta.status} />
      </h1>
      {aviso && <div className="aviso aviso--ok">{aviso}</div>}

      <div className="dividido">
        <VisualizadorOriginal caminho={minuta.arquivo_origem} />

        <section className="painel-lateral">
          <header className="painel-lateral__cabecalho">
            <h2>Minuta gerada</h2>
            <span className="tabela__id">gerada em {dataHora(minuta.gerada_em)}</span>
          </header>
          <div className="folha">
            <Markdown texto={minuta.texto} />
          </div>
        </section>
      </div>

      <div className="dividido">
        <section className="bloco">
          <h2>Campos extraídos</h2>
          <dl className="definicoes">
            {Object.keys(ROTULOS_CAMPO).map((c) => (
              <div key={c}>
                <dt>
                  {ROTULOS_CAMPO[c]}
                  {minuta.campos_corrigidos_por_humano.includes(c) && <span className="etiqueta">corrigido na confirmação</span>}
                </dt>
                <dd>{String(minuta.campos[c] ?? "")}</dd>
              </div>
            ))}
          </dl>
        </section>
        <section className="bloco">
          <h2>Conferência automática com o gabarito</h2>
          {!minuta.avaliacao ? (
            <p className="vazio">Este caso não tem gabarito.</p>
          ) : minuta.avaliacao.falhas.length === 0 ? (
            <p className="ok">Campos exatos, itens obrigatórios e itens proibidos conferem.</p>
          ) : (
            <ul className="lista-alertas">
              {minuta.avaliacao.falhas.map((f) => (
                <li key={f}>{f}</li>
              ))}
            </ul>
          )}
          <p className="bloco__ajuda">Tom, clareza e correção do texto livre são julgamento seu.</p>
        </section>
      </div>

      {aguardando ? (
        <form className="bloco decisao" onSubmit={decidir}>
          <h2>Sua decisão</h2>
          <div className="opcoes" role="radiogroup">
            {minuta.decisoes.map((d) => (
              <label key={d} className={`opcao ${decisao === d ? "opcao--marcada" : ""}`}>
                <input type="radio" name="decisao" value={d} checked={decisao === d} onChange={() => setDecisao(d)} />
                <strong>{ROTULOS_DECISAO[d]}</strong>
                <span>{AJUDA_DECISAO[d]}</span>
              </label>
            ))}
          </div>
          {decisao === "aprovar_com_correcao" && (
            <label className="campo">
              <span className="campo__rotulo">Texto corrigido (Markdown)</span>
              <textarea className="editor" value={textoCorrigido} onChange={(e) => setTextoCorrigido(e.target.value)} rows={18} />
            </label>
          )}
          <label className="campo">
            <span className="campo__rotulo">Justificativa</span>
            <textarea value={justificativa} onChange={(e) => setJustificativa(e.target.value)} rows={3} required />
          </label>
          <label className="campo">
            <span className="campo__rotulo">Revisor</span>
            <input value={revisor} onChange={(e) => setRevisor(e.target.value)} placeholder="Nome ou função" required />
          </label>
          <Erro mensagem={erro} />
          {ocupado ? (
            <Carregando texto={ocupado} />
          ) : (
            <button className="botao botao--primario botao--largo" type="submit" disabled={!decisao}>
              Registrar decisão
            </button>
          )}
          <p className="bloco__ajuda">Nada é enviado ao cidadão: a decisão só fica registrada.</p>
        </form>
      ) : (
        <section className="bloco decisao">
          <h2>Decisão registrada</h2>
          {minuta.revisao && (
            <p>
              <strong>{ROTULOS_DECISAO[minuta.revisao.decisao]}</strong> por {minuta.revisao.revisor} em{" "}
              {dataHora(minuta.revisao.data_hora)}: {minuta.revisao.justificativa}
            </p>
          )}
          <Erro mensagem={erro} />
          {ocupado && <Carregando texto={ocupado} />}
          <div className="cartao__acoes">
            {aprovada &&
              (minuta.audio ? (
                <audio controls src={urlArquivo(minuta.audio)} />
              ) : (
                <button className="botao" onClick={gerarAudio} disabled={!!ocupado}>
                  Gerar áudio da minuta (acessibilidade)
                </button>
              ))}
            {!aprovada && (
              <button className="botao botao--primario" onClick={processarDeNovo} disabled={!!ocupado}>
                Processar o caso de novo
              </button>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
