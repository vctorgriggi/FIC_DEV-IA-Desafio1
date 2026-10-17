from types import SimpleNamespace


def interacao(texto="ok", *, entrada=10, saida=5, pensamento=0, audio=None, imagem=None):
    uso = SimpleNamespace(total_input_tokens=entrada, total_output_tokens=saida, total_thought_tokens=pensamento)
    return SimpleNamespace(
        output_text=texto,
        output_audio=SimpleNamespace(data=audio) if audio is not None else None,
        output_image=SimpleNamespace(data=imagem) if imagem is not None else None,
        usage=uso,
    )


class SDKFalso:
    """Imita client.interactions.create do google-genai, sem rede."""

    def __init__(self, resposta=None, erro=None):
        self.chamadas = []
        self._resposta = resposta if resposta is not None else interacao()
        self._erro = erro
        self.interactions = SimpleNamespace(create=self._criar)

    def _criar(self, **argumentos):
        self.chamadas.append(argumentos)
        if self._erro is not None:
            raise self._erro
        return self._resposta
