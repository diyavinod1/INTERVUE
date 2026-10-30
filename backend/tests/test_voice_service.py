import pytest

from app.providers.voice.base import SynthesisResult, TranscriptionResult, VoiceProviderError
from app.providers.voice.sarvam import SarvamTTSProvider
from app.services.voice_service import (
    VoiceService,
    VoiceUnavailableError,
    count_filler_words,
    prepare_text_for_speech,
)


def test_prepare_text_for_speech_markdown_and_code():
    raw = (
        '```python\nprint("hello")\n```\n'
        'You mentioned using **PostgreSQL** and `Redis` for caching in your CI/CD pipeline. '
        "How do you handle O(n) lookups vs O(1) in C++ and Node.js?"
    )
    cleaned = prepare_text_for_speech(raw)
    assert "**" not in cleaned
    assert "`" not in cleaned
    assert "```" not in cleaned
    assert "Postgres" in cleaned
    assert "Redis" in cleaned
    assert "CI CD" in cleaned
    assert "O of n" in cleaned
    assert "O of 1" in cleaned
    assert "versus" in cleaned
    assert "C plus plus" in cleaned
    assert "Node JS" in cleaned


def test_prepare_text_for_speech_strips_quotes_and_headings():
    raw = '"### Technical Design\n- We deployed to k8s w/o downtime."'
    cleaned = prepare_text_for_speech(raw)
    assert not cleaned.startswith('"')
    assert not cleaned.endswith('"')
    assert "###" not in cleaned
    assert "Kubernetes" in cleaned
    assert "without" in cleaned


async def test_sarvam_tts_provider_payload(monkeypatch):
    provider = SarvamTTSProvider()
    provider.settings.sarvam_api_key = "test-sarvam-key"
    provider.settings.sarvam_tts_voice = "dev_en_conversational"
    provider.settings.sarvam_tts_model = "bulbul:v4-flash"

    captured_request = {}

    class MockResponse:
        status_code = 200

        def json(self):
            # Base64 encoded fake WAV header
            import base64
            fake_wav = base64.b64encode(b"RIFF....WAVEfmt ").decode("utf-8")
            return {"request_id": "req-123", "audios": [fake_wav]}

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, headers=None, json=None, **kwargs):
            captured_request["url"] = url
            captured_request["headers"] = headers
            captured_request["json"] = json
            return MockResponse()

    monkeypatch.setattr("httpx.AsyncClient", MockAsyncClient)

    result = await provider.synthesize("Hello candidate", voice="", language="")
    assert result.mime_type == "audio/wav"
    assert captured_request["json"]["model"] == "bulbul:v4-flash"
    assert captured_request["json"]["speaker"] == "dev_en_conversational"
    assert captured_request["json"]["target_language_code"] == "en-IN"
    assert captured_request["json"]["enable_preprocessing"] is True
    assert captured_request["json"]["inputs"] == ["Hello candidate"]


async def test_voice_service_synthesize_prepares_text(monkeypatch):
    service = VoiceService()
    captured_text = []

    async def fake_synthesize(self, text, *, voice, language):
        captured_text.append(text)
        return SynthesisResult(audio_bytes=b"wavbytes", mime_type="audio/wav")

    monkeypatch.setattr(type(service._sarvam_tts), "synthesize", fake_synthesize)

    res, provider = await service.synthesize('**Great!** Let\'s discuss `PostgreSQL` and C++.')
    assert provider == "sarvam"
    assert len(captured_text) == 1
    assert captured_text[0] == "Great! Let's discuss Postgres and C plus plus."


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
