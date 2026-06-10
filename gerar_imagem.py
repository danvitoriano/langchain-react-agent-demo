import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from langchain_community.utilities.dalle_image_generator import DallEAPIWrapper
from langchain_core.tools import Tool

OUTPUT_DIR = Path("generated_images")


def criar_ferramenta_gerar_imagem() -> Tool:
    def _criar_cliente_dalle() -> DallEAPIWrapper:
        modelo = os.getenv("DALLE_MODEL", "dall-e-3")
        tamanho = os.getenv("DALLE_SIZE", "1024x1024")

        kwargs: dict[str, str] = {"model": modelo, "size": tamanho}
        if modelo == "dall-e-3":
            kwargs["quality"] = os.getenv("DALLE_QUALITY", "standard")

        return DallEAPIWrapper(**kwargs)

    def gerar_e_salvar(prompt: str) -> str:
        dalle = _criar_cliente_dalle()
        url = dalle.run(prompt)
        if not url or url == "No image was generated":
            return "Não foi possível gerar a imagem."

        OUTPUT_DIR.mkdir(exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        arquivo = OUTPUT_DIR / f"imagem_{timestamp}.png"

        urllib.request.urlretrieve(url.split("\n")[0], arquivo)
        return f"Imagem gerada e salva em: {arquivo.resolve()}"

    return Tool(
        name="gerar_imagem",
        description=(
            "Gera uma imagem a partir de uma descrição em texto usando DALL-E. "
            "Use quando o usuário pedir para criar, desenhar ou visualizar uma imagem. "
            "Entrada: prompt descritivo da imagem desejada."
        ),
        func=gerar_e_salvar,
    )
