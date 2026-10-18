import { useEffect, useState } from "react";
import { api, urlArquivo, type Peca } from "../api";
import { Carregando, dataHora, Erro, ROTULOS_DECISAO, Status, useRevisor } from "../comum";

const DECISOES_PECA = ["aprovar", "rejeitar", "nova_geracao"];

export function RevisaoPeca({ id, ir }: { id: string; ir: (rota: string) => void }) {
  const [peca, setPeca] = useState<Peca | null>(null);
  const [checklist, setChecklist] = useState<Record<string, boolean | undefined>>({});
  const [decisao, setDecisao] = useState("");
  const [justificativa, setJustificativa] = useState("");
  const [revisor, setRevisor] = useRevisor();
  const [erro, setErro] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState<string | null>(null);

  const carregar = () => api.peca(id).then(setPeca).catch((e: Error) => setErro(e.message));
  useEffect(() => {
    carregar();
  }, [id]);

  if (!peca) return erro ? <Erro mensagem={erro} /> : <Carregando texto="Carregando…" />;
  const itens = Object.entries(peca.checklist_peca ?? {});
  const respondido = itens.every(([chave]) => checklist[chave] !== undefined);
  const tudoOk = itens.every(([chave]) => checklist[chave] === true);
  const aguardando = peca.status === "aguardando_revisao";

  async function decidir(evento: React.FormEvent) {
    evento.preventDefault();
    setErro(null);
    setOcupado("Registrando a decisão…");
    try {
      await api.decidirPeca(id, { checklist: checklist as Record<string, boolean>, decisao, justificativa, revisor });
      await carregar();
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setOcupado(null);
    }
  }

  async function gerarOutra() {
    if (!peca || !window.confirm("Gerar outra peça usa o modelo de imagem pago (cerca de US$ 0,03). Continuar?")) return;
    setOcupado("Gerando a peça visual…");
    try {
      const { peca: nova } = await api.gerarPeca(peca.caso_id);
      ir(`/peca/${nova}`);
    } catch (e) {
      setErro((e as Error).message);
      setOcupado(null);
    }
  }

  return (
    <div className="pagina">
      <h1 className="titulo">
        Peça visual <span className="titulo__sub">{peca.caso_id}</span> <Status valor={peca.status} />
      </h1>

      <div className="dividido">
        <section className="painel-lateral">
          <header className="painel-lateral__cabecalho">
            <h2>Peça</h2>
            <a href={urlArquivo(peca.imagem)} target="_blank" rel="noreferrer">
              Abrir em tamanho real
            </a>
          </header>
          <img className="peca" src={urlArquivo(peca.imagem)} alt={`Peça visual do caso ${peca.caso_id}`} />
        </section>

        <div className="painel-lateral">
          <div className="aviso">
            <strong>Proveniência</strong>
            <p>{peca.nota_proveniencia}</p>
            <p className="tabela__id">
              {peca.modelo} · {dataHora(peca.data_geracao)}
            </p>
          </div>
          <details className="detalhes">
            <summary>Prompt enviado ao modelo</summary>
            <pre className="original__texto">{peca.prompt}</pre>
          </details>
          {peca.ilustracao_original && (
            <details className="detalhes">
              <summary>Ilustração original do modelo</summary>
              <img className="peca" src={urlArquivo(peca.ilustracao_original)} alt="Ilustração original gerada pelo modelo" />
            </details>
          )}

          {aguardando ? (
            <form onSubmit={decidir}>
              <h2>Checklist</h2>
              {itens.map(([chave, pergunta]) => (
                <fieldset key={chave} className="checklist__item">
                  <legend>{pergunta}</legend>
                  {[true, false].map((valor) => (
                    <label key={String(valor)} className={`pilula ${checklist[chave] === valor ? "pilula--marcada" : ""}`}>
                      <input
                        type="radio"
                        name={chave}
                        checked={checklist[chave] === valor}
                        onChange={() => setChecklist({ ...checklist, [chave]: valor })}
                      />
                      {valor ? "Sim" : "Não"}
                    </label>
                  ))}
                </fieldset>
              ))}

              <h2>Sua decisão</h2>
              <div className="opcoes opcoes--compactas" role="radiogroup">
                {DECISOES_PECA.map((d) => {
                  const bloqueada = d === "aprovar" && !tudoOk;
                  return (
                    <label key={d} className={`opcao ${decisao === d ? "opcao--marcada" : ""} ${bloqueada ? "opcao--bloqueada" : ""}`}>
                      <input type="radio" name="decisao" value={d} disabled={bloqueada} checked={decisao === d} onChange={() => setDecisao(d)} />
                      <strong>{ROTULOS_DECISAO[d]}</strong>
                      {bloqueada && <span>Só com todos os itens do checklist em "Sim".</span>}
                    </label>
                  );
                })}
              </div>
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
                <button className="botao botao--primario botao--largo" type="submit" disabled={!respondido || !decisao}>
                  Registrar decisão
                </button>
              )}
            </form>
          ) : (
            <div className="bloco decisao">
              <h2>Decisão registrada</h2>
              {peca.revisao && (
                <>
                  <p>
                    <strong>{ROTULOS_DECISAO[peca.revisao.decisao]}</strong> por {peca.revisao.revisor} em{" "}
                    {dataHora(peca.revisao.data_hora)}: {peca.revisao.justificativa}
                  </p>
                  <ul className="lista-checklist">
                    {itens.map(([chave, pergunta]) => (
                      <li key={chave}>
                        {peca.revisao!.checklist[chave] ? "✓" : "✗"} {pergunta}
                      </li>
                    ))}
                  </ul>
                </>
              )}
              <Erro mensagem={erro} />
              {ocupado ? (
                <Carregando texto={ocupado} />
              ) : (
                peca.status !== "aprovada" && (
                  <button className="botao botao--primario" onClick={gerarOutra}>
                    Gerar outra peça
                  </button>
                )
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
