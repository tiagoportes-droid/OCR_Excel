"""
Funcoes de normalizacao de dados extraidos.
"""

import re
import unicodedata
from datetime import datetime, date

from logger import log


def remover_acentos(texto: str) -> str:
    """Remove acentos/diacriticos de uma string."""
    if not texto:
        return ""
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalizar_espacos(texto: str) -> str:
    """Remove espacos duplicados e trim."""
    if not texto:
        return ""
    return re.sub(r"\s+", " ", texto).strip()


def normalizar_caixa(texto: str) -> str:
    """Converte para title case normalizado."""
    if not texto:
        return ""
    return normalizar_espacos(texto).title()


def normalizar_moeda(valor_str: str) -> float | None:
    """
    Converte string de moeda brasileira para float.
    Exemplos:
        'R$ 1.250,50' -> 1250.50
        '1250,50' -> 1250.50
        '1,250.50' -> 1250.50 (formato americano)
        '1250.50' -> 1250.50
    """
    if not valor_str:
        return None

    try:
        # Se ja for float/int
        if isinstance(valor_str, (int, float)):
            return float(valor_str)

        texto = str(valor_str).strip()

        # Remover simbolo de moeda e espacos
        texto = re.sub(r"[R$\s]", "", texto)

        # Remover caracteres nao-numericos exceto . e ,
        texto = re.sub(r"[^\d.,\-]", "", texto)

        if not texto:
            return None

        # Detectar formato brasileiro (1.250,50) vs americano (1,250.50)
        # Se tem virgula E ponto, verificar qual vem por ultimo
        tem_virgula = "," in texto
        tem_ponto = "." in texto

        if tem_virgula and tem_ponto:
            last_comma = texto.rfind(",")
            last_dot = texto.rfind(".")
            if last_comma > last_dot:
                # Formato brasileiro: 1.250,50
                texto = texto.replace(".", "").replace(",", ".")
            else:
                # Formato americano: 1,250.50
                texto = texto.replace(",", "")
        elif tem_virgula:
            # Pode ser separador decimal brasileiro
            partes = texto.split(",")
            if len(partes) == 2 and len(partes[1]) <= 2:
                texto = texto.replace(",", ".")
            else:
                texto = texto.replace(",", "")
        # Se so tem ponto, manter (pode ser decimal ou milhar)

        valor = float(texto)
        return round(valor, 2)

    except (ValueError, TypeError):
        log.warning(f"Nao foi possivel normalizar moeda: {valor_str}")
        return None


def normalizar_data(data_str: str) -> str | None:
    """
    Converte diversas representacoes de data para DD/MM/AAAA.
    """
    if not data_str:
        return None

    texto = str(data_str).strip()

    formatos = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d.%m.%Y",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%y",
        "%d-%m-%y",
        "%d de %B de %Y",
        "%d de %b de %Y",
    ]

    for fmt in formatos:
        try:
            dt = datetime.strptime(texto, fmt)
            return dt.strftime("%d/%m/%Y")
        except ValueError:
            continue

    # Tentar regex para extrair data
    match = re.search(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})", texto)
    if match:
        d, m, y = match.group(1), match.group(2), match.group(3)
        if len(y) == 2:
            y = "20" + y
        try:
            dt = datetime(int(y), int(m), int(d))
            return dt.strftime("%d/%m/%Y")
        except ValueError:
            pass

    log.warning(f"Nao foi possivel normalizar data: {data_str}")
    return data_str


def limpar_cpf(cpf_str: str) -> str:
    """Remove formatacao do CPF, mantendo apenas digitos."""
    if not cpf_str:
        return ""
    return re.sub(r"\D", "", str(cpf_str))


def limpar_cnpj(cnpj_str: str) -> str:
    """Remove formatacao do CNPJ, mantendo apenas digitos."""
    if not cnpj_str:
        return ""
    return re.sub(r"\D", "", str(cnpj_str))


def limpar_cep(cep_str: str) -> str:
    """Remove formatacao do CEP, mantendo apenas digitos."""
    if not cep_str:
        return ""
    return re.sub(r"\D", "", str(cep_str))


def limpar_telefone(telefone_str: str) -> str:
    """Remove formatacao do telefone, mantendo apenas digitos."""
    if not telefone_str:
        return ""
    return re.sub(r"\D", "", str(telefone_str))


def normalizar_documento_extraido(dados: dict) -> dict:
    """
    Aplica todas as normalizacoes nos dados extraidos.
    """
    if not dados:
        return dados

    resultado = dict(dados)

    # Normalizar moeda
    if resultado.get("valor") is not None:
        if isinstance(resultado["valor"], str):
            resultado["valor"] = normalizar_moeda(resultado["valor"])

    # Normalizar data
    if resultado.get("data"):
        resultado["data"] = normalizar_data(str(resultado["data"]))

    # Limpar CPF
    if resultado.get("cpf"):
        resultado["cpf"] = limpar_cpf(resultado["cpf"])

    # Limpar CNPJ
    if resultado.get("cnpj"):
        resultado["cnpj"] = limpar_cnpj(resultado["cnpj"])

    # Limpar CEP
    if resultado.get("cep"):
        resultado["cep"] = limpar_cep(resultado["cep"])

    # Limpar telefone
    if resultado.get("telefone"):
        resultado["telefone"] = limpar_telefone(resultado["telefone"])

    # Normalizar nomes
    for campo in ["nome", "pagador", "recebedor", "empresa"]:
        if resultado.get(campo):
            resultado[campo] = normalizar_espacos(str(resultado[campo]))

    return resultado