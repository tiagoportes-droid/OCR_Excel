"""
Utilitarios gerais: hash, estabilidade de arquivo, parsing de nome de arquivo, etc.
"""

import hashlib
import time
import unicodedata
import re
from pathlib import Path

from config import (
    FILE_STABILITY_INTERVAL,
    FILE_STABILITY_CHECKS,
    ALL_EXTENSIONS,
)
from logger import log


def calcular_md5(filepath: Path, chunk_size: int = 8192) -> str:
    """Calcula o hash MD5 de um arquivo."""
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def arquivo_estavel(filepath: Path) -> bool:
    """
    Verifica se o arquivo terminou de ser copiado/escrito.
    Compara o tamanho do arquivo em intervalos consecutivos.
    """
    try:
        previous_size = -1
        for i in range(FILE_STABILITY_CHECKS):
            if not filepath.exists():
                return False
            current_size = filepath.stat().st_size
            if current_size == 0:
                time.sleep(FILE_STABILITY_INTERVAL)
                continue
            if current_size == previous_size:
                # Tenta abrir para garantir que nao esta bloqueado
                try:
                    with open(filepath, "rb") as f:
                        f.read(1)
                    return True
                except (IOError, PermissionError):
                    pass
            previous_size = current_size
            time.sleep(FILE_STABILITY_INTERVAL)
        # Ultima verificacao
        if filepath.exists() and filepath.stat().st_size > 0:
            try:
                with open(filepath, "rb") as f:
                    f.read(1)
                return True
            except (IOError, PermissionError):
                pass
        return False
    except Exception as e:
        log.warning(f"Erro ao verificar estabilidade de {filepath}: {e}")
        return False


def extensao_suportada(filepath: Path) -> bool:
    """Verifica se a extensao do arquivo e suportada."""
    return filepath.suffix.lower() in ALL_EXTENSIONS


def eh_imagem(filepath: Path) -> bool:
    """Verifica se o arquivo e uma imagem."""
    from config import IMAGE_EXTENSIONS
    return filepath.suffix.lower() in IMAGE_EXTENSIONS


def eh_pdf(filepath: Path) -> bool:
    """Verifica se o arquivo e um PDF."""
    from config import PDF_EXTENSIONS
    return filepath.suffix.lower() in PDF_EXTENSIONS


def remover_acentos(texto: str) -> str:
    """Remove acentos de uma string."""
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalizar_texto(texto: str) -> str:
    """Normaliza texto: remove acentos, lowercase, espaços duplicados."""
    texto = remover_acentos(texto)
    texto = texto.lower().strip()
    texto = re.sub(r"\s+", " ", texto)
    return texto


def parsear_nome_arquivo(filepath: Path) -> dict[str, str | None]:
    """
    Extrai informacoes do nome do arquivo.

    Formatos:
        Cliente - Local - Servico.ext
        Cliente - Servico.ext

    Retorna dict com cliente, local, servico.
    """
    nome = filepath.stem.strip()
    resultado: dict[str, str | None] = {
        "cliente": None,
        "local": None,
        "servico": None,
    }

    if not nome:
        return resultado

    partes = [p.strip() for p in nome.split("-") if p.strip()]

    if len(partes) >= 3:
        resultado["cliente"] = partes[0]
        resultado["local"] = partes[1]
        resultado["servico"] = " - ".join(partes[2:])
    elif len(partes) == 2:
        resultado["cliente"] = partes[0]
        resultado["servico"] = partes[1]
    elif len(partes) == 1:
        resultado["cliente"] = partes[0]

    return resultado


def mover_arquivo(origem: Path, destino_dir: Path) -> Path:
    """Move um arquivo para o diretorio de destino, tratando conflitos de nome."""
    destino_dir.mkdir(parents=True, exist_ok=True)
    destino = destino_dir / origem.name

    if destino.exists():
        stem = origem.stem
        suffix = origem.suffix
        counter = 1
        while destino.exists():
            destino = destino_dir / f"{stem}_{counter}{suffix}"
            counter += 1

    try:
        origem.rename(destino)
    except OSError:
        # Se rename falhar (ex: entre drives diferentes), copiar e deletar
        import shutil
        shutil.copy2(str(origem), str(destino))
        try:
            origem.unlink()
        except Exception:
            pass

    return destino


def formatar_tempo(segundos: float) -> str:
    """Formata segundos em MM:SS."""
    m, s = divmod(int(segundos), 60)
    return f"{m:02d}:{s:02d}"


def truncar_texto(texto: str, max_len: int = 200) -> str:
    """Trunca texto para exibicao em logs."""
    if len(texto) <= max_len:
        return texto
    return texto[:max_len] + "..."