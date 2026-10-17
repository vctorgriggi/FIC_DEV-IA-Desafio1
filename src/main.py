"""Ponto de entrada (RF01): python -m src.main <comando>."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import fluxo
from .audit import Auditoria, agora_iso
from .config import CasoInexistente, Config, carregar_chave, carregar_config, versoes
from .entradas import ArquivoInvalido, validar_arquivo
from .llm_client import ClienteLLM, ErroLLM
from .revisao import RevisaoInvalida, ler_metadados, perguntar_decisao, registrar_decisao, resumo_revisoes
from .tipos import PendenteDeImplementacao

SAIDA_ERRO_USO = 1
SAIDA_ERRO_PROVEDOR = 2
SAIDA_PENDENTE = 3
SAIDA_CANCELADA = 130


def cmd_verificar(config: Config, args: argparse.Namespace) -> None:
    ambiente = {"data_hora": agora_iso(), "versoes": versoes(), "chave_configurada": carregar_chave() is not None}
    destino = config.caminho("logs") / "ambiente.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(ambiente, ensure_ascii=False, indent=2), encoding="utf-8")

    for nome, versao in ambiente["versoes"].items():
        print(f"{nome:15} {versao}")
    print(f"{'chave da API':15} {'configurada' if ambiente['chave_configurada'] else 'AUSENTE (.env)'}")
    for caso in config.dados["casos"]:
        existe = (config.raiz / caso["arquivo"]).is_file()
        print(f"caso {caso['id']:10} {caso['arquivo']} {'ok' if existe else 'ARQUIVO AUSENTE'}")
    print(f"Versões registradas em {config.relativo(destino)}")

    if args.chamar_api:
        resposta = ClienteLLM(config).gerar(modelo=config.modelo("texto"), entrada="Responda apenas: ok")
        print(f"API ok: {config.modelo('texto')} respondeu em {resposta.duracao_s}s")


def cmd_casos(config: Config, args: argparse.Namespace) -> None:
    for caso in config.dados["casos"]:
        print(f"{caso['id']:12} {caso['modalidade']:8} {caso['arquivo']}")


def cmd_processar(config: Config, args: argparse.Namespace) -> None:
    config.caso(args.caso)  # caso inexistente falha antes de exigir a chave
    metadados = fluxo.processar_caso(args.caso, config=config, cliente=ClienteLLM(config), auditoria=Auditoria(config))
    print(f"Minuta gerada: {metadados['arquivo_minuta']}")
    print(f"Revise com: python -m src.main revisar {metadados['id_execucao']}")


def cmd_revisar(config: Config, args: argparse.Namespace) -> None:
    metadados = ler_metadados(config, args.id_execucao)
    print((config.raiz / metadados["arquivo_minuta"]).read_text(encoding="utf-8"))
    print(f"\nCampos ausentes: {', '.join(metadados['campos_ausentes']) or 'nenhum'}")
    decisao, justificativa, revisor = perguntar_decisao()
    metadados = registrar_decisao(
        config, Auditoria(config), args.id_execucao, decisao=decisao, justificativa=justificativa, revisor=revisor
    )
    print(f"Status: {metadados['status']}. Nada é enviado automaticamente ao cidadão.")


def cmd_audio_minuta(config: Config, args: argparse.Namespace) -> None:
    metadados = fluxo.sintetizar_minuta(args.id_execucao, config=config, cliente=ClienteLLM(config), auditoria=Auditoria(config))
    print(f"Áudio gerado: {metadados['audio']}")


def cmd_avaliacao(config: Config, args: argparse.Namespace) -> None:
    resumo = resumo_revisoes(config)
    for status, total in sorted(resumo["por_status"].items()):
        print(f"{status:25} {total}")
    if not resumo["revisadas"]:
        print("Nenhuma minuta revisada ainda.")
        return
    print(f"Taxa de aprovação sem correção: {resumo['taxa_aprovacao_sem_correcao']:.1%} de {resumo['revisadas']} revisadas")
    print(f"Taxa de aprovação com correção: {resumo['taxa_aprovacao_com_correcao']:.1%}")


def ler_especificacao(caminho: str) -> dict:
    try:
        return json.loads(Path(caminho).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ArquivoInvalido(f"Especificação não encontrada: {caminho}.") from None
    except json.JSONDecodeError as erro:
        raise ArquivoInvalido(f"Especificação não é JSON válido: {caminho} ({erro}).") from None


def cmd_peca_visual(config: Config, args: argparse.Namespace) -> None:
    especificacao = ler_especificacao(args.especificacao)
    imagem_base = validar_arquivo(Path(args.imagem_base), "imagem", config).caminho if args.imagem_base else None
    peca = fluxo.gerar_peca_visual(
        args.caso,
        especificacao,
        imagem_base=imagem_base,
        config=config,
        cliente=ClienteLLM(config),
        auditoria=Auditoria(config),
    )
    print(f"Peça gerada: {config.relativo(peca.caminho)}")


def montar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m src.main", description="Central Inteligente de Atendimento — Desafio 1")
    sub = parser.add_subparsers(dest="comando", required=True)

    verificar = sub.add_parser("verificar", help="mostra e registra versões, chave e arquivos dos casos")
    verificar.add_argument("--chamar-api", action="store_true", help="faz uma chamada curta para testar a chave")
    verificar.set_defaults(funcao=cmd_verificar)

    sub.add_parser("casos", help="lista os casos do config.json").set_defaults(funcao=cmd_casos)

    processar = sub.add_parser("processar", help="processa um caso até a minuta aguardando revisão")
    processar.add_argument("caso")
    processar.set_defaults(funcao=cmd_processar)

    revisar = sub.add_parser("revisar", help="aprova, rejeita ou pede nova geração de uma minuta")
    revisar.add_argument("id_execucao")
    revisar.set_defaults(funcao=cmd_revisar)

    audio = sub.add_parser("audio-minuta", help="gera o áudio de uma minuta aprovada (RF07)")
    audio.add_argument("id_execucao")
    audio.set_defaults(funcao=cmd_audio_minuta)

    sub.add_parser("avaliacao", help="contagem por status e taxa de aprovação (RF13)").set_defaults(funcao=cmd_avaliacao)

    peca = sub.add_parser("peca-visual", help="gera ou edita a peça visual de um caso (RF10)")
    peca.add_argument("caso")
    peca.add_argument("--especificacao", required=True, help="JSON com sujeito, composição, estilo, iluminação, proporção e restrições")
    peca.add_argument("--imagem-base", help="imagem a editar; sem ela, gera uma nova")
    peca.set_defaults(funcao=cmd_peca_visual)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = montar_parser().parse_args(argv)
    try:
        args.funcao(carregar_config(), args)
    except PendenteDeImplementacao as erro:
        print(f"Pendente: {erro}", file=sys.stderr)
        return SAIDA_PENDENTE
    except ErroLLM as erro:
        print(f"Erro do provedor: {erro}", file=sys.stderr)
        return SAIDA_ERRO_PROVEDOR
    except (ArquivoInvalido, CasoInexistente, RevisaoInvalida) as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return SAIDA_ERRO_USO
    except (KeyboardInterrupt, EOFError):
        print("\nOperação cancelada; nada foi registrado como decisão.", file=sys.stderr)
        return SAIDA_CANCELADA
    return 0


if __name__ == "__main__":
    sys.exit(main())
