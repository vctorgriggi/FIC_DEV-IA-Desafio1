import json

from src.config import RAIZ
import pytest

from src.entradas import ArquivoInvalido
from src.experimento import PROMPTS, executar_experimento, gerar_prompt_c
from src.llm_client import ClienteLLM
from testes.falsos import SDKFalso, interacao

ENTRADA = json.loads((RAIZ / "dados/experimento_rf02/entrada_texto-01.json").read_text(encoding="utf-8"))


def test_tres_prompts_com_mesmo_modelo_parametros_sistema_e_entrada(config, auditoria):
    sdk = SDKFalso(interacao("Minuta", entrada=100, saida=200))
    metricas = executar_experimento(
        ENTRADA, origem="dados/experimento_rf02/entrada_texto-01.json",
        config=config, cliente=ClienteLLM(config, chave="c", sdk=sdk), auditoria=auditoria,
    )

    assert len(sdk.chamadas) == 3
    for campo in ("model", "system_instruction", "generation_config", "timeout", "store"):
        assert len({json.dumps(c[campo], sort_keys=True) for c in sdk.chamadas}) == 1, campo
    # rindex: o prompt pode citar a etiqueta; o bloco anexado pelo sistema é o último.
    blocos = {c["input"][c["input"].rindex('<conteudo_externo origem="campos_extraidos">'):] for c in sdk.chamadas}
    assert len(blocos) == 1  # mesma entrada delimitada; só o prompt da tarefa muda
    assert ENTRADA["campos"]["protocolo"] in blocos.pop()

    assert set(metricas["resultados"]) == {"A", "B", "C"}
    for rotulo, (nome, versao) in PROMPTS.items():
        resultado = metricas["resultados"][rotulo]
        assert resultado["prompt"] == f"{nome}_v{versao}"
        assert resultado["tokens_entrada"] == 100 and resultado["custo_estimado_usd"] is not None
        assert (config.raiz / resultado["saida"]).read_text(encoding="utf-8") == "Minuta"
    pasta = config.caminho("experimentos") / metricas["id_execucao"]
    assert json.loads((pasta / "metricas.json").read_text(encoding="utf-8")) == metricas
    eventos = auditoria.eventos(caso_id="experimento-rf02")
    assert [e["versao_prompt"] for e in eventos] == ["minuta_a_v1", "minuta_b_v1", "minuta_c_v2"]


def test_prompt_c_vem_do_metaprompt_e_nao_sobrescreve(config, auditoria):
    (config.caminho("prompts") / "minuta_c_v2.md").unlink(missing_ok=True)
    sdk = SDKFalso(interacao("```markdown\n# PROMPT C\nRedija a minuta.\n```"))
    cliente = ClienteLLM(config, chave="c", sdk=sdk)
    destino = gerar_prompt_c(config=config, cliente=cliente, auditoria=auditoria)

    assert destino.read_text(encoding="utf-8") == "# PROMPT C\nRedija a minuta.\n"
    metaprompt = (config.caminho("prompts") / "metaprompt_v1.md").read_text(encoding="utf-8").strip()
    assert sdk.chamadas[0]["input"] == metaprompt
    assert auditoria.eventos(etapa="metaprompt")[0]["versao_prompt"] == "metaprompt_v1"
    with pytest.raises(ArquivoInvalido, match="já existe"):
        gerar_prompt_c(config=config, cliente=cliente, auditoria=auditoria)
