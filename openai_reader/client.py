"""
Cliente OpenAI - gerencia conexao e chamadas a API.
Utiliza o SDK oficial mais recente (openai>=1.30).
"""

import time
from typing import Any

import openai
from openai import OpenAI, APIError, APITimeoutError, RateLimitError, APIConnectionError

from config import OPENAI_API_KEY, OPENAI_MODEL, RETRY_MAX_ATTEMPTS, RETRY_BASE_DELAY, RETRY_MAX_DELAY
from logger import log


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
                if hasattr(e, "status_code") and e.status_code and e.status_code >= 500:
                    delay = min(RETRY_BASE_DELAY * (2 ** (attempt - 1)), RETRY_MAX_DELAY)
                    log.warning(f"Erro servidor {e.status_code} (tentativa {attempt}/{RETRY_MAX_ATTEMPTS}). Aguardando {delay}s...")
                    time.sleep(delay)
                else:
                    log.error(f"Erro da API OpenAI nao-retentavel: {e}")
                    raise

            except Exception as e:
                log.error(f"Erro inesperado na chamada OpenAI: {e}")
                raise

        log.error(f"Todas as {RETRY_MAX_ATTEMPTS} tentativas falharam para a chamada OpenAI")
        raise last_error  # type: ignore[misc]