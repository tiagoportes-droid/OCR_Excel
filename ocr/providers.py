"""Providers de OCR independentes."""
from __future__ import annotations
import base64
from pathlib import Path
from typing import Any

from config import (
    OPENAI_ENABLED, OPENAI_API_KEY, OPENAI_MODEL,
    PADDLEOCR_ENABLED, GEMINI_ENABLED, GEMINI_API_KEY,
    GEMINI_MODEL, QWEN_ENABLED, QWEN_MODEL, QWEN_BASE_URL,
)
from logger import log

_OPENAI_SEM_CREDITOS = False

PROMPT = (
    "Extraia todo o texto visivel desta imagem. "
    "Inclua numeros, valores, datas, codigos e identificadores "
    "exatamente como aparecem. Responda apenas com o texto extraido."
)


class OCRProvider:
    """Interface base."""
    name = "base"

    def analyze(self, image_path: Path) -> dict[str, Any]:
        raise NotImplementedError

    def _r(self, text=None, success=True, conf=0.0, error=None):
        return {
            "provider": self.name,
            "success": success,
            "text": text,
            "confidence": conf,
            "error": error,
        }


class OpenAIProvider(OCRProvider):
    """OpenAI Vision (opcional)."""
    name = "openai"

    def __init__(self):
        self._client = None
        self._model = OPENAI_MODEL or "gpt-4o"

    def _get_client(self):
        global _OPENAI_SEM_CREDITOS
        if _OPENAI_SEM_CREDITOS or self._client is None:
            if _OPENAI_SEM_CREDITOS:
                return None
            if not OPENAI_API_KEY:
                log.warning("OPENAI_API_KEY nao configurada - OpenAI desabilitado")
                return None
            from openai import OpenAI
            self._client = OpenAI(api_key=OPENAI_API_KEY)
        return self._client

    def analyze(self, image_path):
        global _OPENAI_SEM_CREDITOS
        if _OPENAI_SEM_CREDITOS:
            return self._r(success=False, error="OpenAI desabilitado nesta execucao")
        client = self._get_client()
        if client is None:
            return self._r(success=False, error="OpenAI nao disponivel")
        try:
            data = base64.b64encode(image_path.read_bytes()).decode()
            ext = image_path.suffix.lower()
            mt = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
                  ".bmp": "image/bmp", ".webp": "image/webp"}.get(ext, "image/png")
            resp = client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:{mt};base64,{data}", "detail": "high"}},
                ]}],
                max_tokens=4096,
            )
            text = resp.choices[0].message.content or ""
            return self._r(text=text.strip(), conf=0.95)
        except Exception as e:
            msg = str(e).lower()
            if "429" in str(e) or "insufficient_quota" in msg or "credit_balance_exhausted" in msg:
                _OPENAI_SEM_CREDITOS = True
                log.warning("OpenAI Vision indisponivel por falta de creditos")
                log.info("Continuando com PaddleOCR, Gemini e Qwen-VL")
                return self._r(success=False, error="OpenAI sem creditos")
            log.warning(f"OpenAI falhou: {e}")
            return self._r(success=False, error=str(e))


class PaddleOCRProvider(OCRProvider):
    """PaddleOCR local (principal fallback)."""
    name = "paddleocr"
    _inst = None

    def _get_ocr(self):
        if PaddleOCRProvider._inst is None:
            try:
                from paddleocr import PaddleOCR
                log.info("Inicializando PaddleOCR (primeira vez)")
                PaddleOCRProvider._inst = PaddleOCR(use_angle_cls=True, lang="pt", show_log=False)
            except ImportError:
                log.warning("PaddleOCR nao esta instalado")
                log.info("Continuando com os providers disponiveis")
                return None
        return PaddleOCRProvider._inst

    def analyze(self, image_path):
        ocr = self._get_ocr()
        if ocr is None:
            return self._r(success=False, error="PaddleOCR nao instalado")
        try:
            res = ocr.ocr(str(image_path), cls=True)
            linhas, confs = [], []
            if res:
                for page in res:
                    if page:
                        for line in page:
                            if line and len(line) >= 2:
                                txt = line[1][0] if isinstance(line[1], (list, tuple)) else str(line[1])
                                # Confianca: linha[1] = (texto, confianca) -> line[1][1]
                                c = line[1][1] if isinstance(line[1], (list, tuple)) and len(line[1]) > 1 else 0.0
                                linhas.append(txt)
                                if isinstance(c, (int, float)):
                                    confs.append(float(c))
            final = "\n".join(linhas)
            conf = sum(confs) / len(confs) if confs else 0.0
            log.info(f"PaddleOCR concluido | {len(linhas)} linhas | conf={conf:.2f}")
            return self._r(text=final, conf=conf)
        except Exception as e:
            log.warning(f"PaddleOCR falhou: {e}")
            return self._r(success=False, error=str(e))


class GeminiProvider(OCRProvider):
    """Google Gemini multimodal."""
    name = "gemini"

    def __init__(self):
        self._client = None
        self._model = GEMINI_MODEL or "gemini-2.0-flash"

    def _get_client(self):
        if self._client is None:
            if not GEMINI_API_KEY:
                log.warning("GEMINI_API_KEY nao configurada - Gemini desabilitado")
                return None
            from google import genai
            self._client = genai.Client(api_key=GEMINI_API_KEY)
        return self._client

    def analyze(self, image_path):
        client = self._get_client()
        if client is None:
            return self._r(success=False, error="Gemini nao configurado")
        try:
            resp = client.models.generate_content(
                model=self._model,
                contents=[PROMPT, image_path.read_bytes()],
                config={"response_modalities": ["TEXT"]},
            )
            text = ""
            if resp.candidates:
                text = resp.candidates[0].content.parts[0].text or ""
            log.info(f"Gemini concluido | {len(text)} chars")
            return self._r(text=text.strip(), conf=0.90)
        except Exception as e:
            log.warning(f"Gemini falhou: {e}")
            return self._r(success=False, error=str(e))


