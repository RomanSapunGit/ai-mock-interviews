import io
from typing import AsyncIterator

import edge_tts

# A natural-sounding English interviewer voice.
DEFAULT_VOICE = "en-US-AriaNeural"


async def speak(text: str, voice: str = DEFAULT_VOICE) -> bytes:
    """
    Convert text to speech using Microsoft Edge TTS (free, no API key).
    Returns raw MP3 bytes.
    """
    communicate = edge_tts.Communicate(text, voice)
    buf = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    return buf.getvalue()


async def speak_stream(text: str, voice: str = DEFAULT_VOICE) -> AsyncIterator[bytes]:
    """
    Yield raw MP3 audio chunks as they arrive from Edge TTS.
    Use this for low-latency streaming (e.g. over WebSocket).
    """
    communicate = edge_tts.Communicate(text, voice)
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            yield chunk["data"]
