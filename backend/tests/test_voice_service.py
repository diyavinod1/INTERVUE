import pytest

from app.providers.voice.base import SynthesisResult, TranscriptionResult, VoiceProviderError
from app.services.voice_service import VoiceService, VoiceUnavailableError, count_filler_words


async def test_uses_sarvam_when_it_succeeds(monkeypatch):
    service = VoiceService()

    async def fake_sarvam_transcribe(self, audio_bytes, *, mime_type, language):
        return TranscriptionResult(text="hello from sarvam")

    monkeypatch.setattr(type(service._sarvam_stt), "transcribe", fake_sarvam_transcribe)

    result, provider = await service.transcribe(b"fake-audio-bytes", mime_type="audio/wav")
    assert provider == "sarvam"
    assert result.text == "hello from sarvam"


async def test_falls_back_when_sarvam_fails(monkeypatch):
    service = VoiceService()
    service.settings.enable_voice_fallback = True

    async def sarvam_fails(self, audio_bytes, *, mime_type, language):
        raise VoiceProviderError("sarvam down")

    async def fallback_succeeds(self, audio_bytes, *, mime_type, language):
        return TranscriptionResult(text="hello from fallback")

    monkeypatch.setattr(type(service._sarvam_stt), "transcribe", sarvam_fails)
    monkeypatch.setattr(type(service._fallback_stt), "transcribe", fallback_succeeds)

    result, provider = await service.transcribe(b"fake-audio-bytes", mime_type="audio/wav")
    assert provider == "fallback"
    assert result.text == "hello from fallback"


async def test_raises_voice_unavailable_when_both_fail(monkeypatch):
    service = VoiceService()
    service.settings.enable_voice_fallback = True

    async def always_fail(self, audio_bytes, *, mime_type, language):
        raise VoiceProviderError("down")

    monkeypatch.setattr(type(service._sarvam_stt), "transcribe", always_fail)
    monkeypatch.setattr(type(service._fallback_stt), "transcribe", always_fail)

    with pytest.raises(VoiceUnavailableError):
        await service.transcribe(b"fake-audio-bytes", mime_type="audio/wav")


async def test_tts_falls_back_on_sarvam_failure(monkeypatch):
    service = VoiceService()
    service.settings.enable_voice_fallback = True

    async def sarvam_fails(self, text, *, voice, language):
        raise VoiceProviderError("sarvam tts down")

    async def fallback_succeeds(self, text, *, voice, language):
        return SynthesisResult(audio_bytes=b"mp3bytes", mime_type="audio/mpeg")

    monkeypatch.setattr(type(service._sarvam_tts), "synthesize", sarvam_fails)
    monkeypatch.setattr(type(service._fallback_tts), "synthesize", fallback_succeeds)

    result, provider = await service.synthesize("hello world")
    assert provider == "fallback"
    assert result.mime_type == "audio/mpeg"


def test_filler_word_counting_is_purely_lexical():
    text = "Um, so like, I think, you know, it was basically fine."
    count = count_filler_words(text)
    assert count >= 3  # um, like, you know, basically all present
