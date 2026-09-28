from pydantic import BaseModel


class TranscribeResponse(BaseModel):
    text: str
    provider_used: str  # "sarvam" | "fallback"
    duration_seconds: float | None = None


class SynthesizeRequest(BaseModel):
    text: str


class SynthesizeResponse(BaseModel):
    audio_base64: str
    mime_type: str
    provider_used: str  # "sarvam" | "fallback"
