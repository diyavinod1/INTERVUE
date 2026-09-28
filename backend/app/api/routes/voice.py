"""
Voice routes (PRD Sec. 11-12). Both routes return a clear error rather than
a raw 500 if voice is fully unavailable, so the frontend can show "switch
to text" instead of a broken UI (PRD Sec. 35, 39).
"""
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.logging import get_logger
from app.schemas.voice import SynthesizeRequest, SynthesizeResponse, TranscribeResponse
from app.services.voice_service import VoiceService, VoiceUnavailableError, audio_to_base64

router = APIRouter(prefix="/api/voice", tags=["voice"])
logger = get_logger(__name__)
_voice_service = VoiceService()


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(audio: UploadFile = File(...)):
    raw_bytes = await audio.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="No audio data received.")

    try:
        result, provider_used = await _voice_service.transcribe(raw_bytes, mime_type=audio.content_type or "audio/wav")
    except VoiceUnavailableError as e:
        logger.error("voice_transcribe_unavailable error=%s", e)
        raise HTTPException(
            status_code=503,
            detail="Voice transcription is temporarily unavailable. Please switch to text mode or try again.",
        ) from e

    return TranscribeResponse(text=result.text, provider_used=provider_used, duration_seconds=result.duration_seconds)


@router.post("/synthesize", response_model=SynthesizeResponse)
async def synthesize(body: SynthesizeRequest):
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Text is required for synthesis.")

    try:
        result, provider_used = await _voice_service.synthesize(body.text)
    except VoiceUnavailableError as e:
        logger.error("voice_synthesize_unavailable error=%s", e)
        raise HTTPException(
            status_code=503,
            detail="Voice synthesis is temporarily unavailable. The question is still available as text.",
        ) from e

    return SynthesizeResponse(
        audio_base64=audio_to_base64(result.audio_bytes), mime_type=result.mime_type, provider_used=provider_used
    )
