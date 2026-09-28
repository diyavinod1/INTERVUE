"""
VoiceService: business logic depends on this, never on Sarvam directly
(PRD Sec. 12). Tries Sarvam first; if it fails (missing key, network error,
API error) and ENABLE_VOICE_FALLBACK is true, tries the fallback provider;
if that also fails, raises so the API layer can tell the frontend to fall
back to text mode rather than the interview silently breaking (PRD Sec. 39).
"""
import base64
import re

from app.core.config import get_settings
from app.core.logging import get_logger
from app.providers.voice.base import SynthesisResult, TranscriptionResult, VoiceProviderError
from app.providers.voice.fallback import FallbackSTTProvider, FallbackTTSProvider
from app.providers.voice.sarvam import SarvamSTTProvider, SarvamTTSProvider

logger = get_logger(__name__)

_FILLER_WORDS = {"um", "uh", "like", "you know", "sort of", "kind of", "basically", "actually", "literally"}


class VoiceUnavailableError(Exception):
    """Raised only when BOTH primary and fallback providers fail."""


class VoiceService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._sarvam_stt = SarvamSTTProvider()
        self._sarvam_tts = SarvamTTSProvider()
        self._fallback_stt = FallbackSTTProvider()
        self._fallback_tts = FallbackTTSProvider()

    async def transcribe(self, audio_bytes: bytes, *, mime_type: str) -> tuple[TranscriptionResult, str]:
        try:
            result = await self._sarvam_stt.transcribe(
                audio_bytes, mime_type=mime_type, language=self.settings.sarvam_stt_language
            )
            return result, "sarvam"
        except VoiceProviderError as e:
            logger.warning("sarvam_stt_failed error=%s", e)
            if not self.settings.enable_voice_fallback:
                raise VoiceUnavailableError(str(e)) from e
            try:
                result = await self._fallback_stt.transcribe(
                    audio_bytes, mime_type=mime_type, language=self.settings.sarvam_stt_language
                )
                return result, "fallback"
            except VoiceProviderError as fallback_error:
                logger.error("fallback_stt_failed error=%s", fallback_error)
                raise VoiceUnavailableError(
                    f"Both Sarvam and fallback speech-to-text failed: {fallback_error}"
                ) from fallback_error

    async def synthesize(self, text: str) -> tuple[SynthesisResult, str]:
        try:
            result = await self._sarvam_tts.synthesize(
                text, voice=self.settings.sarvam_tts_voice, language=self.settings.sarvam_stt_language
            )
            return result, "sarvam"
        except VoiceProviderError as e:
            logger.warning("sarvam_tts_failed error=%s", e)
            if not self.settings.enable_voice_fallback:
                raise VoiceUnavailableError(str(e)) from e
            try:
                result = await self._fallback_tts.synthesize(
                    text, voice=self.settings.sarvam_tts_voice, language=self.settings.sarvam_stt_language
                )
                return result, "fallback"
            except VoiceProviderError as fallback_error:
                logger.error("fallback_tts_failed error=%s", fallback_error)
                raise VoiceUnavailableError(
                    f"Both Sarvam and fallback text-to-speech failed: {fallback_error}"
                ) from fallback_error


def audio_to_base64(audio_bytes: bytes) -> str:
    return base64.b64encode(audio_bytes).decode("utf-8")


def count_filler_words(text: str) -> int:
    """A measurable voice signal (PRD Sec. 36) - purely a word-frequency
    count, never used to infer confidence, honesty, or any psychological
    state."""
    lowered = text.lower()
    count = 0
    for filler in _FILLER_WORDS:
        count += len(re.findall(r"\b" + re.escape(filler) + r"\b", lowered))
    return count
