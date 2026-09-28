"""
Sarvam AI implementation of SpeechToTextService / TextToSpeechService.

Sarvam's REST API is used for both speech-to-text and text-to-speech.
Browser-recorded audio (typically WebM/Opus) is converted to WAV before
being sent to Sarvam STT because Sarvam STT does not accept audio/webm.

If Sarvam changes its API contract, this is the main provider file that
needs to change. voice_service.py and everything upstream only depend on
the SpeechToTextService / TextToSpeechService interfaces.
"""

import base64
import subprocess

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.providers.voice.base import (
    SpeechToTextService,
    SynthesisResult,
    TextToSpeechService,
    TranscriptionResult,
    VoiceProviderError,
)

logger = get_logger(__name__)

_TIMEOUT_SECONDS = 20


class SarvamSTTProvider(SpeechToTextService):
    def __init__(self) -> None:
        self.settings = get_settings()

    def _convert_to_wav(
        self,
        audio_bytes: bytes,
        mime_type: str,
    ) -> bytes:
        """
        Convert browser audio such as WebM/Opus into PCM WAV.

        Sarvam STT does not accept audio/webm, so all non-WAV input is
        normalized to mono 16 kHz PCM WAV before being uploaded.
        """

        mime = (mime_type or "").lower().split(";")[0].strip()

        # Already WAV — no conversion required.
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
                "FFmpeg is required to convert browser audio to WAV. "
                "Please install FFmpeg and make sure it is available on PATH."
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
                "FFmpeg returned empty audio after WAV conversion."
            )

        return result.stdout

    async def transcribe(
        self,
        audio_bytes: bytes,
        *,
        mime_type: str,
        language: str,
    ) -> TranscriptionResult:
        if not self.settings.sarvam_api_key:
            raise VoiceProviderError("SARVAM_API_KEY is not set.")

        # Convert browser WebM/Opus audio into WAV before sending to Sarvam.
        wav_bytes = self._convert_to_wav(
            audio_bytes,
            mime_type,
        )

        headers = {
            "api-subscription-key": self.settings.sarvam_api_key,
        }

        # IMPORTANT:
        # We converted the audio to WAV, so the filename and MIME type
        # must also describe the converted WAV file.
        files = {
            "file": (
                "audio.wav",
                wav_bytes,
                "audio/wav",
            )
        }

        data = {
            "language_code": (
                language
                or self.settings.sarvam_stt_language
            ),
            "model": "saaras:v3",
            "mode": "transcribe",
        }

        try:
            async with httpx.AsyncClient(
                timeout=_TIMEOUT_SECONDS
            ) as client:
                resp = await client.post(
                    f"{self.settings.sarvam_base_url}/speech-to-text",
                    headers=headers,
                    data=data,
                    files=files,
                )

        except httpx.HTTPError as exc:
            raise VoiceProviderError(
                f"Sarvam STT request failed: {exc}"
            ) from exc

        if resp.status_code >= 400:
            raise VoiceProviderError(
                f"Sarvam STT error {resp.status_code}: "
                f"{resp.text[:500]}"
            )

        try:
            payload = resp.json()
        except ValueError as exc:
            raise VoiceProviderError(
                f"Sarvam STT returned invalid JSON: "
                f"{resp.text[:500]}"
            ) from exc

        text = (payload.get("transcript") or "").strip()

        if not text:
            raise VoiceProviderError(
                f"Sarvam STT returned no transcript: {payload}"
            )

        return TranscriptionResult(
            text=text,
        )


class SarvamTTSProvider(TextToSpeechService):
    def __init__(self) -> None:
        self.settings = get_settings()

    async def synthesize(
        self,
        text: str,
        *,
        voice: str,
        language: str,
    ) -> SynthesisResult:
        if not self.settings.sarvam_api_key:
            raise VoiceProviderError("SARVAM_API_KEY is not set.")

        headers = {
            "api-subscription-key": self.settings.sarvam_api_key,
            "Content-Type": "application/json",
        }

        body = {
            "inputs": [text],
            "target_language_code": (
                language
                or self.settings.sarvam_stt_language
            ),
            "speaker": (
                voice
                or self.settings.sarvam_tts_voice
            ),
            "model": "bulbul:v3",
        }

        try:
            async with httpx.AsyncClient(
                timeout=_TIMEOUT_SECONDS
            ) as client:
                resp = await client.post(
                    f"{self.settings.sarvam_base_url}/text-to-speech",
                    headers=headers,
                    json=body,
                )

        except httpx.HTTPError as exc:
            raise VoiceProviderError(
                f"Sarvam TTS request failed: {exc}"
            ) from exc

        if resp.status_code >= 400:
            raise VoiceProviderError(
                f"Sarvam TTS error {resp.status_code}: "
                f"{resp.text[:500]}"
            )

        try:
            payload = resp.json()
        except ValueError as exc:
            raise VoiceProviderError(
                f"Sarvam TTS returned invalid JSON: "
                f"{resp.text[:500]}"
            ) from exc

        audios = payload.get("audios", [])

        if not audios:
            raise VoiceProviderError(
                f"Sarvam TTS returned no audio: {payload}"
            )

        try:
            audio_bytes = base64.b64decode(audios[0])
        except Exception as exc:
            raise VoiceProviderError(
                "Sarvam TTS returned invalid base64 audio."
            ) from exc

        return SynthesisResult(
            audio_bytes=audio_bytes,
            mime_type="audio/wav",
        )