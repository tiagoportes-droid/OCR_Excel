"""
Testes do sistema multi-provider OCR.

Cobre os 12 cenarios especificados:
1. OpenAI funcionando
2. OpenAI 429 credit_balance_exhausted - programa continua
3. PaddleOCR funcionando
4. PaddleOCR indisponivel
5. Gemini funcionando
6. Gemini indisponivel
7. Qwen-VL funcionando
8. Qwen-VL indisponivel
9. Todos retornando o mesmo texto -> CONFIRMED/HIGH
10. Dois providers iguais e um diferente -> CONSENSUS + divergencia
11. Todos diferentes -> DIVERGENT/LOW
12. Nenhum provider funcionando -> OCR_FAILED sem crash
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Garantir que a raiz do projeto esta no path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ocr.comparator import OCRResultComparator, normalizar_texto, comparar_textos
from ocr.manager import OCRManager


# ============================================================
# Fixtures e helpers
# ============================================================

def _resultado(provider: str, texto: str | None = None, conf: float = 0.9, success: bool = True, error: str | None = None) -> dict:
    """Cria resultado padronizado de provider."""
    return {
        "provider": provider,
        "success": success,
        "text": texto if success else None,
        "confidence": conf if success else 0.0,
        "error": error,
    }


@pytest.fixture
def comparador() -> OCRResultComparator:
    return OCRResultComparator(require_consensus=True, min_confidence=0.80)


@pytest.fixture
def imagem_teste(tmp_path: Path) -> Path:
    """Cria imagem PNG de teste."""
    img = tmp_path / "documento.png"
    # Criar PNG minimo valido (1x1 pixel)
    import base64
    png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
        "z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )
    img.write_bytes(base64.b64decode(png_b64))
    return img


# ============================================================
# Teste 1: OpenAI funcionando
# ============================================================

class TestOpenAIProvider:
    @patch("ocr.providers.OpenAIProvider._get_client")
    def test_openai_funcionando(self, mock_get_client, imagem_teste: Path):
        """OpenAI retorna texto com sucesso."""
        from ocr.providers import OpenAIProvider

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "Pedido 12345\nValor R$ 150,00"
        mock_client.chat.completions.create.return_value = mock_resp
        mock_get_client.return_value = mock_client

        provider = OpenAIProvider()
        res = provider.analyze(imagem_teste)

        assert res["success"] is True
        assert "Pedido 12345" in res["text"]
        assert "R$ 150,00" in res["text"]
        assert res["confidence"] > 0

    @patch("ocr.providers.OpenAIProvider._get_client")
    def test_openai_429_credit_balance(self, mock_get_client, imagem_teste: Path):
        """OpenAI retornando 429 credit_balance_exhausted - provider falha mas nao crasha."""
        from ocr.providers import OpenAIProvider

        mock_client = MagicMock()
        err = Exception("429 - insufficient_quota - credit_balance_exhausted")
        mock_client.chat.completions.create.side_effect = err
        mock_get_client.return_value = mock_client

        provider = OpenAIProvider()
        res = provider.analyze(imagem_teste)

        assert res["success"] is False
        assert "creditos" in res["error"].lower() or "credit" in res["error"].lower()

    @patch("ocr.providers.OpenAIProvider._get_client")
    def test_openai_429_desabilita_durante_execucao(self, mock_get_client, imagem_teste: Path):
        """Apos 429, OpenAI nao e chamada novamente nesta execucao."""
        from ocr import providers

        # Reset do flag global (pode ter ficado True de teste anterior)
        providers._OPENAI_SEM_CREDITOS = False

        mock_client = MagicMock()
        err = Exception("429 - credit_balance_exhausted")
        mock_client.chat.completions.create.side_effect = err
        mock_get_client.return_value = mock_client

        provider = providers.OpenAIProvider()
        provider.analyze(imagem_teste)  # primeira chamada -> 429

        # Segunda chamada deve falhar sem tentar a API novamente
        res = provider.analyze(imagem_teste)
        assert res["success"] is False
        assert mock_client.chat.completions.create.call_count == 1

        # Reset para nao afetar outros testes
        providers._OPENAI_SEM_CREDITOS = False


# ============================================================
# Teste 3/4: PaddleOCR
# ============================================================

class TestPaddleOCRProvider:
    @patch("ocr.providers.PaddleOCRProvider._get_ocr")
    def test_paddleocr_funcionando(self, mock_get_ocr, imagem_teste: Path):
        """PaddleOCR retorna texto e confianca."""
        from ocr.providers import PaddleOCRProvider

        mock_ocr = MagicMock()
        # Estrutura: [[ [ [box], (text, conf) ] ]]
        mock_ocr.ocr.return_value = [
            [
                [
                    [[10, 10], [100, 10], [100, 30], [10, 30]],
                    ("Pedido 12345", 0.95),
                ],
                [
                    [[10, 40], [100, 40], [100, 60], [10, 60]],
                    ("Valor R$ 150,00", 0.92),
                ],
            ]
        ]
        mock_get_ocr.return_value = mock_ocr

        provider = PaddleOCRProvider()
        res = provider.analyze(imagem_teste)

        assert res["success"] is True
        assert "Pedido 12345" in res["text"]
        assert "R$ 150,00" in res["text"]
        assert res["confidence"] > 0.9

    @patch("ocr.providers.PaddleOCRProvider._get_ocr")
    def test_paddleocr_indisponivel(self, mock_get_ocr, imagem_teste: Path):
        """PaddleOCR nao instalado - retorna erro sem crash."""
        from ocr.providers import PaddleOCRProvider

        mock_get_ocr.return_value = None
        provider = PaddleOCRProvider()
        res = provider.analyze(imagem_teste)

        assert res["success"] is False
        assert res["error"] is not None


# ============================================================
# Teste 5/6: Gemini
# ============================================================

class TestGeminiProvider:
    @patch("ocr.providers.GeminiProvider._get_client")
    def test_gemini_funcionando(self, mock_get_client, imagem_teste: Path):
        """Gemini retorna texto com sucesso."""
        from ocr.providers import GeminiProvider

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_part = MagicMock()
        mock_part.text = "Pedido 12345\nValor R$ 150,00"
        mock_candidate = MagicMock()
        mock_candidate.content.parts = [mock_part]
        mock_resp.candidates = [mock_candidate]
        mock_client.models.generate_content.return_value = mock_resp
        mock_get_client.return_value = mock_client

        provider = GeminiProvider()
        res = provider.analyze(imagem_teste)

        assert res["success"] is True
        assert "Pedido 12345" in res["text"]
        assert res["confidence"] > 0

    def test_gemini_indisponivel(self, imagem_teste: Path):
        """Gemini sem API key - retorna erro sem crash."""
        from ocr import providers

        with patch("ocr.providers.GEMINI_API_KEY", ""):
            provider = providers.GeminiProvider()
            res = provider.analyze(imagem_teste)
            assert res["success"] is False
            assert "configurado" in res["error"].lower()


# ============================================================
# Teste 7/8: Qwen-VL
# ============================================================

class TestQwenVLProvider:
    @patch("ocr.providers.QwenVLProvider._analyze_ollama")
    def test_qwen_funcionando_via_ollama(self, mock_ollama, imagem_teste: Path):
        """Qwen-VL via Ollama retorna texto."""
        from ocr.providers import QwenVLProvider

        mock_ollama.return_value = {
            "provider": "qwen", "success": True,
            "text": "Pedido 12345\nValor R$ 150,00",
            "confidence": 0.85, "error": None,
        }
        provider = QwenVLProvider()
        res = provider.analyze(imagem_teste)

        assert res["success"] is True
        assert "Pedido 12345" in res["text"]

    @patch("ocr.providers.QwenVLProvider._analyze_ollama")
    @patch("ocr.providers.QwenVLProvider._get_pipe")
    def test_qwen_indisponivel(self, mock_pipe, mock_ollama, imagem_teste: Path):
        """Qwen-VL indisponivel (Ollama down e HF sem transformers)."""
        from ocr.providers import QwenVLProvider

        mock_pipe.return_value = None
        # Forcar excecao na chamada Ollama
        mock_ollama.side_effect = Exception("Connection refused")
        # Forcar modo ollama para testar fallback
        provider = QwenVLProvider()
        provider._modo = "ollama"
        with patch("ocr.providers.QwenVLProvider._ollama_disponivel", return_value=False):
            res = provider.analyze(imagem_teste)

        # Pode falhar de forma controlada
        assert isinstance(res, dict)
        assert "success" in res


# ============================================================
# Testes do Comparador (Testes 9-12)
# ============================================================

class TestOCRResultComparator:
    def test_9_todos_iguais_confirmed_high(self, comparador: OCRResultComparator):
        """9. Todos retornando o mesmo texto -> CONFIRMED/HIGH"""
        resultados = [
            _resultado("paddleocr", "Pedido 12345\nValor R$ 150,00", conf=0.95),
            _resultado("gemini", "Pedido 12345\nValor R$ 150,00"),
            _resultado("qwen", "Pedido 12345\nValor R$ 150,00"),
        ]
        final = comparador.comparar(resultados)

        assert final["success"] is True
        assert final["status"] == "confirmed"
        assert final["confidence"] == "high"
        assert final["divergence"] is False
        assert "Pedido 12345" in final["final_text"]
        assert "R$ 150,00" in final["final_text"]

    def test_10_dois_iguais_um_diferente_consensus(self, comparador: OCRResultComparator):
        """10. Dois providers iguais e um diferente -> CONSENSUS + divergencia."""
        resultados = [
            _resultado("paddleocr", "Pedido 12345\nValor R$ 150,00", conf=0.95),
            _resultado("gemini", "Pedido 12345\nValor R$ 150,00"),
            _resultado("qwen", "Pedido 12345\nValor R$ 180,00"),
        ]
        final = comparador.comparar(resultados)

        assert final["success"] is True
        assert final["status"] in ("confirmed", "consensus")
        assert final["divergence"] is True
        assert "150,00" in final["final_text"]
        # Provider discordante identificado
        assert any(
            r["provider"] == "qwen" for r in final.get("divergent_providers", [])
        )

    def test_11_todos_diferentes_divergent_low(self, comparador: OCRResultComparator):
        """11. Todos retornando resultados diferentes -> DIVERGENT/LOW."""
        resultados = [
            _resultado("paddleocr", "Pedido 12345\nValor R$ 150,00"),
            _resultado("gemini", "Pedido 54321\nValor R$ 180,00"),
            _resultado("qwen", "Pedido 99999\nValor R$ 200,00"),
        ]
        final = comparador.comparar(resultados)

        assert final["success"] is False
        assert final["status"] == "divergent"
        assert final["confidence"] == "low"
        assert final["divergence"] is True
        assert final["final_text"] is None

    def test_12_nenhum_provider_funcionando(self, comparador: OCRResultComparator):
        """12. Nenhum provider funcionando -> OCR_FAILED sem crash."""
        resultados = [
            _resultado("paddleocr", None, success=False, error="PaddleOCR nao instalado"),
            _resultado("gemini", None, success=False, error="Sem API key"),
            _resultado("qwen", None, success=False, error="Ollama down"),
        ]
        final = comparador.comparar(resultados)

        assert final["success"] is False
        assert final["status"] == "ocr_failed"
        assert final["confidence"] == "very_low"
        assert final["divergence"] is False

    def test_valores_monetarios_diferentes_nao_ignorados(self):
        """R$ 150,00 vs R$ 180,00 devem ser diferentes."""
        assert comparar_textos(
            "Pedido 12345\nValor R$ 150,00",
            "Pedido 12345\nValor R$ 180,00",
        ) is False

    def test_codigos_diferentes_nao_ignorados(self):
        """Pedido 12345 vs Pedido 12346 devem ser diferentes."""
        assert comparar_textos(
            "Pedido 12345\nValor R$ 150,00",
            "Pedido 12346\nValor R$ 150,00",
        ) is False

    def test_espacos_e_maiusculas_normalizadas(self):
        """Espacos duplicados e maiusculas sao normalizadas."""
        assert comparar_textos(
            "Pedido  12345\n VALOR R$ 150,00",
            "pedido 12345\nvalor R$ 150,00",
        ) is True

    def test_normalizacao_preserva_numeros(self):
        """Numeros e valores monetarios nao sao alterados pela normalizacao."""
        n = normalizar_texto("Pedido  12345\n\n\n Valor R$ 150,00  ")
        assert "12345" in n
        assert "150,00" in n


# ============================================================
# Teste do OCRManager (orquestracao)
# ============================================================

class TestOCRManager:
    @patch("ocr.manager.criar_providers")
    def test_manager_paralelo_com_todos_ok(self, mock_providers, imagem_teste: Path):
        """Manager executa providers e retorna resultado consolidado."""
        from ocr.providers import OCRProvider

        class FakeProvider(OCRProvider):
            def __init__(self, nome: str, texto: str):
                self.name = nome
                self._texto = texto

            def analyze(self, image_path):
                return _resultado(self.name, self._texto, conf=0.9)

        fake_providers = [
            FakeProvider("paddleocr", "Pedido 12345\nValor R$ 150,00"),
            FakeProvider("gemini", "Pedido 12345\nValor R$ 150,00"),
        ]
        mock_providers.return_value = fake_providers

        OCRManager.reiniciar()
        manager = OCRManager()
        res = manager.analisar_imagem(imagem_teste)

        assert res["success"] is True
        assert res["status"] == "confirmed"
        assert res["confidence"] == "high"
        assert "Pedido 12345" in (res.get("final_text") or "")

        OCRManager.reiniciar()

    @patch("ocr.manager.criar_providers")
    def test_manager_sobrevive_provider_com_erro(self, mock_providers, imagem_teste: Path):
        """Provider que falha nao derruba os outros."""
        from ocr.providers import OCRProvider

        class BomProvider(OCRProvider):
            def __init__(self, nome: str, texto: str):
                self.name = nome
                self._texto = texto

            def analyze(self, image_path):
                return _resultado(self.name, self._texto, conf=0.9)

        class RuimProvider(OCRProvider):
            def __init__(self, nome: str):
                self.name = nome

            def analyze(self, image_path):
                raise Exception("Falha critica")

        fake_providers = [
            BomProvider("paddleocr", "Pedido 12345\nValor R$ 150,00"),
            RuimProvider("qwen"),
        ]
        mock_providers.return_value = fake_providers

        OCRManager.reiniciar()
        manager = OCRManager()
        res = manager.analisar_imagem(imagem_teste)

        assert res["success"] is True
        assert "Pedido 12345" in (res.get("final_text") or "")

        OCRManager.reiniciar()

    @patch("ocr.manager.criar_providers")
    def test_manager_sem_providers_ocr_failed(self, mock_providers, imagem_teste: Path):
        """Nenhum provider -> OCR_FAILED sem crash."""
        mock_providers.return_value = []

        OCRManager.reiniciar()
        manager = OCRManager()
        res = manager.analisar_imagem(imagem_teste)

        assert res["success"] is False
        assert res["status"] == "ocr_failed"

        OCRManager.reiniciar()