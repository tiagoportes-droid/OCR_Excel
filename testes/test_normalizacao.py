"""Testes para normalizacao de dados."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from processamento.normalizacao import (
    normalizar_documento_extraido,
    normalizar_moeda,
    normalizar_data,
    normalizar_espacos,
    limpar_cpf,
    limpar_cnpj,
    limpar_cep,
    remover_acentos,
)


class TestNormalizarDocumento:
    def test_normaliza_cpf(self):
        dados = {"cpf": "123.456.789-09"}
        resultado = normalizar_documento_extraido(dados)
        assert resultado["cpf"] == "12345678909"

    def test_normaliza_cnpj(self):
        dados = {"cnpj": "12.345.678/0001-95"}
        resultado = normalizar_documento_extraido(dados)
        assert resultado["cnpj"] == "12345678000195"

    def test_normaliza_cep(self):
        dados = {"cep": "01310-100"}
        resultado = normalizar_documento_extraido(dados)
        assert resultado["cep"] == "01310100"

    def test_normaliza_valor_string(self):
        dados = {"valor": "R$ 1.250,50"}
        resultado = normalizar_documento_extraido(dados)
        assert resultado["valor"] == 1250.50

    def test_normaliza_data(self):
        dados = {"data": "2024-03-15"}
        resultado = normalizar_documento_extraido(dados)
        assert resultado["data"] == "15/03/2024"

    def test_normaliza_nomes(self):
        dados = {"nome": "  Joao   da   Silva  "}
        resultado = normalizar_documento_extraido(dados)
        assert resultado["nome"] == "Joao da Silva"

    def test_dados_nulos(self):
        resultado = normalizar_documento_extraido({})
        assert resultado == {}

    def test_dados_none(self):
        resultado = normalizar_documento_extraido(None)
        assert resultado is None


class TestNormalizarMoeda:
    def test_brasileiro(self):
        assert normalizar_moeda("R$ 1.250,50") == 1250.50

    def test_inteiro(self):
        assert normalizar_moeda(100) == 100.0

    def test_float(self):
        assert normalizar_moeda(99.99) == 99.99


class TestRemoverAcentos:
    def test_basico(self):
        assert remover_acentos("acao") == "acao"
        assert remover_acentos("") == ""