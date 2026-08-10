"""
Validacao de dados extraidos: CPF, CNPJ, CEP, datas, valores, campos obrigatorios.
"""

import re
from datetime import datetime

from logger import log


def validar_cpf(cpf: str) -> bool:
    """
    Validacao real de CPF com digitos verificadores.
    """
    if not cpf:
        return False

    cpf = re.sub(r"\D", "", cpf)

    if len(cpf) != 11:
        return False

    # CPFs com todos os digitos iguais sao invalidos
    if cpf == cpf[0] * 11:
        return False

    # Calculo do primeiro digito verificador
    soma = 0
    for i in range(9):
        soma += int(cpf[i]) * (10 - i)
    resto = (soma * 10) % 11
    if resto == 10:
        resto = 0
    if resto != int(cpf[9]):
        return False

    # Calculo do segundo digito verificador
    soma = 0
    for i in range(10):
        soma += int(cpf[i]) * (11 - i)
    resto = (soma * 10) % 11
    if resto == 10:
        resto = 0
    if resto != int(cpf[10]):
        return False

    return True


def validar_cnpj(cnpj: str) -> bool:
    """
    Validacao real de CNPJ com digitos verificadores.
    """
    if not cnpj:
        return False

    cnpj = re.sub(r"\D", "", cnpj)

    if len(cnpj) != 14:
        return False

    if cnpj == cnpj[0] * 14:
        return False

    # Primeiro digito verificador
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * pesos1[i] for i in range(12))
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto
    if int(cnpj[12]) != digito1:
        return False

    # Segundo digito verificador
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * pesos2[i] for i in range(13))
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto
    if int(cnpj[13]) != digito2:
        return False

    return True


def validar_cep(cep: str) -> bool:
    """Valida formato do CEP (8 digitos)."""
    if not cep:
        return False
    cep_limpo = re.sub(r"\D", "", cep)
    return len(cep_limpo) == 8


def validar_data(data_str: str) -> bool:
    """Valida se a string e uma data valida no formato DD/MM/AAAA."""
    if not data_str:
        return False

    formatos = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"]
    for fmt in formatos:
        try:
            dt = datetime.strptime(data_str, fmt)
            # Verificar se a data e razoavel (nao no futuro distante, nao muito antiga)
            if dt.year < 2000 or dt.year > 2100:
                return False
            return True
        except ValueError:
            continue
    return False


def validar_valor(valor) -> bool:
    """Valida se o valor e um numero positivo razoavel."""
    if valor is None:
        return False
    try:
        v = float(valor)
        return v > 0 and v < 100_000_000  # Limite razoavel
    except (ValueError, TypeError):
        return False


def validar_email(email: str) -> bool:
    """Validacao basica de email."""
    if not email:
        return False
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validar_dados_extraidos(dados: dict) -> dict:
    """
    Valida todos os campos dos dados extraidos.
    Retorna dict com resultados da validacao.
    """
    validacoes: dict = {
        "valido": True,
        "erros": [],
        "avisos": [],
    }

    # Validar CPF se presente
    if dados.get("cpf"):
        if not validar_cpf(dados["cpf"]):
            validacoes["avisos"].append(f"CPF invalido: {dados['cpf']}")

    # Validar CNPJ se presente
    if dados.get("cnpj"):
        if not validar_cnpj(dados["cnpj"]):
            validacoes["avisos"].append(f"CNPJ invalido: {dados['cnpj']}")

    # Validar CEP se presente
    if dados.get("cep"):
        if not validar_cep(dados["cep"]):
            validacoes["avisos"].append(f"CEP invalido: {dados['cep']}")

    # Validar data se presente
    if dados.get("data"):
        if not validar_data(dados["data"]):
            validacoes["avisos"].append(f"Data invalida: {dados['data']}")

    # Validar valor se presente
    if dados.get("valor") is not None:
        if not validar_valor(dados["valor"]):
            validacoes["avisos"].append(f"Valor invalido: {dados['valor']}")

    # Validar email se presente
    if dados.get("email"):
        if not validar_email(dados["email"]):
            validacoes["avisos"].append(f"Email invalido: {dados['email']}")

    # Verificar confianca
    confianca = dados.get("confianca")
    if confianca is not None and confianca < 0.5:
        validacoes["avisos"].append(f"Confianca baixa: {confianca}")

    # Verificar se tem ao menos um campo util
    campos_uteis = ["tipo_documento", "valor", "data", "pagador", "recebedor", "nome", "empresa"]
    tem_campo_util = any(dados.get(c) for c in campos_uteis)
    if not tem_campo_util:
        validacoes["valido"] = False
        validacoes["erros"].append("Nenhum campo util foi extraido do documento")

    if validacoes["erros"]:
        validacoes["valido"] = False

    return validacoes