import { useEffect, useState } from "react";
import { Confirmacao } from "./componentes/Confirmacao";
import { Painel } from "./componentes/Painel";
import { RevisaoMinuta } from "./componentes/RevisaoMinuta";
import { RevisaoPeca } from "./componentes/RevisaoPeca";

function rotaAtual() {
  return window.location.hash.replace(/^#/, "") || "/";
}

export function App() {
  const [rota, setRota] = useState(rotaAtual);

  useEffect(() => {
    const mudar = () => {
      setRota(rotaAtual());
      window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", mudar);
    return () => window.removeEventListener("hashchange", mudar);
  }, []);

  const ir = (destino: string) => {
    window.location.hash = destino;
  };
  const [, pagina, id] = rota.split("/");

  let conteudo;
  if (pagina === "confirmar" && id) conteudo = <Confirmacao key={id} id={id} ir={ir} />;
  else if (pagina === "minuta" && id) conteudo = <RevisaoMinuta key={id} id={id} ir={ir} />;
  else if (pagina === "peca" && id) conteudo = <RevisaoPeca key={id} id={id} ir={ir} />;
  else conteudo = <Painel ir={ir} />;

  return (
    <>
      <header className="topo">
        <a className="topo__marca" href="#/">
          Central de Atendimento
          <span>Desafio 1 · IA Generativa</span>
        </a>
        <nav>
          <a href="#/" aria-current={pagina ? undefined : "page"}>
            Painel
          </a>
        </nav>
      </header>
      <main>{conteudo}</main>
      <footer className="rodape">
        Protótipo com dados fictícios. Nenhuma resposta é enviada ao cidadão: toda minuta termina na decisão de uma pessoa.
      </footer>
    </>
  );
}
