"""
Extrator principal usando OpenAI.
Envia documentos (imagens e textos) para a API e retorna dados estruturados.
"""

import base64
from pathlib import Path
from typing import Any

from openai_reader.client import OpenAIClient
from openai_reader.prompts import SYSTEM_PROMPT, VISION_USER_PROMPT, TEXT_USER_PROMPT
from openai_reader.schemas import DocumentoExtraido
from config import OPENAI_INPUT_PRICE_PER_1M, OPENAI_OUTPUT_PRICE_PER_1M
from logger import log


class ExtratorOpenAI:
    """Extrai dados estruturados de documentos usando a API da OpenAI."""

    def __init__(self, client: OpenAIClient | None = None):
        self._client = client or OpenAIClient()

    def extrair_de_imagem(self, image_path: Path) -> dict[str, Any]:
        """
        Envia imagem para a OpenAI Vision e retorna dados estruturados.
        Utiliza beta.chat.completions.parse com Pydantic para structured output.
        """
        log.info(f"OpenAI Vision | Enviando imagem: {image_path.name}")

        image_data = self._encode_image(image_path)
        media_type = self._get_media_type(image_path)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": VISION_USER_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{image_data}",
                            "detail": "high",
                        },
                    },
                ],
            },
        ]

        response = self._client.chat_completion(
            messages=messages,
            response_format=DocumentoExtraido,
        )

        return self._process_response(response)

    def extrair_de_texto(self, texto: str) -> dict[str, Any]:
        """
        Envia texto extraido de PDF digital para a OpenAI e retorna dados estruturados.
        """
        log.info(f"OpenAI Texto | Enviando texto ({len(texto)} chars)")

        prompt_texto = TEXT_USER_PROMPT.format(texto=texto[:15000])  # Limitar texto

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt_texto},
        ]

        response = self._client.chat_completion(
            messages=messages,
            response_format=DocumentoExtraido,
        )

        return self._process_response(response)

    def extrair_de_pdf_imagem(self, pages_images: list[Path]) -> dict[str, Any]:
        """
        Envia multiplas paginas de PDF como imagens para a OpenAI.
        """
        log.info(f"OpenAI Vision | Enviando {len(pages_images)} paginas de PDF")

        content: list[dict[str, Any]] = [
            {"type": "text", "text": VISION_USER_PROMPT},
        ]

        for page_img in pages_images[:10]:  # Limitar a 10 paginas
            image_data = self._encode_image(page_img)
            media_type = self._get_media_type(page_img)
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{media_type};base64,{image_data}",
                        "detail": "high",
                    },
                }
            )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ]

        response = self._client.chat_completion(
            messages=messages,
            response_format=DocumentoExtraido,
        )

        return self._process_response(response)

    def _process_response(self, response: Any) -> dict[str, Any]:
        """Processa a resposta da OpenAI e extrai os dados."""
        resultado: dict[str, Any] = {
            "dados": None,
            "tokens_entrada": 0,
            "tokens_saida": 0,
            "custo_estimado": 0.0,
            "modelo": self._client.model,
        }

        usage = response.usage
        if usage:
            resultado["tokens_entrada"] = usage.prompt_tokens
            resultado["tokens_saida"] = usage.completion_tokens
            resultado["custo_estimado"] = self._calcular_custo(
                usage.prompt_tokens, usage.completion_tokens
            )

        choice = response.choices[0]
        message = choice.message

        # Structured Output: parsed contém o objeto Pydantic
        if hasattr(message, "parsed") and message.parsed is not None:
            doc: DocumentoExtraido = message.parsed
            resultado["dados"] = doc.model_dump()
            log.info(
                f"OpenAI | Extracao concluida | tipo={doc.tipo_documento} "
                f"confianca={doc.confianca} custo={resultado['custo_estimado']:.4f}"
            )
        elif hasattr(message, "refusal") and message.refusal:
            log.warning(f"OpenAI recusou a analise: {message.refusal}")
            resultado["dados"] = None
        else:
            # Fallback: tentar content como texto
            log.warning("OpenAI nao retornou structured output. Tentando parsear content.")
            resultado["dados"] = None

        return resultado

    def _encode_image(self, image_path: Path) -> str:
        """Codifica imagem em base64."""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _get_media_type(self, image_path: Path) -> str:
        """Retorna o media type correto para a extensao."""
        ext = image_path.suffix.lower()
        media_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".bmp": "image/bmp",
            ".tiff": "image/tiff",
            ".tif": "image/tiff",
            ".webp": "image/webp",
            ".gif": "image/gif",
        }
        return media_types.get(ext, "image/png")

    def _calcular_custo(self, tokens_entrada: int, tokens_saida: int) -> float:
        """Calcula custo estimado baseado nos precos configurados."""
        custo_in = (tokens_entrada / 1_000_000) * OPENAI_INPUT_PRICE_PER_1M
        custo_out = (tokens_saida / 1_000_000) * OPENAI_OUTPUT_PRICE_PER_1M
        return custo_in + custo_out