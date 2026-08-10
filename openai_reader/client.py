"""
Cliente OpenAI - gerencia conexao e chamadas a API.
Utiliza o SDK oficial mais recente (openai>=1.30).

Importante: quando a conta nao tem creditos (429 insufficient_quota /
credit_balance_exhausted), NAO faz retry — apenas registra WARNING e
desabilita novas chamadas durante a execucao atual.
"""

import time
from typing import Any

from openai import OpenAI, APIError, APITimeoutError, RateLimitError, APIConnectionError

from config import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    RETRY_MAX_ATTEMPTS,
    RETRY_BASE_DELAY,
    RETRY_MAX_DELAY,
)
from logger import log

# Sinaliza que a OpenAI esta sem creditos nesta execucao.
# Usado para evitar novas chamadas desnecessarias.
_OPENAI_SEM_CREDITOS = False


def openai_sem_creditos() -> bool:
    """True se a OpenAI ja foi detectada sem creditos nesta execucao."""
    return _OPENAI_SEM_CREDITOS


def _detectar_falta_creditos(e: Exception) -> bool:
    """Identifica erros de falta de creditos: 429, insufficient_quota, credit_balance_exhausted."""
    msg = str(e).lower()
    return (
        "429" in str(e)
        or "insufficient_quota" in msg
        or "credit_balance_exhausted" in msg
    )


class OpenAIClient:
    """Wrapper do cliente OpenAI com retry e logging."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self._api_key = api_key if api_key is not None else OPENAI_API_KEY
        self._model = model or OPENAI_MODEL

        if not self._api_key:
            raise ValueError("OPENAI_API_KEY nao configurada. Defina no arquivo .env")

        self._client = OpenAI(api_key=self._api_key)
        log.info(f"Cliente OpenAI inicializado | modelo={self._model}")

    @property
    def model(self) -> str:
        return self._model

    @property
    def client(self) -> OpenAI:
        return self._client

    def chat_completion(
        self,
        messages: list[dict[str, Any]],
        response_format: Any = None,
        max_tokens: int = 4096,
        temperature: float = 0.1,
    ) -> Any:
        """
        Executa chamada ao chat completions com retry e backoff exponencial.
        Suporta structured outputs via response_format (Pydantic model).
        """
        global _OPENAI_SEM_CREDITOS

        # Se jah detectamos falta de creditos, nao tentar novamente
        if _OPENAI_SEM_CREDITOS:
            raise RuntimeError("OpenAI desabilitado nesta execucao por falta de creditos")

        last_error: Exception | None = None

        for attempt in range(1, RETRY_MAX_ATTEMPTS + 1):
            try:
                kwargs: dict[str, Any] = {
                    "model": self._model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                }

                # Structured Outputs: usar beta.chat.completions.parse para Pydantic
                if response_format is not None:
                    response = self._client.beta.chat.completions.parse(
                        **kwargs,
                        response_format=response_format,
                    )
                else:
                    response = self._client.chat.completions.create(**kwargs)

                # Log de tokens
                usage = response.usage
                if usage:
                    log.info(
                        f"OpenAI | tokens_entrada={usage.prompt_tokens} "
                        f"tokens_saida={usage.completion_tokens} "
                        f"total={usage.total_tokens}"
                    )

                return response

            except RateLimitError as e:
                # 429 pode ser rate limit temporario OU falta de creditos
                if _detectar_falta_creditos(e):
                    _OPENAI_SEM_CREDITOS = True
                    log.warning("OpenAI Vision indisponivel por falta de creditos")
                    log.info("Continuando com PaddleOCR, Gemini e Qwen-VL")
                    raise RuntimeError("OpenAI sem creditos") from e

                last_error = e
                delay = min(RETRY_BASE_DELAY * (2 ** (attempt - 1)), RETRY_MAX_DELAY)
                log.warning(f"Rate limit atingido (tentativa {attempt}/{RETRY_MAX_ATTEMPTS}). Aguardando {delay}s...")
                time.sleep(delay)

            except APITimeoutError as e:
                last_error = e
                delay = min(RETRY_BASE_DELAY * (2 ** (attempt - 1)), RETRY_MAX_DELAY)
                log.warning(f"Timeout da API (tentativa {attempt}/{RETRY_MAX_ATTEMPTS}). Aguardando {delay}s...")
                time.sleep(delay)

            except APIConnectionError as e:
                last_error = e
                delay = min(RETRY_BASE_DELAY * (2 ** (attempt - 1)), RETRY_MAX_DELAY)
                log.warning(f"Erro de conexao (tentativa {attempt}/{RETRY_MAX_ATTEMPTS}). Aguardando {delay}s...")
                time.sleep(delay)

            except APIError as e:
                last_error = e
                if _detectar_falta_creditos(e):
                    _OPENAI_SEM_CREDITOS = True
                    log.warning("OpenAI Vision indisponivel por falta de creditos")
                    log.info("Continuando com PaddleOCR, Gemini e Qwen-VL")
                    raise RuntimeError("OpenAI sem creditos") from e

                status_code = getattr(e, "status_code", None)
                if status_code and status_code >= 500:
                    delay = min(RETRY_BASE_DELAY * (2 ** (attempt - 1)), RETRY_MAX_DELAY)
                    log.warning(f"Erro servidor {status_code} (tentativa {attempt}/{RETRY_MAX_ATTEMPTS}). Aguardando {delay}s...")
                    time.sleep(delay)
                else:
                    log.error(f"Erro da API OpenAI nao-retentavel: {e}")
                    raise

            except Exception as e:
                # Qualquer outra excecao pode conter mensagem de falta de creditos
                if _detectar_falta_creditos(e):
                    _OPENAI_SEM_CREDITOS = True
                    log.warning("OpenAI Vision indisponivel por falta de creditos")
                    log.info("Continuando com PaddleOCR, Gemini e Qwen-VL")
                    raise RuntimeError("OpenAI sem creditos") from e
                log.error(f"Erro inesperado na chamada OpenAI: {e}")
                raise

        log.error(f"Todas as {RETRY_MAX_ATTEMPTS} tentativas falharam para a chamada OpenAI")
        raise last_error  # type: ignore[misc]
