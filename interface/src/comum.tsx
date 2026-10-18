import DOMPurify from "dompurify";
import { marked } from "marked";
import { useEffect, useState } from "react";
import { urlArquivo } from "./api";

export const ROTULOS_STATUS: Record<string, string> = {
  aguardando_revisao: "Aguardando revisão",
  aguardando_confirmacao: "Aguardando confirmação",
  aprovada: "Aprovada",
  aprovada_com_correcao: "Aprovada com correção",
  rejeitada: "Rejeitada",
  nova_geracao_solicitada: "Nova geração pedida",
};

export const ROTULOS_DECISAO: Record<string, string> = {
  aprovar: "Aprovar",
  aprovar_com_correcao: "Aprovar com correção",
  rejeitar: "Rejeitar",
  nova_geracao: "Pedir nova geração",
};

export const ROTULOS_MODALIDADE: Record<string, string> = { texto: "Texto", audio: "Áudio", imagem: "Imagem" };

export const ROTULOS_CAMPO: Record<string, string> = {
  protocolo: "Protocolo",
  data: "Data",
  solicitante: "Solicitante",
  assunto: "Assunto",
  pedido: "Pedido",
  categoria: "Categoria",
};

export function Status({ valor }: { valor: string }) {
  return <span className={`status status--${valor}`}>{ROTULOS_STATUS[valor] ?? valor}</span>;
}

export function dataHora(iso: string) {
  return new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

export function Erro({ mensagem }: { mensagem: string | null }) {
  return mensagem ? (
    <div className="aviso aviso--erro" role="alert">
      {mensagem}
    </div>
  ) : null;
}

export function Carregando({ texto }: { texto: string }) {
  return (
    <div className="carregando" role="status">
      <span className="carregando__roda" aria-hidden="true" />
      {texto}
    </div>
  );
}

/** Mesma normalização de src/comparacao.py: sem caixa nem acento, pontuação de dados preservada. */
function normalizar(texto: string) {
  return texto
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9./@-]+/g, " ")
    .trim();
}

export function contemTrechoIncerto(valor: string, trechos: string[]) {
  const alvo = normalizar(valor);
  return trechos.some((trecho) => {
    const lido = normalizar(trecho.split(" — ")[0]);
    return lido !== "" && alvo.includes(lido);
  });
}

export function useRevisor(): [string, (nome: string) => void] {
  const [revisor, setRevisor] = useState(() => {
    try {
      return localStorage.getItem("revisor") ?? "";
    } catch {
      return "";
    }
  });
  const atualizar = (nome: string) => {
    setRevisor(nome);
    try {
      localStorage.setItem("revisor", nome);
    } catch {
      // sem armazenamento local: o nome só não fica lembrado
    }
  };
  return [revisor, atualizar];
}

/** A minuta é Markdown gerado em parte pelo modelo: o HTML passa pelo DOMPurify antes de entrar na página. */
export function Markdown({ texto }: { texto: string }) {
  // Caminhos relativos à pasta da minuta (../../dados/...) viram a rota de arquivos da API.
  const ajustado = texto.replace(/\]\((?:\.\.\/)+((?:dados|resultados)\/[^)\s]+)\)/g, (_, caminho) => `](${urlArquivo(caminho)})`);
  const html = DOMPurify.sanitize(marked.parse(ajustado, { async: false }));
  return <div className="markdown" dangerouslySetInnerHTML={{ __html: html }} />;
}

export function VisualizadorOriginal({ caminho }: { caminho: string }) {
  const extensao = caminho.split(".").pop()?.toLowerCase() ?? "";
  const url = urlArquivo(caminho);
  const [texto, setTexto] = useState<string | null>(null);

  useEffect(() => {
    if (extensao === "txt") {
      fetch(url)
        .then((r) => r.text())
        .then(setTexto)
        .catch(() => setTexto("Não foi possível abrir o arquivo."));
    }
  }, [url, extensao]);

  let conteudo;
  if (extensao === "pdf") conteudo = <iframe className="original__pdf" src={url} title="Documento original" />;
  else if (["png", "jpg", "jpeg", "webp"].includes(extensao)) conteudo = <img className="original__imagem" src={url} alt="Imagem original" />;
  else if (["mp3", "wav", "m4a", "ogg", "flac"].includes(extensao)) conteudo = <audio controls src={url} className="original__audio" />;
  else conteudo = <pre className="original__texto">{texto ?? "Carregando…"}</pre>;

  return (
    <section className="painel-lateral original">
      <header className="painel-lateral__cabecalho">
        <h2>Original</h2>
        <a href={url} target="_blank" rel="noreferrer">
          Abrir em nova aba
        </a>
      </header>
      <p className="original__caminho">{caminho}</p>
      {conteudo}
    </section>
  );
}
