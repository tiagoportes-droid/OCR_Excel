"""
Pre-processamento de imagens com OpenCV para melhorar qualidade do OCR.
Nao degrada a imagem original - trabalha em copia.
"""

from pathlib import Path
import tempfile

import numpy as np
from PIL import Image

from logger import log


def preprocessar_imagem(image_path: Path) -> Path:
    """
    Aplica pre-processamento completo em uma imagem para melhorar OCR.
    Retorna caminho de imagem temporaria preprocessada.
    A imagem original NAO e alterada.
    """
    try:
        import cv2

        img = cv2.imread(str(image_path))
        if img is None:
            log.warning(f"OpenCV nao conseguiu carregar {image_path.name}")
            return image_path

        original = img.copy()

        # Converter para grayscale
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()

        # Remocao de ruido
        gray = cv2.fastNlMeansDenoising(gray, h=10)

        # Correcao de rotacao (deskew)
        gray = _deskew(gray)

        # Aumento de contraste (CLAHE)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)

        # Sharpening
        kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
        gray = cv2.filter2D(gray, -1, kernel)

        # Binarizacao Otsu
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Salvar em arquivo temporario
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png", prefix="ocr_pre_")
        cv2.imwrite(tmp.name, binary)
        tmp.close()

        log.info(f"Pre-processamento concluido | {image_path.name} -> {tmp.name}")
        return Path(tmp.name)

    except ImportError:
        log.warning("OpenCV nao instalado - retornando imagem original")
        return image_path
    except Exception as e:
        log.warning(f"Pre-processamento falhou para {image_path.name}: {e}")
        return image_path


def _deskew(image: np.ndarray, max_angle: float = 15.0) -> np.ndarray:
    """
    Corrige rotacao (skew) da imagem.
    """
    try:
        import cv2

        coords = np.column_stack(np.where(image > 0))
        if len(coords) < 10:
            return image

        angle = cv2.minAreaRect(coords)[-1]

        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        if abs(angle) > max_angle:
            return image

        if abs(angle) < 0.5:
            return image

        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            image, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )

        log.info(f"Deskew aplicado: {angle:.2f} graus")
        return rotated

    except Exception:
        return image


def redimensionar_para_ocr(image_path: Path, target_dpi: int = 300) -> Path:
    """
    Redimensiona imagem para DPI ideal para OCR, se necessario.
    """
    try:
        import cv2

        img = cv2.imread(str(image_path))
        if img is None:
            return image_path

        h, w = img.shape[:2]

        # Se a imagem for muito pequena, aumentar
        if w < 1000 or h < 1000:
            scale = max(1000 / w, 1000 / h, 1.0)
            if scale > 1.0:
                new_w = int(w * scale)
                new_h = int(h * scale)
                img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)

                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png", prefix="ocr_resize_")
                cv2.imwrite(tmp.name, img)
                tmp.close()
                log.info(f"Imagem redimensionada de {w}x{h} para {new_w}x{new_h}")
                return Path(tmp.name)

        return image_path

    except ImportError:
        return image_path
    except Exception:
        return image_path