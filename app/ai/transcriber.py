import logging
from app.config.settings import settings

logger = logging.getLogger(__name__)

async def transcribe_audio(audio_bytes: bytes, filename: str) -> str:
    """
    Transcribe audio using Groq's Whisper endpoint.

    Returns the transcribed text. Raises on API or network failure.
    """
    if not settings.evaluator.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    response = await settings.evaluator.client.audio.transcriptions.create(
        model=settings.app.GROQ_WHISPER_MODEL,
        file=(filename, audio_bytes),
    )
    return response.text
