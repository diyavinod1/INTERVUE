"""
Provider-agnostic LLM interface.

The rest of the application (agents, services) depends on this interface,
never on OpenRouter directly. That's what makes "switch models / switch
providers via config" actually true rather than aspirational: to add a new
provider you implement this ABC and wire it up in llm_service.py - nothing
in agents/ or services/ changes.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    text: str
    model_used: str
    used_fallback: bool = False


class LLMProvider(ABC):
    @abstractmethod
    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int = 600,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Return a completion for the given chat messages."""
        raise NotImplementedError