class QwenVLProvider(OCRProvider):
    """
    Qwen-VL multimodal.

    Prioriza Ollama (simples e leve). Se Ollama nao estiver disponivel,
    tenta Hugging Face Transformers como fallback.

    Modelo padrao: qwen2.5vl:3b (quantizado, roda em 16GB RAM sem GPU dedicada)
    Configuravel via .env: QWEN_MODEL e QWEN_BASE_URL.
    """
    name = "qwen"

    def __init__(self):
        self._pipe = None
        self._processor = None
        # QWEN_MODEL: para Ollama use "qwen2.5vl:3b"; para HF use "Qwen/Qwen2.5-VL-3B-Instruct"
        self._model_name = QWEN_MODEL or "qwen2.5vl:3b"
        self._base_url = QWEN_BASE_URL or "http://localhost:11434"
        self._modo = "ollama" if ":" in self._model_name and "/" not in self._model_name else "huggingface"

    def _ollama_disponivel(self) -> bool:
        """Verifica se Ollama esta rodando localmente."""
        try:
            import urllib.request
            import json
            req = urllib.request.Request(
                f"{self._base_url}/api/tags",
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=2) as resp:
                data = json.loads(resp.read().decode())
            return bool(data.get("models"))
        except Exception:
            return False

    def _get_pipe(self):
        """Carrega Qwen via Hugging Face (fallback)."""
        if self._pipe is None:
            try:
                from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
                log.info(f"Carregando Qwen-VL (HF): {self._model_name}")
                self._pipe = Qwen2_5_VLForConditionalGeneration.from_pretrained(
                    self._model_name, device_map="cpu"
                )
                self._processor = AutoProcessor.from_pretrained(self._model_name)
                log.info("Qwen-VL (HF) carregado")
            except ImportError:
                log.warning("transformers nao instalado - Qwen desabilitado")
                return None
            except Exception as e:
                log.warning(f"Falha ao carregar Qwen-VL (HF): {e}")
                return None
        return self._pipe

    def analyze(self, image_path):
        # 1) Tentar Ollama primeiro
        if self._modo == "ollama" or self._ollama_disponivel():
            try:
                return self._analyze_ollama(image_path)
            except Exception as e:
                log.warning(f"Qwen-VL (Ollama) falhou: {e}")
                # Se Ollama falhar, tentar HF como fallback (se modo era ollama)
                if self._modo == "huggingface":
                    pass
                elif self._get_pipe() is not None:
                    log.info("Qwen-VL | Ollama indisponivel, tentando Hugging Face")
                    try:
                        return self._analyze_hf(image_path)
                    except Exception as e2:
                        log.warning(f"Qwen-VL (HF) falhou: {e2}")
                        return self._r(success=False, error=str(e2))
                return self._r(success=False, error="Qwen-VL nao disponivel")

        # 2) Fallback: Hugging Face Transformers
        pipe = self._get_pipe()
        if pipe is None:
            return self._r(success=False, error="Qwen-VL nao disponivel")
        try:
            return self._analyze_hf(image_path)
        except Exception as e:
            log.warning(f"Qwen-VL falhou: {e}")
            return self._r(success=False, error=str(e))

    def _analyze_ollama(self, image_path) -> dict:
        """Executa Qwen-VL via Ollama API."""
        import base64
        import json
        import urllib.request

        image_b64 = base64.b64encode(image_path.read_bytes()).decode()
        payload = {
            "model": self._model_name,
            "prompt": PROMPT,
            "images": [image_b64],
            "stream": False,
            "options": {"temperature": 0.1},
        }

        req = urllib.request.Request(
            f"{self._base_url}/api/generate",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode())

        text = (data.get("response") or "").strip()
        log.info(f"Qwen-VL (Ollama) concluido | {len(text)} chars")
        return self._r(text=text, conf=0.85)

    def _analyze_hf(self, image_path) -> dict:
        """Executa Qwen-VL via Hugging Face Transformers."""
        from qwen_vl_utils import process_vision_info

        messages = [{"role": "user", "content": [
            {"type": "image", "image": f"file://{image_path}"},
            {"type": "text", "text": PROMPT}]}]
        text = self._processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = self._processor(
            text=[text], images=image_inputs, videos=video_inputs,
            padding=True, return_tensors="pt",
        )
        outputs = self._pipe.generate(**inputs, max_new_tokens=1024)
        gen = self._processor.batch_decode(
            outputs[:, inputs.input_ids.shape[1]:], skip_special_tokens=True
        )
        extra = gen[0].strip()
        log.info(f"Qwen-VL (HF) concluido | {len(extra)} chars")
        return self._r(text=extra, conf=0.85)


def criar_providers():
    """Cria providers ativos conforme .env."""
    providers = []
    if OPENAI_ENABLED:
        providers.append(OpenAIProvider())
    if PADDLEOCR_ENABLED:
        providers.append(PaddleOCRProvider())
    if GEMINI_ENABLED:
        providers.append(GeminiProvider())
    if QWEN_ENABLED:
        providers.append(QwenVLProvider())
    if not providers:
        providers.append(PaddleOCRProvider())
    return providers
