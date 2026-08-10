"""
Schemas Pydantic para Structured Outputs da OpenAI.
Define a estrutura dos dados extraidos dos documentos.
"""

from pydantic import BaseModel, Field
from typing import Optional


class DocumentoExtraido(BaseModel):
    """Schema principal para dados extraidos de comprovantes financeiros."""

    tipo_documento: Optional[str] = Field(
        None,
        description="Tipo do documento: PIX, TED, DOC, Boleto, Nota Fiscal, Comprovante, Recibo, Extrato, etc.",
    )
    empresa: Optional[str] = Field(
        None,
        description="Nome da empresa principal identificada no documento.",
    )
    nome: Optional[str] = Field(
        None,
        description="Nome da pessoa fisica principal identificada.",
    )
    pagador: Optional[str] = Field(
        None,
        description="Nome completo do pagador/remetente da transacao.",
    )
    recebedor: Optional[str] = Field(
        None,
        description="Nome completo do recebedor/destinatario/beneficiario da transacao.",
    )
    cpf: Optional[str] = Field(
        None,
        description="CPF identificado no documento (apenas digitos).",
    )
    cnpj: Optional[str] = Field(
        None,
        description="CNPJ identificado no documento (apenas digitos).",
    )
    valor: Optional[float] = Field(
        None,
        description="Valor principal da transacao em reais (float, ex: 1250.50).",
    )
    data: Optional[str] = Field(
        None,
        description="Data da transacao no formato DD/MM/AAAA.",
    )
    hora: Optional[str] = Field(
        None,
        description="Hora da transacao no formato HH:MM:SS ou HH:MM.",
    )
    banco: Optional[str] = Field(
        None,
        description="Nome do banco ou instituicao financeira.",
    )
    agencia: Optional[str] = Field(
        None,
        description="Numero da agencia bancaria.",
    )
    conta: Optional[str] = Field(
        None,
        description="Numero da conta bancaria.",
    )
    pix: Optional[str] = Field(
        None,
        description="Chave PIX utilizada (CPF, CNPJ, email, telefone ou chave aleatoria).",
    )
    codigo: Optional[str] = Field(
        None,
        description="Codigo da transacao, numero do documento, NSU ou identificador unico.",
    )
    autenticacao: Optional[str] = Field(
        None,
        description="Codigo de autenticacao ou comprovante.",
    )
    endereco: Optional[str] = Field(
        None,
        description="Endereco identificado no documento.",
    )
    cidade: Optional[str] = Field(
        None,
        description="Cidade identificada no documento.",
    )
    estado: Optional[str] = Field(
        None,
        description="Estado (UF) identificado no documento.",
    )
    cep: Optional[str] = Field(
        None,
        description="CEP identificado no documento (apenas digitos).",
    )
    telefone: Optional[str] = Field(
        None,
        description="Telefone identificado no documento.",
    )
    email: Optional[str] = Field(
        None,
        description="Email identificado no documento.",
    )
    descricao: Optional[str] = Field(
        None,
        description="Descricao da transacao ou servico.",
    )
    observacoes: Optional[str] = Field(
        None,
        description="Observacoes adicionais relevantes ou ambiguidades encontradas.",
    )
    confianca: Optional[float] = Field(
        None,
        description="Nivel de confianca geral da extracao de 0.0 a 1.0.",
    )