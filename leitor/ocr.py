"""
OCR local como fallback: PaddleOCR, EasyOCR, Tesseract.
Ordem de prioridade configuravel.
"""

from pathlib import Path

from logger import log


def ocr_paddleocr(image_path: Path) -> str:
    """Executa OCR usando PaddleOCR."""
    try:
        from paddleocr import PaddleOCR

        ocr = PaddleOCR(use_angle_cls=True, lang="pt", show_log=False)
        resultado = ocr.ocr(str(image_path), cls=True)

        linhas: list[str] = []
        if resultado:
            for page in resultado:
                if page:
                    for line in page:
                        if line and len(line) >= 2:
                            texto = line[1][0] if isinstance(line[1], (list, tuple)) else str(line[1])
                            linhas.append(texto)

        texto_final = "\n".join(linhas)
        log.info(f"PaddleOCR | {image_path.name} | {len(linhas)} linhas | {len(texto_final)} chars")
        return texto_final

    except ImportError:
        log.warning("PaddleOCR nao instalado")
        return ""
    except Exception as e:
        log.warning(f"PaddleOCR falhou para {image_path.name}: {e}")
        return ""


def ocr_easyocr(image_path: Path) -> str:
    """Executa OCR usando EasyOCR."""
    try:
        import easyocr

        reader = easyocr.Reader(["pt", "en"], gpu=False)
        resultado = reader.readtext(str(image_path))

        linhas = [item[1] for item in resultado if item and len(item) >= 2]

        texto_final = "\n".join(linhas)
        log.info(f"EasyOCR | {image_path.name} | {len(linhas)} linhas | {len(texto_final)} chars")
        return texto_final

    except ImportError:
        log.warning("EasyOCR nao instalado")
        return ""
    except Exception as e:
        log.warning(f"EasyOCR falhou para {image_path.name}: {e}")
        return ""


def ocr_tesseract(image_path: Path) -> str:
    """Executa OCR usando Tesseract/Pytesseract."""
    try:
        import pytesseract

        texto = pytesseract.image_to_string(
            str(image_path),
            lang="por",
            config="--oem 3 --psm 6",
        )

        texto_final = texto.strip()
        log.info(f"Tesseract | {image_path.name} | {len(texto_final)} chars")
        return texto_final

    except ImportError:
        log.warning("pytesseract nao instalado")
        return ""
    except Exception as e:
        log.warning(f"Tesseract falhou para {image_path.name}: {e}")
        return ""


def executar_ocr_fallback(image_path: Path) -> str:
    """
    Executa OCR local com fallback em cadeia:
    PaddleOCR -> EasyOCR -> Tesseract
    """
    log.info(f"Iniciando OCR fallback para {image_path.name}")

    # Tentativa 1: PaddleOCR
    texto = ocr_paddleocr(image_path)
    if texto.strip():
        log.info(f"OCR fallback: PaddleOCR teve sucesso para {image_path.name}")
        return texto

    # Tentativa 2: EasyOCR
    texto = ocr_easyocr(image_path)
    if texto.strip():
        log.info(f"OCR fallback: EasyOCR teve sucesso para {image_path.name}")
        return texto

    # Tentativa 3: Tesseract
    texto = ocr_tesseract(image_path)
    if texto.strip():
        log.info(f"OCR fallback: Tesseract teve sucesso para {image_path.name}")
        return texto

    log.error(f"Todos os motores OCR falharam para {image_path.name}")
    return ""