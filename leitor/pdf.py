"""
Leitor de PDFs: extrai texto digital com pdfplumber e converte paginas em imagens com PyMuPDF.
"""

import tempfile
from pathlib import Path
from typing import Any

from logger import log


def extrair_texto_pdf(filepath: Path) -> str:
    """
    Extrai texto de um PDF digital usando pdfplumber.
    Retorna o texto concatenado de todas as paginas.
    """
    try:
        import pdfplumber

        texto_total = []
        with pdfplumber.open(str(filepath)) as pdf:
            for i, page in enumerate(pdf.pages):
                texto = page.extract_text() or ""
                if texto.strip():
                    texto_total.append(f"--- Pagina {i + 1} ---\n{texto}")

        resultado = "\n\n".join(texto_total)
        log.info(f"pdfplumber | {filepath.name} | {len(pdf.pages)} paginas | {len(resultado)} chars extraidos")
        return resultado

    except Exception as e:
        log.warning(f"pdfplumber falhou para {filepath.name}: {e}")
        return ""


def pdf_tem_texto_digital(filepath: Path, min_chars: int = 50) -> bool:
    """
    Verifica se um PDF possui texto digital extraivel.
    PDFs escaneados tipicamente nao possuem texto ou possuem muito pouco.
    """
    try:
        texto = extrair_texto_pdf(filepath)
        tem_texto = len(texto.strip()) >= min_chars
        log.info(f"PDF digital check | {filepath.name} | tem_texto={tem_texto} ({len(texto.strip())} chars)")
        return tem_texto
    except Exception:
        return False


def pdf_para_imagens(filepath: Path, dpi: int = 200) -> list[Path]:
    """
    Converte paginas de um PDF em imagens PNG usando PyMuPDF (fitz).
    Retorna lista de caminhos temporarios das imagens.
    """
    try:
        import fitz  # PyMuPDF

        imagens: list[Path] = []
        temp_dir = Path(tempfile.mkdtemp(prefix="ocr_pdf_"))

        doc = fitz.open(str(filepath))
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)

        for i, page in enumerate(doc):
            pix = page.get_pixmap(matrix=mat)
            img_path = temp_dir / f"page_{i + 1:03d}.png"
            pix.save(str(img_path))
            imagens.append(img_path)

        doc.close()
        log.info(f"PyMuPDF | {filepath.name} | {len(imagens)} paginas convertidas em imagem")
        return imagens

    except Exception as e:
        log.error(f"PyMuPDF falhou para {filepath.name}: {e}")
        return []


def extrair_texto_pymupdf(filepath: Path) -> str:
    """
    Extrai texto usando PyMuPDF como alternativa ao pdfplumber.
    """
    try:
        import fitz

        texto_total = []
        doc = fitz.open(str(filepath))
        for i, page in enumerate(doc):
            texto = page.get_text("text") or ""
            if texto.strip():
                texto_total.append(f"--- Pagina {i + 1} ---\n{texto}")
        doc.close()

        resultado = "\n\n".join(texto_total)
        log.info(f"PyMuPDF texto | {filepath.name} | {len(resultado)} chars")
        return resultado

    except Exception as e:
        log.warning(f"PyMuPDF texto falhou para {filepath.name}: {e}")
        return ""