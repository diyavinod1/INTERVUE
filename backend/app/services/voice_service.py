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


def prepare_text_for_speech(text: str) -> str:
    """
    Prepare conversational text for TTS synthesis.

    Cleans markdown formatting, code fences, inline syntax, and expands common
    technical acronyms/symbols so speech sounds natural, human, and articulate
    without reading syntax or punctuation literally.
    """
    if not text:
        return ""

    cleaned = text.strip()

    # Strip surrounding quotation marks if LLM output was wrapped in quotes
    if (cleaned.startswith('"') and cleaned.endswith('"')) or (
        cleaned.startswith("“") and cleaned.endswith("”")
    ):
        cleaned = cleaned[1:-1].strip()

    # Remove markdown code blocks (```python ... ```)
    cleaned = re.sub(r"```[\w-]*\n([\s\S]*?)\n```", r"\1", cleaned)
    cleaned = re.sub(r"```[\w-]*", "", cleaned)
    cleaned = cleaned.replace("```", "")

    # Remove inline code backticks `code` -> code
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)

    # Remove markdown links [anchor text](url) -> anchor text
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)

    # Remove bare URLs
    cleaned = re.sub(r"https?://\S+", "", cleaned)

    # Remove markdown headings (# Heading, ## Heading)
    cleaned = re.sub(r"^#{1,6}\s+", "", cleaned, flags=re.MULTILINE)

    # Remove markdown bullet points (- Item, * Item, + Item, 1. Item)
    cleaned = re.sub(r"^[\s]*[-*+]\s+", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^[\s]*\d+\.\s+", "", cleaned, flags=re.MULTILINE)

    # Remove markdown bold and italic markers: **bold**, *italic*, __bold__, _italic_
    cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"\*([^*]+)\*", r"\1", cleaned)
    cleaned = re.sub(r"__([^_]+)__", r"\1", cleaned)
    cleaned = re.sub(r"(?<!\w)_([^_]+)_(?!\w)", r"\1", cleaned)

    # Remove blockquotes (> quote)
    cleaned = re.sub(r"^>\s*", "", cleaned, flags=re.MULTILINE)

    # Expand common technical symbols and abbreviations for natural speech flow
    replacements = [
        (r"\bC\+\+(?!\w)", "C plus plus"),
        (r"\bC#(?!\w)", "C sharp"),
        (r"\.NET\b", "dot NET"),
        (r"\.net\b", "dot net"),
        (r"\bNode\.js\b", "Node JS"),
        (r"\bnode\.js\b", "Node JS"),
        (r"\bVue\.js\b", "Vue JS"),
        (r"\bNext\.js\b", "Next JS"),
        (r"\bNest\.js\b", "Nest JS"),
        (r"\bCI/CD\b", "CI CD"),
        (r"\bI/O\b", "I O"),
        (r"\be\.g\.,?\b", "for example"),
        (r"\bi\.e\.,?\b", "that is"),
        (r"\betc\.\b", "etcetera"),
        (r"\bvs\.?\b", "versus"),
        (r"\bw/o\b", "without"),
        (r"\bw/\b", "with"),
        (r"\bPostgreSQL\b", "Postgres"),
        (r"\bpostgres\b", "Postgres"),
        (r"\bK8s\b|\bk8s\b", "Kubernetes"),
        (r"\bO\(1\)", "O of 1"),
        (r"\bO\(n\)", "O of n"),
        (r"\bO\(n\s+log\s+n\)", "O of n log n"),
        (r"\bO\(n\^2\)", "O of n squared"),
        (r"&", " and "),
        (r"(\w+)/(\w+)", r"\1 or \2"),
    ]

    for pattern, repl in replacements:
        cleaned = re.sub(pattern, repl, cleaned)

    # Normalize whitespace (replace tabs, newlines, multiple spaces with single space)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Clean up double punctuation if any was produced
    cleaned = re.sub(r"\.+", ".", cleaned)
    cleaned = re.sub(r"\?+", "?", cleaned)
    cleaned = re.sub(r"!+", "!", cleaned)
    cleaned = re.sub(r",+", ",", cleaned)

    return cleaned


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
            logger.warning("sarvam_stt_failed error=%s -- switching to fallback STT", e)
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
        prepared_text = prepare_text_for_speech(text)
        try:
            result = await self._sarvam_tts.synthesize(
                prepared_text, voice=self.settings.sarvam_tts_voice, language=self.settings.sarvam_stt_language
            )
            return result, "sarvam"
        except VoiceProviderError as e:
            logger.warning("sarvam_tts_failed error=%s -- switching to fallback TTS (gTTS)", e)
            if not self.settings.enable_voice_fallback:
                raise VoiceUnavailableError(str(e)) from e
            try:
                result = await self._fallback_tts.synthesize(
                    prepared_text, voice=self.settings.sarvam_tts_voice, language=self.settings.sarvam_stt_language
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
