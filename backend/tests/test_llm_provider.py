import pytest

from app.core.config import get_settings
from app.providers.llm.base import LLMMessage
from app.providers.llm.openrouter import LLMProviderError, OpenRouterProvider

get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _set_api_key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_MAX_RETRIES", "1")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_falls_back_to_secondary_model_when_primary_fails(monkeypatch):
    provider = OpenRouterProvider()
    calls = []

    async def fake_call_once(self, model, messages, temperature, max_tokens, json_mode):
        calls.append(model)
        if model == provider.settings.openrouter_model:
            raise Exception("primary model down")
        return "fallback response"

    monkeypatch.setattr(OpenRouterProvider, "_call_once", fake_call_once)

    response = await provider.complete([LLMMessage(role="user", content="hi")])
    assert response.used_fallback is True
    assert response.text == "fallback response"
    assert provider.settings.openrouter_fallback_model in calls


@pytest.mark.asyncio
async def test_raises_when_both_primary_and_fallback_fail(monkeypatch):
    provider = OpenRouterProvider()

    async def always_fail(self, model, messages, temperature, max_tokens, json_mode):
        raise Exception(f"{model} is down")

    monkeypatch.setattr(OpenRouterProvider, "_call_once", always_fail)

    with pytest.raises(LLMProviderError):
        await provider.complete([LLMMessage(role="user", content="hi")])


@pytest.mark.asyncio
async def test_missing_api_key_raises_clear_error(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    get_settings.cache_clear()
    provider = OpenRouterProvider()
    with pytest.raises(LLMProviderError, match="OPENROUTER_API_KEY"):
        await provider.complete([LLMMessage(role="user", content="hi")])
    get_settings.cache_clear()
