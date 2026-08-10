"""Testes para validacao de dados."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from processamento.validacao import (
    validar_cpf,
    validar_cnpj,
    validar_cep,
    validar_data,
    validar_valor,
    validar_email,
    validar_dados_extraidos,
)


class TestValidarCPF:
    def test_cpf_valido(self):
        assert validar_cpf("52998224725") is True

    def test_cpf_invalido(self):
        assert validar_cpf("11111111111") is False
        assert validar_cpf("12345678900") is False
        assert validar_cpf("12345") is False

    def test_cpf_vazio(self):
        assert validar_cpf("") is False

    def test_cpf_todos_iguais(self):
        for d in range(10):
            assert validar_cpf(str(d) * 11) is False


class TestValidarCNPJ:
    def test_cnpj_valido(self):
        assert validar_cnpj("11222333000181") is True

    def test_cnpj_invalido(self):
        assert validar_cnpj("11111111111111") is False
        assert validar_cnpj("00000000000000") is False
        assert validar_cnpj("1234") is False

    def test_cnpj_vazio(self):
        assert validar_cnpj("") is False


class TestValidarCEP:
    def test_cep_valido(self):
        assert validar_cep("01310100") is True

    def test_cep_invalido(self):
        assert validar_cep("1234") is False
        assert validar_cep("") is False


class TestValidarData:
    def test_data_valida(self):
        assert validar_data("15/03/2024") is True

    def test_data_invalida(self):
        assert validar_data("") is False

    def test_data_ano_invalido(self):
        assert validar_data("15/03/1900") is False


class TestValidarValor:
    def test_valor_valido(self):
        assert validar_valor(100.50) is True
        assert validar_valor(1) is True

    def test_valor_invalido(self):
        assert validar_valor(0) is False
        assert validar_valor(-10) is False
        assert validar_valor(None) is False


class TestValidarDadosExtraidos:
    def test_documento_com_campos_uteis(self):
        dados = {"tipo_documento": "PIX", "valor": 100.0}
        resultado = validar_dados_extraidos(dados)
        assert resultado["valido"] is True

    def test_documento_sem_campos_uteis(self):
        dados = {"cep": "01310100"}
        resultado = validar_dados_extraidos(dados)
        assert resultado["valido"] is False

    def test_documento_cpf_invalido_gera_aviso(self):
        dados = {"tipo_documento": "PIX", "valor": 50.0, "cpf": "12345678900"}
        resultado = validar_dados_extraidos(dados)
        assert len(resultado["avisos"]) > 0