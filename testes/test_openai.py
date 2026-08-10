"""Testes para o cliente OpenAI (mocks)."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestOpenAIClient:
    """Testes para o cliente OpenAI utilizando mocks."""

    @patch("openai_reader.client.OpenAI")
    def test_instanciacao_sem_key_levanta_erro(self, mock_openai_class):
        from openai_reader.client import OpenAIClient

        with pytest.raises(ValueError):
            OpenAIClient(api_key="", model="gpt-4o")

    @patch("openai_reader.client.OpenAI")
    def test_instanciacao_com_key(self, mock_openai_class):
        from openai_reader.client import OpenAIClient

        client = OpenAIClient(api_key="sk-test-key", model="gpt-4o")
        assert client._model == "gpt-4o"
        mock_openai_class.assert_called_once_with(api_key="sk-test-key")

    @patch("openai_reader.client.OpenAI")
    def test_modelo_padrao(self, mock_openai_class):
        from openai_reader.client import OpenAIClient

        client = OpenAIClient(api_key="sk-test-key")
        assert client._model is not None
        assert len(client._model) > 0


class TestExtratorOpenAI:
    """Testes para o ExtratorOpenAI."""

    def test_media_type_jpg(self):
        from openai_reader.extractor import ExtratorOpenAI

        with patch("openai_reader.extractor.OpenAIClient"):
            extrator = ExtratorOpenAI.__new__(ExtratorOpenAI)
            extrator._client = MagicMock()
            mt = extrator._get_media_type(Path("foto.jpg"))
            assert mt == "image/jpeg"

    def test_media_type_png(self):
        from openai_reader.extractor import ExtratorOpenAI

        with patch("openai_reader.extractor.OpenAIClient"):
            extrator = ExtratorOpenAI.__new__(ExtratorOpenAI)
            extrator._client = MagicMock()
            mt = extrator._get_media_type(Path("img.png"))
            assert mt == "image/png"

    def test_media_type_desconhecido(self):
        from openai_reader.extractor import ExtratorOpenAI

        with patch("openai_reader.extractor.OpenAIClient"):
            extrator = ExtratorOpenAI.__new__(ExtratorOpenAI)
            extrator._client = MagicMock()
            mt = extrator._get_media_type(Path("file.xyz"))
            assert mt == "image/png"  # default