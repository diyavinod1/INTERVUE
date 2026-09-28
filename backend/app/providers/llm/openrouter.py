"""
OpenRouter implementation of LLMProvider.

Behavior:
  - Calls the primary model (OPENROUTER_MODEL).
  - Retries transient failures (timeouts, 429, 5xx) a limited number of
    times with exponential backoff - never indefinitely.
  - If the primary model still fails after retries, tries the fallback
    model (OPENROUTER_FALLBACK_MODEL) ONCE.
  - If both fail, raises LLMProviderError so callers (agents/nodes) can
    degrade gracefully instead of the interview silently breaking.

We use the OpenAI-compatible /chat/completions endpoint that OpenRouter
exposes, called directly with httpx (LangChain's ChatOpenAI-compatible
wrapper is used at the LangChain integration layer in llm_service.py for
prompt templating / structured output; this module is the raw transport).
"""
import asyncio
import random

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.core.logging import get_logger
from app.providers.llm.base import LLMMessage, LLMProvider, LLMResponse

logger = get_logger(__name__)


class LLMProviderError(Exception):
    pass


class _RetryableError(Exception):
    pass


class OpenRouterProvider(LLMProvider):
    def __init__(self) -> None:
        self.settings = get_settings()

    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int = 600,
        json_mode: bool = False,
    ) -> LLMResponse:
        if not self.settings.openrouter_api_key:
            raise LLMProviderError(
                "OPENROUTER_API_KEY is not set. Add it to backend/.env (see .env.example)."
            )

        try:
            text = await self._call_with_retries(
                self.settings.openrouter_model, messages, temperature, max_tokens, json_mode
            )
            return LLMResponse(text=text, model_used=self.settings.openrouter_model, used_fallback=False)
        except Exception as primary_error:  # noqa: BLE001
            logger.warning(
                "primary_model_failed model=%s error=%s -- attempting fallback",
                self.settings.openrouter_model,
                type(primary_error).__name__,
            )
            if not self.settings.openrouter_fallback_model:
                raise LLMProviderError(f"Primary model failed and no fallback configured: {primary_error}") from primary_error

            try:
                text = await self._call_once(
                    self.settings.openrouter_fallback_model, messages, temperature, max_tokens, json_mode
                )
                return LLMResponse(text=text, model_used=self.settings.openrouter_fallback_model, used_fallback=True)
            except Exception as fallback_error:  # noqa: BLE001
                logger.error(
                    "fallback_model_failed model=%s error=%s",
                    self.settings.openrouter_fallback_model,
                    type(fallback_error).__name__,
                )
                raise LLMProviderError(
                    f"Both primary and fallback models failed. primary={primary_error} fallback={fallback_error}"
                ) from fallback_error

    async def _call_with_retries(
        self, model: str, messages: list[LLMMessage], temperature: float, max_tokens: int, json_mode: bool
    ) -> str:
        max_attempts = max(1, self.settings.openrouter_max_retries + 1)
        last_error: Exception | None = None
        for attempt in range(max_attempts):
            try:
                return await self._call_once(model, messages, temperature, max_tokens, json_mode)
            except _RetryableError as e:
                last_error = e
                if attempt < max_attempts - 1:
                    backoff = (2 ** attempt) + random.uniform(0, 0.5)
                    logger.warning("openrouter_retry attempt=%d backoff=%.1fs", attempt + 1, backoff)
                    await asyncio.sleep(backoff)
        raise LLMProviderError(f"OpenRouter call failed after {max_attempts} attempts: {last_error}")

    async def _call_once(
        self, model: str, messages: list[LLMMessage], temperature: float, max_tokens: int, json_mode: bool
    ) -> str:
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "Content-Type": "application/json",
            # Recommended by OpenRouter for attribution / rate-limit tiers.
            "HTTP-Referer": self.settings.frontend_url or "http://localhost:5173",
            "X-Title": "Intervue",
        }

        try:
            async with httpx.AsyncClient(timeout=self.settings.openrouter_timeout_seconds) as client:
                resp = await client.post(
                    f"{self.settings.openrouter_base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
        except httpx.TimeoutException as e:
            raise _RetryableError(f"timeout: {e}") from e
        except httpx.TransportError as e:
            raise _RetryableError(f"transport error: {e}") from e

        if resp.status_code == 429 or resp.status_code >= 500:
            raise _RetryableError(f"status={resp.status_code} body={resp.text[:200]}")
        if resp.status_code >= 400:
            raise LLMProviderError(f"OpenRouter error {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise LLMProviderError(f"Unexpected OpenRouter response shape: {data}") from e
