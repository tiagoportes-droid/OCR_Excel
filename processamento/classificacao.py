"""
Classificacao de documentos.
A IA classifica o tipo; regras Python confirmam/sobrescrevem.
"""

from logger import log
from utils import normalizar_texto


# Tipos conhecidos e palavras-chave associadas
TIPOS_CONHECIDOS: dict[str, list[str]] = {
    "PIX Cora": ["cora", "pix cora", "conta cora"],
    "Getnet": ["getnet", "get net"],
    "Sicoob": ["sicoob", "bancoob"],
    "Nota Jandibloc": ["jandibloc", "jandi bloc", "jandi-bloc"],
    "Boleto Caixa": ["caixa economica", "caixa federal", "boleto caixa", "cef"],
    "PIX": ["pix", "transferencia pix", "pagamento pix"],
    "TED": ["ted", "transferencia ted"],
    "DOC": ["doc", "transferencia doc"],
    "Boleto": ["boleto", "boleto bancario"],
    "Nota Fiscal": ["nota fiscal", "nf-e", "nfe", "nfse", "nota fiscal de servico"],
    "Recibo": ["recibo"],
    "Extrato": ["extrato"],
    "Comprovante": ["comprovante"],
}


def classificar_por_regras(texto: str, dados_ia: dict | None = None) -> str | None:
    """
    Classifica o documento baseado em regras (palavras-chave no texto).
    """
    if not texto:
        return None

    texto_norm = normalizar_texto(texto)

    for tipo, palavras in TIPOS_CONHECIDOS.items():
        for palavra in palavras:
            if palavra in texto_norm:
                log.info(f"Classificacao por regras: '{tipo}' (encontrou '{palavra}')")
                return tipo

    return None


def classificar_documento(
    tipo_ia: str | None,
    texto_documento: str = "",
    dados_ia: dict | None = None,
) -> dict:
    """
    Classifica o documento combinando IA + regras.
    Retorna dict com tipo_final, divergencia, confianca.
    """
    tipo_regras = classificar_por_regras(texto_documento, dados_ia)

    resultado = {
        "tipo_ia": tipo_ia,
        "tipo_regras": tipo_regras,
        "tipo_final": None,
        "divergencia": False,
        "confianca_classificacao": 1.0,
    }

    confianca = 1.0
    if dados_ia:
        confianca = dados_ia.get("confianca", 1.0) or 1.0

    # Se ambos concordam
    if tipo_ia and tipo_regras:
        tipo_ia_norm = normalizar_texto(tipo_ia)
        tipo_regras_norm = normalizar_texto(tipo_regras)

        if tipo_ia_norm == tipo_regras_norm or tipo_regras_norm in tipo_ia_norm or tipo_ia_norm in tipo_regras_norm:
            resultado["tipo_final"] = tipo_regras  # Preferir o nome padronizado das regras
            resultado["confianca_classificacao"] = confianca
        else:
            resultado["divergencia"] = True
            log.warning(f"Divergencia na classificacao: IA='{tipo_ia}' vs Regras='{tipo_regras}'")

            # Se confianca da IA for alta, usar IA; senao, usar regras
            if confianca >= 0.7:
                resultado["tipo_final"] = tipo_ia
            else:
                resultado["tipo_final"] = tipo_regras
            resultado["confianca_classificacao"] = confianca * 0.7

    # Apenas IA classificou
    elif tipo_ia:
        resultado["tipo_final"] = tipo_ia
        resultado["confianca_classificacao"] = confianca

    # Apenas regras classificaram
    elif tipo_regras:
        resultado["tipo_final"] = tipo_regras
        resultado["confianca_classificacao"] = 0.8

    # Nenhum classificou
    else:
        resultado["tipo_final"] = "Outros"
        resultado["confianca_classificacao"] = 0.3
        log.warning("Documento nao classificado por nenhum metodo")

    return resultado