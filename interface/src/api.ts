export interface Caso {
  id: string;
  modalidade: "texto" | "audio" | "imagem";
  arquivo: string;
  gabarito: string;
}

export interface Pendente {
  id_execucao: string;
  caso_id: string;
  modalidade: string;
  preparado_em: string;
}

export interface Revisao {
  decisao: string;
  justificativa: string;
  revisor: string;
  data_hora: string;
}

export interface MinutaResumo {
  id_execucao: string;
  caso_id: string;
  modalidade: string;
  arquivo_origem: string;
  arquivo_minuta: string;
  gerada_em: string;
  status: string;
  falhas: string[] | null;
  revisao?: Revisao;
}

export interface Peca {
  id_execucao: string;
  caso_id: string;
  imagem: string;
  ilustracao_original: string | null;
  prompt: string;
  modelo: string;
  data_geracao: string;
  nota_proveniencia: string;
  status: string;
  revisao?: Revisao & { checklist: Record<string, boolean> };
  checklist_peca?: Record<string, string>;
}

export interface Painel {
  casos: Caso[];
  pendentes: Pendente[];
  minutas: MinutaResumo[];
  pecas: Peca[];
  resumo: {
    por_status: Record<string, number>;
    revisadas: number;
    taxa_aprovacao_sem_correcao: number | null;
    taxa_aprovacao_com_correcao: number | null;
  };
  checklist_peca: Record<string, string>;
}

export type Campos = Record<string, string | string[] | boolean>;

export interface Execucao {
  id_execucao: string;
  caso_id: string;
  modalidade: string;
  arquivo_origem: string;
  campos: Campos;
  trechos_incertos: string[];
  campos_criticos: string[];
  texto_bruto?: string;
  texto_revisado?: string;
  status: string;
}

export interface Avaliacao {
  falhas: string[];
  campos: Record<string, { esperado: string; obtido: string; confere: boolean | null }>;
}

export interface MinutaDetalhe extends MinutaResumo {
  texto: string;
  campos: Campos;
  campos_corrigidos_por_humano: string[];
  avaliacao: Avaliacao | null;
  decisoes: string[];
  audio?: string;
}

async function chamar<T>(caminho: string, corpo?: unknown): Promise<T> {
  const resposta = await fetch(caminho, {
    method: corpo === undefined ? "GET" : "POST",
    headers: corpo === undefined ? undefined : { "Content-Type": "application/json" },
    body: corpo === undefined ? undefined : JSON.stringify(corpo),
  });
  const dados = await resposta.json().catch(() => ({}));
  if (!resposta.ok) {
    throw new Error(dados.erro ?? dados.detail ?? `Erro ${resposta.status}`);
  }
  return dados as T;
}

export const api = {
  painel: () => chamar<Painel>("/api/painel"),
  processar: (caso: string) => chamar<{ confirmacao?: string; minuta?: string }>(`/api/casos/${caso}/processar`, {}),
  execucao: (id: string) => chamar<Execucao>(`/api/execucoes/${id}`),
  confirmar: (id: string, campos: Record<string, string>, revisor: string) =>
    chamar<{ minuta: string }>(`/api/execucoes/${id}/confirmar`, { campos, revisor }),
  descartar: (id: string, justificativa: string, revisor: string) =>
    chamar<{ descartada: string }>(`/api/execucoes/${id}/descartar`, { justificativa, revisor }),
  minuta: (id: string) => chamar<MinutaDetalhe>(`/api/minutas/${id}`),
  decidirMinuta: (id: string, corpo: { decisao: string; justificativa: string; revisor: string; texto_corrigido?: string }) =>
    chamar<MinutaResumo>(`/api/minutas/${id}/decisao`, corpo),
  audio: (id: string) => chamar<{ audio: string }>(`/api/minutas/${id}/audio`, {}),
  gerarPeca: (caso: string) => chamar<{ peca: string }>("/api/pecas", { caso_id: caso }),
  peca: (id: string) => chamar<Peca>(`/api/pecas/${id}`),
  decidirPeca: (id: string, corpo: { checklist: Record<string, boolean>; decisao: string; justificativa: string; revisor: string }) =>
    chamar<Peca>(`/api/pecas/${id}/decisao`, corpo),
};

export const urlArquivo = (caminho: string) => `/api/arquivo?caminho=${encodeURIComponent(caminho)}`;
