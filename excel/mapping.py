"""
Mapeamento de colunas do Excel com aliases.
Permite localizar colunas independente do nome exato usado no cabecalho.
"""

from logger import log

# ============================================================
# ALIASES - cada campo pode ter multiplos nomes de coluna
# ============================================================
ALIASES: dict[str, list[str]] = {
    "cliente": ["Cliente", "Nome Cliente", "Nome", "cliente", "nome cliente", "nome"],
    "local": ["Local", "Cidade", "Localidade", "local", "cidade", "localidade"],
    "servico": [
        "Serviço", "Servico", "Especificação", "Especificacao",
        "Descrição do Serviço", "Descricao do Servico",
        "serviço", "servico", "especificação", "especificacao",
        "descrição do serviço", "descricao do servico",
    ],
    "valor": ["Valor", "Valor Pago", "Total", "valor", "valor pago", "total"],
    "data": ["Data", "Data Pagamento", "data", "data pagamento"],
    "hora": ["Hora", "Horário", "Horario", "hora", "horário", "horario"],
    "tipo_documento": [
        "Tipo", "Tipo Documento", "Tipo de Documento",
        "tipo", "tipo documento", "tipo de documento",
    ],
    "pagador": ["Pagador", "De", "Remetente", "pagador", "de", "remetente"],
    "recebedor": [
        "Recebedor", "Para", "Beneficiário", "Beneficiario", "Destinatário", "Destinatario",
        "recebedor", "para", "beneficiário", "beneficiario", "destinatário", "destinatario",
    ],
    "empresa": ["Empresa", "Razão Social", "Razao Social", "empresa", "razão social", "razao social"],
    "cpf": ["CPF", "cpf"],
    "cnpj": ["CNPJ", "cnpj"],
    "banco": ["Banco", "Instituição", "Instituicao", "banco", "instituição", "instituicao"],
    "agencia": ["Agência", "Agencia", "agência", "agencia"],
    "conta": ["Conta", "conta"],
    "pix": ["PIX", "Chave PIX", "pix", "chave pix"],
    "codigo": ["Código", "Codigo", "ID", "código", "codigo", "id"],
    "autenticacao": [
        "Autenticação", "Autenticacao", "Comprovante",
        "autenticação", "autenticacao", "comprovante",
    ],
    "endereco": ["Endereço", "Endereco", "endereço", "endereco"],
    "cidade": ["Cidade", "cidade"],
    "estado": ["Estado", "UF", "estado", "uf"],
    "cep": ["CEP", "cep"],
    "telefone": ["Telefone", "Tel", "telefone", "tel"],
    "email": ["E-mail", "Email", "e-mail", "email"],
    "descricao": [
        "Descrição", "Descricao", "descrição", "descricao",
    ],
    "direcao": [
        "Direção", "Direcao", "Entrada/Saída", "Entrada/Saida",
        "Tipo Movimento", "direção", "direcao", "entrada/saída", "entrada/saida",
        "tipo movimento",
    ],
    "confianca": ["Confiança", "Confianca", "confiança", "confianca"],
    "observacoes": [
        "Observações", "Observacoes", "Obs", "Notas",
        "observações", "observacoes", "obs", "notas",
    ],
    "nome": ["Nome", "nome"],
}

# Campos obrigatorios - se nao encontrar a coluna, registrar erro
CAMPOS_OBRIGATORIOS: set[str] = {"valor"}


def mapear_colunas(cabecalhos: list[str]) -> dict[str, int | None]:
    """
    Dado uma lista de cabecalhos do Excel, retorna um mapeamento
    campo -> indice_da_coluna (0-based).

    Retorna None para campos sem coluna correspondente.
    """
    mapa: dict[str, int | None] = {}

    for campo, aliases in ALIASES.items():
        encontrado = False
        for alias in aliases:
            for idx, cab in enumerate(cabecalhos):
                if cab and cab.strip() == alias:
                    mapa[campo] = idx
                    encontrado = True
                    break
            if encontrado:
                break
        if not encontrado:
            mapa[campo] = None

    # Verificar campos obrigatorios
    faltando = [c for c in CAMPOS_OBRIGATORIOS if mapa.get(c) is None]
    if faltando:
        log.warning(f"Colunas obrigatorias nao encontradas no Excel: {faltando}")

    return mapa