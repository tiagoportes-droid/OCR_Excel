"""Normalizacao e comparacao de resultados OCR."""
from __future__ import annotations
import re
from typing import Any

from logger import log


def normalizar_texto(texto: str) -> str:
    """Normaliza texto para comparacao segura."""
    if not texto:
        return ""
    t = texto.strip()
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = re.sub(r" +\n", "\n", t)
    t = re.sub(r"\n +", "\n", t)
    return t.strip()


def normalizar_para_consenso(texto: str) -> str:
    """Normaliza para consenso preservando dados criticos."""
    return normalizar_texto(texto or "").lower()


def _campos_criticos(texto: str) -> list[str]:
    """Campos criticos que nao podem divergir."""
    campos = []
    campos += re.findall(r"r\$\s*[\d.,]+", texto, re.IGNORECASE)
    campos += re.findall(r"\d{2}[/\-]\d{2}[/\-]\d{2,4}", texto)
    campos += re.findall(r"\d{3}[.\s]?\d{3}[.\s]?\d{3}[.\-\s]?\d{2}", texto)
    campos += re.findall(r"\d{2}[.\s]?\d{3}[.\s]?\d{3}[/\s]?\d{4}[\-\s]?\d{2}", texto)
    return campos


def comparar_textos(a: str, b: str) -> bool:
    """True se textos sao equivalentes."""
    if not a or not b:
        return False
    ca, cb = _campos_criticos(a), _campos_criticos(b)
    # Se um dos textos nao tem campos criticos mas o outro tem, nao sao equivalentes
    if (ca or cb) and set(ca) != set(cb):
        return False
    return normalizar_para_consenso(a) == normalizar_para_consenso(b)


class OCRResultComparator:
    """Compara resultados de providers e determina consenso/divergencia."""

    def __init__(self, require_consensus: bool = True, min_confidence: float = 0.80):
        self.require_consensus = require_consensus
        self.min_confidence = min_confidence

    def _ajustar_confianca_por_paddle(
        self, confianca: str, melhor_grupo: list[dict[str, Any]]
    ) -> str:
        """
        Considera a confianca numerica do PaddleOCR (quando disponivel)
        para ajustar o nivel final de confianca.

        Regras:
        - PaddleOCR conf < 0.50 e HIGH -> MEDIUM
        - PaddleOCR conf < 0.50 e MEDIUM -> LOW
        - PaddleOCR conf >= 0.50 mantem o nivel
        """
        for r in melhor_grupo:
            if r.get("provider") == "paddleocr" and r.get("confidence"):
                conf = float(r.get("confidence") or 0.0)
                if conf < self.min_confidence:
                    if confianca == "high":
                        log.info(
                            f"OCR | Confianca PaddleOCR baixa ({conf:.2f}) - ajustando HIGH -> MEDIUM"
                        )
                        return "medium"
                    elif confianca == "medium":
                        log.info(
                            f"OCR | Confianca PaddleOCR baixa ({conf:.2f}) - ajustando MEDIUM -> LOW"
                        )
                        return "low"
        return confianca

    def comparar(self, resultados: list[dict[str, Any]]) -> dict[str, Any]:
        """Recebe resultados padronizados e retorna resultado final."""
        validos = [r for r in resultados if r.get("success") and r.get("text")]
        todos = resultados or []

        if not validos:
            log.warning("OCR | Nenhum provider retornou resultado valido")
            return {
                "success": False,
                "status": "ocr_failed",
                "confidence": "very_low",
                "final_text": None,
                "divergence": False,
                "providers": todos,
                "groups": [],
                "divergent_providers": [],
            }

        grupos: dict[str, list[dict[str, Any]]] = {}
        for r in validos:
            chave = normalizar_para_consenso(r["text"])
            grupos.setdefault(chave, []).append(r)

        grupos_ordenados = sorted(grupos.items(), key=lambda kv: len(kv[1]), reverse=True)
        melhor_chave, melhor_grupo = grupos_ordenados[0]
        melhor_texto = melhor_grupo[0]["text"]

        n_validos = len(validos)
        n_melhor = len(melhor_grupo)
        proporcao = n_melhor / n_validos if n_validos else 0.0

        if n_melhor >= 2 and proporcao >= 0.5:
            divergent = [r for r in validos if normalizar_para_consenso(r["text"]) != melhor_chave]

            status = "confirmed" if n_melhor >= 2 else "consensus"
            if n_melhor == n_validos:
                confianca = "high"
            elif proporcao >= 0.66:
                confianca = "high" if n_validos >= 3 else "medium"
            else:
                confianca = "medium"

            # Considerar confianca do PaddleOCR (quando disponivel) no nivel final
            confianca = self._ajustar_confianca_por_paddle(confianca, melhor_grupo)

            log.info(f"OCR | Consenso encontrado | {n_melhor}/{n_validos} concordam")
            log.info(f"OCR | Status: {status.upper()}")
            log.info(f"OCR | Confianca: {confianca.upper()}")

            return {
                "success": True,
                "status": status,
                "confidence": confianca,
                "final_text": melhor_texto,
                "divergence": bool(divergent),
                "providers": todos,
                "groups": [{"text": g[0]["text"], "providers": g} for _, g in grupos_ordenados],
                "divergent_providers": divergent,
            }

        # Apenas 1 provider valido: sucesso parcial, sem consenso suficiente
        if n_validos == 1:
            confianca = "low"
            confianca = self._ajustar_confianca_por_paddle(confianca, melhor_grupo)

            log.info(f"OCR | Apenas {n_validos} provider valido - resultado nao confirmado")
            log.info(f"OCR | Status: UNCONFIRMED")
            log.info(f"OCR | Confianca: {confianca.upper()}")

            return {
                "success": True,
                "status": "unconfirmed",
                "confidence": confianca,
                "final_text": melhor_texto,
                "divergence": False,
                "providers": todos,
                "groups": [{"text": g[0]["text"], "providers": g} for _, g in grupos_ordenados],
                "divergent_providers": [],
            }

        log.warning("OCR | DIVERGENCIA DETECTADA")
        log.warning("OCR | Status: DIVERGENT")
        log.warning("OCR | Confianca: LOW")
        for r in validos:
            log.warning(f"OCR | {r['provider'].upper()}: {r.get('text', '')[:200]}")

        return {
            "success": False,
            "status": "divergent",
            "confidence": "low",
            "final_text": None,
            "divergence": True,
            "providers": todos,
            "groups": [{"text": g[0]["text"], "providers": g} for _, g in grupos_ordenados],
            "divergent_providers": [],
        }


def notify_ocr_divergence(imagem: str, resultado: dict[str, Any]) -> None:
    """Notifica divergencia OCR. Ponto de extensao: Discord, Telegram, email, webhook."""
    log.warning(f"OCR | DIVERGENCIA DETECTADA | Imagem: {imagem}")
    for r in resultado.get("providers", []):
        if r.get("success"):
            log.warning(f"OCR | {r['provider'].upper()}: {r.get('text', '')[:200]}")
    log.warning("OCR | STATUS: NAO FOI POSSIVEL CONFIRMAR O RESULTADO")
    # TODO: Integrar com Discord, Telegram, e-mail ou webhook aqui.
    # Exemplo:
    #   _enviar_discord(webhook_url, imagem, resultado)
    #   _enviar_email(destinatario, assunto, corpo)