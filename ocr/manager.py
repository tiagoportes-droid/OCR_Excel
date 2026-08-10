"""
Gerenciador central de OCR multi-provider.
Orquestra execucao dos providers e compara resultados.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from config import OCR_REQUIRE_CONSENSUS, OCR_MIN_CONFIDENCE
from logger import log
from ocr.providers import criar_providers
from ocr.comparator import OCRResultComparator, notify_ocr_divergence


class OCRManager:
    """
    Orquestra providers de OCR independentes e retorna resultado consolidado.

    Uso:
        manager = OCRManager()
        resultado = manager.analisar_imagem("documento.png")

    O manager e singleton por processo: providers pesados (PaddleOCR, Qwen)
    sao inicializados uma unica vez e reutilizados entre chamadas.
    """

    _instancia: "OCRManager | None" = None

    def __new__(cls, *args, **kwargs):
        """Singleton: garante que modelos pesados sejam carregados apenas uma vez por processo."""
        if cls._instancia is None:
            cls._instancia = super().__new__(cls)
        return cls._instancia

    def __init__(
        self,
        require_consensus: bool | None = None,
        min_confidence: float | None = None,
    ):
        # __init__ roda toda vez; so inicializa providers se ainda nao existe
        if not getattr(self, "_inicializado", False):
            self._inicializado = True
            self._require_consensus = (
                require_consensus if require_consensus is not None else OCR_REQUIRE_CONSENSUS
            )
            self._min_confidence = (
                min_confidence if min_confidence is not None else OCR_MIN_CONFIDENCE
            )
            self._providers = criar_providers()
            self._comparator = OCRResultComparator(
                require_consensus=self._require_consensus,
                min_confidence=self._min_confidence,
            )
            if self._providers:
                nomes = ", ".join(p.name for p in self._providers)
                log.info(f"OCR | Manager iniciado | providers: {nomes}")
            else:
                log.warning("OCR | Nenhum provider habilitado")

    @classmethod
    def reiniciar(cls) -> None:
        """Zera a instancia singleton (util em testes)."""
        cls._instancia = None

    @property
    def providers(self) -> list[Any]:
        return list(self._providers)

    def analisar_imagem(self, image_path: Path) -> dict[str, Any]:
        """
        Executa todos os providers em paralelo e compara os resultados.

        Retorna:
        {
            "success": bool,
            "status": "confirmed" | "consensus" | "divergent" | "ocr_failed",
            "confidence": "high" | "medium" | "low" | "very_low",
            "final_text": str | None,
            "divergence": bool,
            "providers": [ {provider, success, text, confidence, error}, ... ],
            "groups": [...],
            "divergent_providers": [...]
        }
        """
        log.info(f"OCR | Processando imagem: {image_path.name}")

        if not self._providers:
            log.warning("OCR | Nenhum provider disponivel")
            return {
                "success": False,
                "status": "ocr_failed",
                "confidence": "very_low",
                "final_text": None,
                "divergence": False,
                "providers": [],
                "groups": [],
                "divergent_providers": [],
            }

        # Executar providers em paralelo (ThreadPool, pois sao I/O-bound ou
        # instancias locais ja carregadas)
        resultados: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=len(self._providers)) as executor:
            futures = {executor.submit(p.analyze, image_path): p for p in self._providers}
            for future in as_completed(futures):
                provider = futures[future]
                try:
                    res = future.result()
                    resultados.append(res)
                    if res.get("success"):
                        conf = res.get("confidence") or 0.0
                        log.info(f"OCR | {provider.name} concluido | conf={conf:.2f}")
                    else:
                        log.warning(f"OCR | {provider.name} falhou | {res.get('error')}")
                except Exception as e:
                    log.warning(f"OCR | {provider.name} erro inesperado: {e}")
                    resultados.append(
                        {
                            "provider": provider.name,
                            "success": False,
                            "text": None,
                            "confidence": 0.0,
                            "error": str(e),
                        }
                    )

        log.info("OCR | Comparando resultados")
        final = self._comparator.comparar(resultados)

        if final.get("divergence"):
            notify_ocr_divergence(str(image_path), final)

        return final