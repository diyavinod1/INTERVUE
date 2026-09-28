"""
Provider-agnostic voice interfaces. voice_service.py depends only on these,
so Sarvam can be swapped or supplemented by a fallback provider without
touching business logic anywhere else in the app.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class TranscriptionResult:
    text: str
    duration_seconds: float | None = None


@dataclass
class SynthesisResult:
    audio_bytes: bytes
    mime_type: str


class SpeechToTextService(ABC):
    @abstractmethod
    async def transcribe(self, audio_bytes: bytes, *, mime_type: str, language: str) -> TranscriptionResult:
        raise NotImplementedError


class TextToSpeechService(ABC):
    @abstractmethod
    async def synthesize(self, text: str, *, voice: str, language: str) -> SynthesisResult:
        raise NotImplementedError


class VoiceProviderError(Exception):
    pass
