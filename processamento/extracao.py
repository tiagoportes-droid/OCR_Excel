"""
Pipeline de extracao: orquestra OpenAI, fallback OCR, pre-processamento.
"""

import time
import traceback
from pathlib import Path
from typing import Any

from config import OPENAI_ENABLED, LOCAL_OCR_FALLBACK
from logger import log
from utils import eh_imagem, eh_pdf

from openai_reader.extractor import ExtratorOpenAI
from openai_reader.schemas import DocumentoExtraido
from leitor.pdf import extrair_texto_pdf, pdf_tem_texto_digital, pdf_para_imagens, extrair_texto_pymupdf
from leitor.ocr import executar_ocr_fallback
from processamento.preprocessamento import preprocessar_imagem
from processamento.normalizacao import normalizar_documento_extraido


def extrair_dados_documento(filepath: Path) -> dict[str, Any]:
    """
    Pipeline principal de extracao de dados de um documento.

    Fluxo:
        1. Detectar formato (PDF vs Imagem)
        2. Para PDF: verificar se e digital -> extrair texto local
        3. Para PDF escaneado / Imagem: usar OpenAI Vision
        4. Se OpenAI falhar: fallback OCR local
        5. Normalizar dados
        6. Retornar resultado estruturado

    Retorna dict com:
        - dados: dict com campos extraidos (ou None)
        - texto_bruto: texto extraido (para classificacao)
        - tokens_entrada: int
        - tokens_saida: int
        - custo_estimado: float
        - modelo: str
        - metodo: str (openai_vision, openai_texto, ocr_fallback)
        - erro: str ou None
    """
    resultado: dict[str, Any] = {
        "dados": None,
        "texto_bruto": "",
        "tokens_entrada": 0,
        "tokens_saida": 0,
        "custo_estimado": 0.0,
        "modelo": None,
        "metodo": None,
        "erro": None,
    }

    try:
        if eh_pdf(filepath):
            resultado = _processar_pdf(filepath, resultado)
        elif eh_imagem(filepath):
            resultado = _processar_imagem(filepath, resultado)
        else:
            resultado["erro"] = f"Formato nao suportado: {filepath.suffix}"
            return resultado

    except Exception as e:
        log.error(f"Erro na extracao de {filepath.name}: {e}\n{traceback.format_exc()}")
        resultado["erro"] = str(e)

    # Normalizar dados extraidos
    if resultado["dados"]:
        resultado["dados"] = normalizar_documento_extraido(resultado["dados"])

    return resultado


def _processar_pdf(filepath: Path, resultado: dict[str, Any]) -> dict[str, Any]:
    """Processa um arquivo PDF."""
    log.info(f"Processando PDF: {filepath.name}")

    # Tentar extrair texto digital
    texto_digital = ""
    if pdf_tem_texto_digital(filepath):
        texto_digital = extrair_texto_pdf(filepath)
        if not texto_digital.strip():
            texto_digital = extrair_texto_pymupdf(filepath)

    resultado["texto_bruto"] = texto_digital

    if texto_digital.strip() and len(texto_digital.strip()) >= 50:
        # PDF digital: tentar enviar texto para OpenAI para interpretacao estruturada
        log.info(f"PDF digital detectado | {filepath.name} | {len(texto_digital)} chars")

        if OPENAI_ENABLED:
            try:
                extrator = ExtratorOpenAI()
                resp = extrator.extrair_de_texto(texto_digital)
                if resp.get("dados"):
                    resultado.update({
                        "dados": resp["dados"],
                        "tokens_entrada": resp.get("tokens_entrada", 0),
                        "tokens_saida": resp.get("tokens_saida", 0),
                        "custo_estimado": resp.get("custo_estimado", 0.0),
                        "modelo": resp.get("modelo"),
                        "metodo": "openai_texto",
                    })
                    return resultado
                else:
                    log.warning(f"OpenAI nao retornou dados para texto do PDF {filepath.name}")
            except Exception as e:
                log.warning(f"OpenAI falhou para texto do PDF {filepath.name}: {e}")

        # Se OpenAI falhou ou esta desabilitada, tentar parsear localmente
        if LOCAL_OCR_FALLBACK:
            resultado = _fallback_texto(texto_digital, resultado)
            if resultado["dados"]:
                return resultado

    # PDF escaneado ou texto insuficiente: converter em imagens e usar Vision
    log.info(f"PDF escaneado ou texto insuficiente: {filepath.name}")
    paginas = pdf_para_imagens(filepath)

    if not paginas:
        resultado["erro"] = "Nao foi possivel converter PDF em imagens"
        return resultado

    if OPENAI_ENABLED:
        try:
            extrator = ExtratorOpenAI()
            resp = extrator.extrair_de_pdf_imagem(paginas)
            if resp.get("dados"):
                resultado.update({
                    "dados": resp["dados"],
                    "tokens_entrada": resp.get("tokens_entrada", 0),
                    "tokens_saida": resp.get("tokens_saida", 0),
                    "custo_estimado": resp.get("custo_estimado", 0.0),
                    "modelo": resp.get("modelo"),
                    "metodo": "openai_vision",
                })
                return resultado
        except Exception as e:
            log.warning(f"OpenAI Vision falhou para PDF {filepath.name}: {e}")

    # Fallback OCR local para cada pagina
    if LOCAL_OCR_FALLBACK:
        textos_ocr = []
        for pg in paginas:
            pg_pre = preprocessar_imagem(pg)
            texto_ocr = executar_ocr_fallback(pg_pre)
            if texto_ocr:
                textos_ocr.append(texto_ocr)

        texto_completo = "\n\n".join(textos_ocr)
        resultado["texto_bruto"] = texto_completo

        if texto_completo.strip():
            resultado = _fallback_texto(texto_completo, resultado)

    # Cleanup
    _limpar_temporarios(paginas)

    if not resultado["dados"]:
        resultado["erro"] = "Nenhum metodo conseguiu extrair dados do PDF"

    return resultado


