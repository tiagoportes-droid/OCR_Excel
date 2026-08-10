"""
Regras de negocio: classificacao de Entrada/Saida, mapeamento de nomes, etc.
"""

from utils import normalizar_texto, remover_acentos
from logger import log

# Nomes de pagadores que indicam ENTRADA
PAGADORES_ENTRADA: list[str] = [
    "Joyce",
    "Diego",
    "Ricardo",
    "Nilson",
    "Cleber",
    "Avelino",
    "Alvaro",
    "Marcos",
    "Iara",
    "Vinicius",
]

# Pagadores que indicam SAIDA
PAGADORES_SAIDA: list[str] = [
    "PORTES ENGENHARIA",
]

# Tipos de documento que indicam SAIDA
TIPOS_SAIDA: list[str] = [
    "Getnet",
    "Sicoob",
    "Nota Jandibloc",
]

# Normalizar listas para comparacao
_PAGADORES_ENTRADA_NORM: list[str] = [normalizar_texto(n) for n in PAGADORES_ENTRADA]
_PAGADORES_SAIDA_NORM: list[str] = [normalizar_texto(n) for n in PAGADORES_SAIDA]
_TIPOS_SAIDA_NORM: list[str] = [normalizar_texto(t) for t in TIPOS_SAIDA]


def determinar_direcao(
    pagador: str | None,
    recebedor: str | None,
    tipo_documento: str | None,
    dados: dict | None = None,
) -> str:
    """
    Determina se a transacao e Entrada ou Saida baseado nas regras de negocio.

    Retorna:
        "Entrada" ou "Saida" ou "Indefinido"
    """
    # Verificar tipo de documento primeiro
    if tipo_documento:
        tipo_norm = normalizar_texto(tipo_documento)
        for tipo_saida in _TIPOS_SAIDA_NORM:
            if tipo_saida in tipo_norm or tipo_norm in tipo_saida:
                log.info(f"Regra: SAIDA por tipo de documento '{tipo_documento}'")
                return "Saída"

    # Verificar pagador
    if pagador:
        pagador_norm = normalizar_texto(pagador)

        # Verificar se e pagador de SAIDA
        for ps in _PAGADORES_SAIDA_NORM:
            if ps in pagador_norm or pagador_norm in ps:
                log.info(f"Regra: SAIDA por pagador '{pagador}'")
                return "Saída"

        # Verificar se e pagador de ENTRADA
        for pe in _PAGADORES_ENTRADA_NORM:
            if pe in pagador_norm or pagador_norm in pe:
                log.info(f"Regra: ENTRADA por pagador '{pagador}'")
                return "Entrada"

    # Verificar no nome tambem (pode ser informacao parcial)
    nome = None
    if dados:
        nome = dados.get("nome")
    if nome:
        nome_norm = normalizar_texto(nome)
        for pe in _PAGADORES_ENTRADA_NORM:
            if pe in nome_norm or nome_norm in pe:
                log.info(f"Regra: ENTRADA por nome '{nome}'")
                return "Entrada"

    log.info("Regra: Direcao INDEFINIDA - nenhuma regra aplicavel")
    return "Indefinido"


def aplicar_dados_nome_arquivo(dados: dict, info_nome: dict) -> dict:
    """
    Sobrescreve campos dos dados extraidos com informacoes do nome do arquivo.
    O nome do arquivo tem PRIORIDADE sobre dados da IA.
    """
    resultado = dict(dados)

    if info_nome.get("cliente"):
        resultado["nome"] = info_nome["cliente"]
        log.info(f"Nome do arquivo sobrescreveu campo 'nome': {info_nome['cliente']}")

    if info_nome.get("local"):
        resultado["cidade"] = info_nome["local"]
        log.info(f"Nome do arquivo sobrescreveu campo 'cidade': {info_nome['local']}")

    if info_nome.get("servico"):
        resultado["descricao"] = info_nome["servico"]
        log.info(f"Nome do arquivo sobrescreveu campo 'descricao': {info_nome['servico']}")

    return resultado


def verificar_confianca_minima(dados: dict, limiar: float = 0.4) -> bool:
    """
    Verifica se a confianca da extracao esta acima do limiar.
    """
    confianca = dados.get("confianca")
    if confianca is None:
        return True  # Se nao informada, assumir OK
    return float(confianca) >= limiar