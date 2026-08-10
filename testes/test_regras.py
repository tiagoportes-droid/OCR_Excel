"""Testes para regras de negocio."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from processamento.regras import determinar_direcao, aplicar_dados_nome_arquivo, verificar_confianca_minima


class TestDeterminarDirecao:
    """Testes para classificacao Entrada/Saida."""

    # ---------- ENTRADA ----------

    def test_pagador_joyce(self):
        assert determinar_direcao("Joyce", None, None) == "Entrada"

    def test_pagador_diego(self):
        assert determinar_direcao("Diego", None, None) == "Entrada"

    def test_pagador_ricardo(self):
        assert determinar_direcao("Ricardo da Silva", None, None) == "Entrada"

    def test_pagador_nilson(self):
        assert determinar_direcao("Nilson", None, None) == "Entrada"

    def test_pagador_cleber(self):
        assert determinar_direcao("Cleber", None, None) == "Entrada"

    def test_pagador_avelino(self):
        assert determinar_direcao("Avelino", None, None) == "Entrada"

    def test_pagador_alvaro(self):
        assert determinar_direcao("Alvaro", None, None) == "Entrada"

    def test_pagador_marcos(self):
        assert determinar_direcao("Marcos", None, None) == "Entrada"

    def test_pagador_iara(self):
        assert determinar_direcao("Iara", None, None) == "Entrada"

    def test_pagador_vinicius(self):
        assert determinar_direcao("Vinicius", None, None) == "Entrada"

    def test_pagador_case_insensitive(self):
        assert determinar_direcao("JOYCE", None, None) == "Entrada"
        assert determinar_direcao("joyce", None, None) == "Entrada"

    # ---------- SAIDA (por pagador) ----------

    def test_pagador_portes_engenharia(self):
        r = determinar_direcao("PORTES ENGENHARIA", None, None)
        assert "Sa" in r  # Saida ou Saída

    def test_pagador_portes_case(self):
        r = determinar_direcao("Portes Engenharia", None, None)
        assert "Sa" in r

    # ---------- SAIDA (por tipo) ----------

    def test_tipo_getnet(self):
        r = determinar_direcao(None, None, "Getnet")
        assert "Sa" in r

    def test_tipo_sicoob(self):
        r = determinar_direcao(None, None, "Sicoob")
        assert "Sa" in r

    def test_tipo_jandibloc(self):
        r = determinar_direcao(None, None, "Nota Jandibloc")
        assert "Sa" in r

    # ---------- INDEFINIDO ----------

    def test_desconhecido(self):
        assert determinar_direcao("Pessoa Qualquer", None, "Outro") == "Indefinido"

    def test_nulo(self):
        assert determinar_direcao(None, None, None) == "Indefinido"


class TestAplicarDadosNomeArquivo:
    def test_sobrescreve_cliente(self):
        dados = {"nome": "IA Nome"}
        info = {"cliente": "Arquivo Nome", "local": None, "servico": None}
        resultado = aplicar_dados_nome_arquivo(dados, info)
        assert resultado["nome"] == "Arquivo Nome"

    def test_sobrescreve_local_e_servico(self):
        dados = {"cidade": "IA Cidade", "descricao": "IA Servico"}
        info = {"cliente": None, "local": "Osasco", "servico": "Pintura"}
        resultado = aplicar_dados_nome_arquivo(dados, info)
        assert resultado["cidade"] == "Osasco"
        assert resultado["descricao"] == "Pintura"


class TestVerificarConfianca:
    def test_confianca_acima(self):
        assert verificar_confianca_minima({"confianca": 0.8}) is True

    def test_confianca_abaixo(self):
        assert verificar_confianca_minima({"confianca": 0.2}, limiar=0.4) is False

    def test_confianca_ausente(self):
        assert verificar_confianca_minima({}) is True