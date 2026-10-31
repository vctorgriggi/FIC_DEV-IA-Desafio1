from types import SimpleNamespace


def resposta(texto="ok", *, entrada=10, saida=5, status="completed", motivo=None):
    """Imita o Response da Responses API."""
    return SimpleNamespace(
        output_text=texto,
        status=status,
        incomplete_details=SimpleNamespace(reason=motivo) if motivo else None,
        usage=SimpleNamespace(input_tokens=entrada, output_tokens=saida),
    )


def transcricao(texto="ok", *, idiomas=("pt",), segundos=None):
    uso = SimpleNamespace(type="duration", seconds=segundos) if segundos is not None else None
    return SimpleNamespace(text=texto, languages=[SimpleNamespace(code=c) for c in idiomas], usage=uso)


def audio(conteudo: bytes):
    return SimpleNamespace(content=conteudo)


def imagem(b64: str | None, *, texto=None, imagem_entrada=None, saida=None):
    uso = None
    if texto is not None:
        detalhes = SimpleNamespace(text_tokens=texto, image_tokens=imagem_entrada or 0)
        uso = SimpleNamespace(input_tokens=texto + (imagem_entrada or 0), input_tokens_details=detalhes, output_tokens=saida)
    return SimpleNamespace(data=[SimpleNamespace(b64_json=b64)] if b64 is not None else [], usage=uso)


class SDKFalso:
    """Imita o cliente OpenAI (responses, audio, images), sem rede.

    Toda chamada entra em `chamadas` com o nome da operação em "_operacao".
    `respostas`, se dada, é consumida em ordem; senão, toda chamada devolve `resposta`.
    """

    def __init__(self, resposta_padrao=None, erro=None, *, respostas=None):
        self.chamadas = []
        self._resposta = resposta_padrao if resposta_padrao is not None else resposta()
        self._respostas = list(respostas or [])
        self._erro = erro
        self.responses = SimpleNamespace(create=self._operacao("responses.create"))
        self.audio = SimpleNamespace(
            transcriptions=SimpleNamespace(create=self._operacao("audio.transcriptions.create")),
            speech=SimpleNamespace(create=self._operacao("audio.speech.create")),
        )
        self.images = SimpleNamespace(
            generate=self._operacao("images.generate"), edit=self._operacao("images.edit")
        )

    def _operacao(self, nome):
        def criar(**argumentos):
            self.chamadas.append({"_operacao": nome, **argumentos})
            if self._erro is not None:
                raise self._erro
            return self._respostas.pop(0) if self._respostas else self._resposta

        return criar
