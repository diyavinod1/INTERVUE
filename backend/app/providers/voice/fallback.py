"""
Fallback voice providers.

These exist purely so the interview never hard-stops if Sarvam is down or
unconfigured.

  - TTS fallback: gTTS (Google Translate TTS)
  - STT fallback: SpeechRecognition using Google's Web Speech recognizer

Both are best-effort. If they fail, voice_service.py can degrade to
text-only interview behavior.
"""

import asyncio
import io
import subprocess

from app.core.logging import get_logger
from app.providers.voice.base import (
    SpeechToTextService,
    SynthesisResult,
    TextToSpeechService,
    TranscriptionResult,
    VoiceProviderError,
)

logger = get_logger(__name__)


class FallbackTTSProvider(TextToSpeechService):
    async def synthesize(
        self,
        text: str,
        *,
        voice: str,
        language: str,
    ) -> SynthesisResult:

        def _generate() -> bytes:
            from gtts import gTTS

            buffer = io.BytesIO()

            # gTTS expects "en", "hi", etc., rather than "en-IN".
            lang = (language or "en").split("-")[0]

            gTTS(
                text=text,
                lang=lang,
            ).write_to_fp(buffer)

            return buffer.getvalue()

        try:
            audio_bytes = await asyncio.to_thread(_generate)

        except Exception as exc:  # noqa: BLE001
            raise VoiceProviderError(
                f"Fallback TTS (gTTS) failed: {exc}"
            ) from exc

        return SynthesisResult(
            audio_bytes=audio_bytes,
            mime_type="audio/mpeg",
        )


class FallbackSTTProvider(SpeechToTextService):
    def _convert_to_wav(
        self,
        audio_bytes: bytes,
        mime_type: str,
    ) -> bytes:
        """
        Convert browser-recorded audio into PCM WAV.

        MediaRecorder commonly produces:
            audio/webm;codecs=opus

        FFmpeg converts it to:
            mono / 16 kHz / PCM 16-bit WAV
        """

        mime = (mime_type or "").lower().split(";")[0].strip()

        # Already WAV.
        if mime in {
            "audio/wav",
            "audio/x-wav",
            "audio/wave",
        }:
            return audio_bytes

        try:
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-i",
                    "pipe:0",
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-acodec",
                    "pcm_s16le",
                    "-f",
                    "wav",
                    "pipe:1",
                ],
                input=audio_bytes,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )

        except FileNotFoundError as exc:
            raise VoiceProviderError(
                "FFmpeg is not installed or is not available on PATH."
            ) from exc

        except subprocess.CalledProcessError as exc:
            detail = exc.stderr.decode(
                "utf-8",
                errors="replace",
            ).strip()

            raise VoiceProviderError(
                f"Audio conversion to WAV failed: {detail[:500]}"
            ) from exc

        if not result.stdout:
            raise VoiceProviderError(
                "FFmpeg returned empty audio after conversion."
            )

        return result.stdout

    async def transcribe(
        self,
        audio_bytes: bytes,
        *,
        mime_type: str,
        language: str,
    ) -> TranscriptionResult:

        def _recognize() -> str:
            import speech_recognition as sr

            normalized_audio = self._convert_to_wav(
                audio_bytes,
                mime_type,
            )

            recognizer = sr.Recognizer()

            with sr.AudioFile(
                io.BytesIO(normalized_audio)
            ) as source:
                audio = recognizer.record(source)

            return recognizer.recognize_google(
                audio,
                language=language or "en-IN",
            )

        try:
            text = await asyncio.to_thread(_recognize)

        except VoiceProviderError:
            raise

        except Exception as exc:  # noqa: BLE001
            raise VoiceProviderError(
                f"Fallback STT (SpeechRecognition) failed: {exc}"
            ) from exc

        text = (text or "").strip()

        if not text:
            raise VoiceProviderError(
                "Fallback STT returned an empty transcript."
            )

        return TranscriptionResult(
            text=text,
        )