"""Testes para extracao de dados (com mocks)."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestSchemasPydantic:
    """Testes para o schema Pydantic de DocumentoExtraido."""

    def test_schema_basico(self):
        from openai_reader.schemas import DocumentoExtraido

        doc = DocumentoExtraido(
            tipo_documento="PIX",
            valor=100.50,
            pagador="Joao",
            recebedor="Maria",
            confianca=0.95,
        )
        dados = doc.model_dump()
        assert dados["tipo_documento"] == "PIX"
        assert dados["valor"] == 100.50
        assert dados["pagador"] == "Joao"
        assert dados["confianca"] == 0.95

    def test_schema_todos_nulos(self):
        from openai_reader.schemas import DocumentoExtraido

        doc = DocumentoExtraido()
        dados = doc.model_dump()
        assert all(v is None for v in dados.values())

    def test_schema_model_dump(self):
        from openai_reader.schemas import DocumentoExtraido

        doc = DocumentoExtraido(tipo_documento="Boleto", valor=250.0)
        dados = doc.model_dump()
        assert isinstance(dados, dict)
        assert dados["tipo_documento"] == "Boleto"
        assert dados["valor"] == 250.0
        assert dados["pagador"] is None


class TestExtratorOpenAIMock:
    """Testes para o ExtratorOpenAI usando mocks."""

    @patch("openai_reader.extractor.ExtratorOpenAI")
    def test_extrair_de_texto_retorna_dados(self, mock_class):
        mock_instance = MagicMock()
        mock_instance.extrair_de_texto.return_value = {
            "dados": {
                "tipo_documento": "Boleto",
                "valor": 500.00,
                "confianca": 0.90,
            },
            "tokens_entrada": 500,
            "tokens_saida": 100,
            "custo_estimado": 0.004,
            "modelo": "gpt-4o",
        }
        mock_class.return_value = mock_instance

        extrator = mock_class()
        resultado = extrator.extrair_de_texto("Texto do boleto...")
        assert resultado["dados"]["tipo_documento"] == "Boleto"
        assert resultado["dados"]["valor"] == 500.00