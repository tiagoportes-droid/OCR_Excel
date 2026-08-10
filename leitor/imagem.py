"""
Leitor de imagens: carrega e prepara imagens para processamento.
"""

from pathlib import Path

from PIL import Image
from logger import log


def carregar_imagem(filepath: Path) -> Image.Image | None:
    """Carrega uma imagem usando Pillow. Retorna None em caso de erro."""
    try:
        img = Image.open(str(filepath))
        img.load()  # Forcar carregamento completo
        # Converter RGBA para RGB se necessario
        if img.mode == "RGBA":
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        log.info(f"Imagem carregada | {filepath.name} | {img.size} | modo={img.mode}")
        return img
    except Exception as e:
        log.error(f"Erro ao carregar imagem {filepath.name}: {e}")
        return None


def imagem_para_bytes(img: Image.Image, formato: str = "PNG") -> bytes:
    """Converte imagem PIL para bytes."""
    import io
    buffer = io.BytesIO()
    img.save(buffer, format=formato)
    return buffer.getvalue()


def redimensionar_imagem(img: Image.Image, max_dim: int = 2048) -> Image.Image:
    """
    Redimensiona imagem se qualquer dimensao exceder max_dim.
    Mantem aspect ratio.
    """
    w, h = img.size
    if w <= max_dim and h <= max_dim:
        return img

    ratio = min(max_dim / w, max_dim / h)
    new_w = int(w * ratio)
    new_h = int(h * ratio)
    resized = img.resize((new_w, new_h), Image.LANCZOS)
    log.info(f"Imagem redimensionada de {img.size} para {resized.size}")
    return resized


def salvar_imagem_temporaria(img: Image.Image, suffix: str = ".png") -> Path:
    """Salva imagem em arquivo temporario e retorna o caminho."""
    import tempfile
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix="ocr_img_")
    img.save(tmp.name)
    tmp.close()
    return Path(tmp.name)