"""
Pacote de OCR multi-providor com comparacao e consenso.
"""

from ocr.providers import (
    OCRProvider,
    OpenAIProvider,
    PaddleOCRProvider,
    GeminiProvider,
    QwenVLProvider,
    criar_providers,
)
from ocr.comparator import OCRResultComparator, normalizar_texto
from ocr.manager import OCRManager

__all__ = [
    "OCRProvider",
    "OpenAIProvider",
    "PaddleOCRProvider",
    "GeminiProvider",
    "QwenVLProvider",
    "criar_providers",
    "OCRResultComparator",
    "normalizar_texto",
    "OCRManager",
]