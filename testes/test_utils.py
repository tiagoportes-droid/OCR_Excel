"""Testes para funcoes utilitarias."""

import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils import (
    calcular_md5,
    remover_acentos,
    normalizar_texto,
    parsear_nome_arquivo,
    extensao_suportada,
    eh_imagem,
    eh_pdf,
    formatar_tempo,
)
from processamento.normalizacao import (
    normalizar_moeda,
    normalizar_data,
    normalizar_espacos,
    limpar_cpf,
    limpar_cnpj,
    limpar_cep,
)


class TestMD5:
    def test_calcula_md5_correto(self, tmp_path):
        arquivo = tmp_path / "teste.txt"
        arquivo.write_bytes(b"conteudo de teste")
        esperado = hashlib.md5(b"conteudo de teste").hexdigest()
        assert calcular_md5(arquivo) == esperado

    def test_md5_arquivos_diferentes(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_bytes(b"aaa")
        f2.write_bytes(b"bbb")
        assert calcular_md5(f1) != calcular_md5(f2)

    def test_md5_arquivos_iguais(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_bytes(b"mesmo conteudo")
        f2.write_bytes(b"mesmo conteudo")
        assert calcular_md5(f1) == calcular_md5(f2)


class TestNormalizacaoTexto:
    def test_remover_acentos(self):
        assert remover_acentos("acao") == "acao"
        assert remover_acentos("cafe") == "cafe"

    def test_normalizar_texto_lowercase(self):
        resultado = normalizar_texto("Joao da Silva")
        assert resultado == "joao da silva"

    def test_normalizar_texto_espacos(self):
        resultado = normalizar_texto("  multiplos   espacos  ")
        assert "  " not in resultado


class TestNormalizacaoMoeda:
    def test_real_brasileiro(self):
        assert normalizar_moeda("R$ 1.250,50") == 1250.50

    def test_sem_simbolo(self):
        assert normalizar_moeda("1250,50") == 1250.50

    def test_formato_americano(self):
        assert normalizar_moeda("1250.50") == 1250.50

    def test_valor_inteiro(self):
        assert normalizar_moeda("R$ 100,00") == 100.00

    def test_vazio(self):
        assert normalizar_moeda("") is None
        assert normalizar_moeda(None) is None


class TestNormalizacaoData:
    def test_dd_mm_yyyy(self):
        assert normalizar_data("15/03/2024") == "15/03/2024"

    def test_yyyy_mm_dd(self):
        assert normalizar_data("2024-03-15") == "15/03/2024"

    def test_vazio(self):
        assert normalizar_data("") is None
        assert normalizar_data(None) is None


class TestLimpezaDocumentos:
    def test_limpar_cpf(self):
        assert limpar_cpf("123.456.789-09") == "12345678909"
        assert limpar_cpf("") == ""

    def test_limpar_cnpj(self):
        assert limpar_cnpj("12.345.678/0001-95") == "12345678000195"

    def test_limpar_cep(self):
        assert limpar_cep("01310-100") == "01310100"


class TestParseNomeArquivo:
    def test_tres_partes(self):
        p = Path("Joao - Osasco - Instalacao Eletrica.jpg")
        resultado = parsear_nome_arquivo(p)
        assert resultado["cliente"] == "Joao"
        assert resultado["local"] == "Osasco"
        assert resultado["servico"] == "Instalacao Eletrica"

    def test_duas_partes(self):
        p = Path("Maria - Manutencao.jpg")
        resultado = parsear_nome_arquivo(p)
        assert resultado["cliente"] == "Maria"
        assert resultado["local"] is None
        assert resultado["servico"] == "Manutencao"

    def test_uma_parte(self):
        p = Path("comprovante.pdf")
        resultado = parsear_nome_arquivo(p)
        assert resultado["cliente"] == "comprovante"
        assert resultado["local"] is None
        assert resultado["servico"] is None


class TestExtensoes:
    def test_extensao_suportada(self):
        assert extensao_suportada(Path("foto.jpg")) is True
        assert extensao_suportada(Path("doc.pdf")) is True
        assert extensao_suportada(Path("file.xyz")) is False

    def test_eh_imagem(self):
        assert eh_imagem(Path("foto.jpg")) is True
        assert eh_imagem(Path("doc.pdf")) is False

    def test_eh_pdf(self):
        assert eh_pdf(Path("doc.pdf")) is True
        assert eh_pdf(Path("foto.jpg")) is False


class TestFormatarTempo:
    def test_formatar(self):
        assert formatar_tempo(65) == "01:05"
        assert formatar_tempo(0) == "00:00"
        assert formatar_tempo(3600) == "60:00"