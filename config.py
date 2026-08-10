"""
Configuracao centralizada do sistema.
Carrega variaveis do .env e expoe como constantes tipadas.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Carregar .env da raiz do projeto
_PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(_PROJECT_ROOT / ".env")


def _get_bool(key: str, default: bool = False) -> bool:
    val = os.getenv(key, str(default)).strip().lower()
    return val in ("true", "1", "yes", "sim")


def _get_int(key: str, default: int = 4) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except (ValueError, TypeError):
        return default


def _get_float(key: str, default: float = 0.0) -> float:
    try:
        return float(os.getenv(key, str(default)))
    except (ValueError, TypeError):
        return default


def _expand_path(raw: str) -> Path:
    """Expande %USERPROFILE% e variaveis de ambiente no Windows."""
    expanded = os.path.expandvars(raw)
    expanded = os.path.expanduser(expanded)
    p = Path(expanded)
    if not p.is_absolute():
        p = _PROJECT_ROOT / p
    return p


# --- OpenAI ---
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
OPENAI_ENABLED: bool = _get_bool("OPENAI_ENABLED", True)
OPENAI_INPUT_PRICE_PER_1M: float = _get_float("OPENAI_INPUT_PRICE_PER_1M", 2.50)
OPENAI_OUTPUT_PRICE_PER_1M: float = _get_float("OPENAI_OUTPUT_PRICE_PER_1M", 10.00)

# --- PaddleOCR ---
PADDLEOCR_ENABLED: bool = _get_bool("PADDLEOCR_ENABLED", True)

# --- Google Gemini ---
GEMINI_ENABLED: bool = _get_bool("GEMINI_ENABLED", True)
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# --- Qwen-VL ---
QWEN_ENABLED: bool = _get_bool("QWEN_ENABLED", True)
QWEN_MODEL: str = os.getenv("QWEN_MODEL", "qwen2.5vl:3b")
QWEN_BASE_URL: str = os.getenv("QWEN_BASE_URL", "http://localhost:11434")

# --- Comparador OCR ---
OCR_REQUIRE_CONSENSUS: bool = _get_bool("OCR_REQUIRE_CONSENSUS", True)
OCR_MIN_CONFIDENCE: float = _get_float("OCR_MIN_CONFIDENCE", 0.80)

# --- Caminhos ---
PROJECT_ROOT: Path = _PROJECT_ROOT
EXCEL_PATH: Path = _expand_path(os.getenv("EXCEL_PATH", "Controle Financeiro Geral.xlsx"))
ENTRADA_PATH: Path = _expand_path(os.getenv("ENTRADA_PATH", "arquivos/entrada"))
PROCESSADOS_PATH: Path = _expand_path(os.getenv("PROCESSADOS_PATH", "arquivos/processados"))
FALHAS_PATH: Path = _expand_path(os.getenv("FALHAS_PATH", "arquivos/falhas"))
DATABASE_PATH: Path = _expand_path(os.getenv("DATABASE_PATH", "banco/processamento.db"))
LOG_PATH: Path = _expand_path(os.getenv("LOG_PATH", "logs/processamento.log"))

WHATSAPP_PATH_RAW: str = os.getenv("WHATSAPP_PATH", "")
WHATSAPP_PATH: Path | None = _expand_path(WHATSAPP_PATH_RAW) if WHATSAPP_PATH_RAW.strip() else None

# --- Workers ---
MAX_WORKERS: int = _get_int("MAX_WORKERS", 4)

# --- Flags ---
LOCAL_OCR_FALLBACK: bool = _get_bool("LOCAL_OCR_FALLBACK", True)
DELETE_PROCESSED_FILES: bool = _get_bool("DELETE_PROCESSED_FILES", False)

# --- Extensoes suportadas ---
IMAGE_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}
PDF_EXTENSIONS: set[str] = {".pdf"}
ALL_EXTENSIONS: set[str] = IMAGE_EXTENSIONS | PDF_EXTENSIONS

# --- Retry ---
RETRY_MAX_ATTEMPTS: int = 3
RETRY_BASE_DELAY: float = 2.0
RETRY_MAX_DELAY: float = 60.0

# --- Estabilidade de arquivo (segundos) ---
FILE_STABILITY_INTERVAL: float = 1.5
FILE_STABILITY_CHECKS: int = 3

# Criar diretorios necessarios
for _dir in [ENTRADA_PATH, PROCESSADOS_PATH, FALHAS_PATH, DATABASE_PATH.parent, LOG_PATH.parent]:
    _dir.mkdir(parents=True, exist_ok=True)