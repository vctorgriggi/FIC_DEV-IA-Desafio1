import { useEffect, useState } from "react";
import { api, type Execucao } from "../api";
import { Carregando, contemTrechoIncerto, Erro, ROTULOS_CAMPO, useRevisor, VisualizadorOriginal } from "../comum";

export function Confirmacao({ id, ir }: { id: string; ir: (rota: string) => void }) {
  const [execucao, setExecucao] = useState<Execucao | null>(null);
  const [valores, setValores] = useState<Record<string, string>>({});
  const [revisor, setRevisor] = useRevisor();
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    api
      .execucao(id)
      .then((e) => {
        setExecucao(e);
        setValores(Object.fromEntries(e.campos_criticos.map((c) => [c, String(e.campos[c] ?? "")])));
      })
      .catch((e: Error) => setErro(e.message));
  }, [id]);

  async function confirmar(evento: React.FormEvent) {
    evento.preventDefault();
    setErro(null);
    setEnviando(true);
    try {
      const { minuta } = await api.confirmar(id, valores, revisor);
      ir(`/minuta/${minuta}`);
    } catch (e) {
      setErro((e as Error).message);
      setEnviando(false);
    }
  }

  if (!execucao) return erro ? <Erro mensagem={erro} /> : <Carregando texto="Carregando…" />;
  if (execucao.status !== "aguardando_confirmacao") {
    return <div className="aviso">Esta execução já foi confirmada. Veja a minuta no painel.</div>;
  }
  const original = (campo: string) => String(execucao.campos[campo] ?? "");

  return (
    <div className="pagina">
      <h1 className="titulo">
        Conferir dados críticos <span className="titulo__sub">{execucao.caso_id}</span>
      </h1>
      <p className="bloco__ajuda">
        Compare cada campo com o documento original ao lado. O modelo pode errar sem marcar a dúvida: confirme olhando o
        original, não só o valor lido.
      </p>

      <div className="dividido">
        <VisualizadorOriginal caminho={execucao.arquivo_origem} />

        <form className="painel-lateral" onSubmit={confirmar}>
          {execucao.trechos_incertos.length > 0 && (
            <div className="aviso aviso--atencao">
              <strong>Trechos que a leitura marcou como incertos</strong>
              <ul>
                {execucao.trechos_incertos.map((t) => (
                  <li key={t}>{t}</li>
                ))}
              </ul>
            </div>
          )}

          {execucao.campos_criticos.map((campo) => {
            const incerto = contemTrechoIncerto(original(campo), execucao.trechos_incertos);
            const alterado = valores[campo] !== original(campo);
            return (
              <label key={campo} className="campo">
                <span className="campo__rotulo">
                  {ROTULOS_CAMPO[campo] ?? campo}
                  {incerto && <span className="etiqueta etiqueta--alerta">contém trecho incerto</span>}
                  {alterado && <span className="etiqueta">corrigido por você (lido: {original(campo)})</span>}
                </span>
                <input value={valores[campo] ?? ""} onChange={(e) => setValores({ ...valores, [campo]: e.target.value })} />
              </label>
            );
          })}

          <details className="detalhes">
            <summary>Outros campos extraídos</summary>
            <dl className="definicoes">
              {["assunto", "pedido", "categoria"].map((c) => (
                <div key={c}>
                  <dt>{ROTULOS_CAMPO[c]}</dt>
                  <dd>{original(c)}</dd>
                </div>
              ))}
            </dl>
          </details>
          {execucao.texto_bruto && (
            <details className="detalhes">
              <summary>Texto lido pelo modelo</summary>
              <pre className="original__texto">{execucao.texto_bruto}</pre>
            </details>
          )}

          <label className="campo">
            <span className="campo__rotulo">Quem conferiu</span>
            <input value={revisor} onChange={(e) => setRevisor(e.target.value)} placeholder="Nome ou função" required />
          </label>
          <Erro mensagem={erro} />
          {enviando ? (
            <Carregando texto="Gerando a minuta, cerca de 15 s…" />
          ) : (
            <button className="botao botao--primario botao--largo" type="submit">
              Confirmar e gerar minuta
            </button>
          )}
        </form>
      </div>
    </div>
  );
}