def _processar_imagem(filepath: Path, resultado: dict[str, Any]) -> dict[str, Any]:
    """Processa um arquivo de imagem."""
    log.info(f"Processando imagem: {filepath.name}")

    if OPENAI_ENABLED:
        try:
            extrator = ExtratorOpenAI()
            resp = extrator.extrair_de_imagem(filepath)
            if resp.get("dados"):
                resultado.update({
                    "dados": resp["dados"],
                    "tokens_entrada": resp.get("tokens_entrada", 0),
                    "tokens_saida": resp.get("tokens_saida", 0),
                    "custo_estimado": resp.get("custo_estimado", 0.0),
                    "modelo": resp.get("modelo"),
                    "metodo": "openai_vision",
                })
                return resultado
        except Exception as e:
            log.warning(f"OpenAI Vision falhou para imagem {filepath.name}: {e}")

    # Fallback OCR local
    if LOCAL_OCR_FALLBACK:
        img_pre = preprocessar_imagem(filepath)
        texto_ocr = executar_ocr_fallback(img_pre)
        resultado["texto_bruto"] = texto_ocr

        if texto_ocr.strip():
            # Tentar enviar texto do OCR para OpenAI
            if OPENAI_ENABLED:
                try:
                    extrator = ExtratorOpenAI()
                    resp = extrator.extrair_de_texto(texto_ocr)
                    if resp.get("dados"):
                        resultado.update({
                            "dados": resp["dados"],
                            "tokens_entrada": resp.get("tokens_entrada", 0),
                            "tokens_saida": resp.get("tokens_saida", 0),
                            "custo_estimado": resp.get("custo_estimado", 0.0),
                            "modelo": resp.get("modelo"),
                            "metodo": "ocr_fallback+openai",
                        })
                        return resultado
                except Exception:
                    pass

            # Ultimo recurso: parsear texto bruto localmente
            resultado = _fallback_texto(texto_ocr, resultado)

    if not resultado["dados"]:
        resultado["erro"] = "Nenhum metodo conseguiu extrair dados da imagem"

    return resultado


def _fallback_texto(texto: str, resultado: dict[str, Any]) -> dict[str, Any]:
    """
    Tenta extrair dados basicos do texto usando regex/heuristicas quando a OpenAI nao esta disponivel.
    """
    import re

    dados: dict[str, Any] = {}

    # Tentar extrair valor
    match_valor = re.search(r"R\$\s*([\d.,]+)", texto)
    if match_valor:
        from processamento.normalizacao import normalizar_moeda
        dados["valor"] = normalizar_moeda(match_valor.group(1))

    # Tentar extrair data
    match_data = re.search(r"(\d{2}[/\-]\d{2}[/\-]\d{2,4})", texto)
    if match_data:
        dados["data"] = match_data.group(1)

    # Tentar extrair CPF
    match_cpf = re.search(r"\d{3}[.\s]?\d{3}[.\s]?\d{3}[.\-\s]?\d{2}", texto)
    if match_cpf:
        dados["cpf"] = re.sub(r"\D", "", match_cpf.group())

    # Tentar extrair CNPJ
    match_cnpj = re.search(r"\d{2}[.\s]?\d{3}[.\s]?\d{3}[/\s]?\d{4}[\-\s]?\d{2}", texto)
    if match_cnpj:
        dados["cnpj"] = re.sub(r"\D", "", match_cnpj.group())

    # Tipo de documento
    texto_lower = texto.lower()
    if "pix" in texto_lower:
        dados["tipo_documento"] = "PIX"
    elif "ted" in texto_lower:
        dados["tipo_documento"] = "TED"
    elif "boleto" in texto_lower:
        dados["tipo_documento"] = "Boleto"
    elif "nota fiscal" in texto_lower:
        dados["tipo_documento"] = "Nota Fiscal"
    elif "comprovante" in texto_lower:
        dados["tipo_documento"] = "Comprovante"

    if dados:
