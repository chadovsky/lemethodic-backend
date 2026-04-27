# Dead code from pre-routers async scaffold. Archived during F-077
# PostgreSQL migration to prevent accidental Alembic Base.metadata
# pollution. 5-minute insurance against accidental import.
import httpx
from app.core.config import get_settings

settings = get_settings()

DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"


async def transcribe_audio(audio_path: str) -> str:
    """Send audio file to Deepgram and return transcript text."""
    with open(audio_path, "rb") as f:
        audio_data = f.read()

    headers = {
        "Authorization": f"Token {settings.deepgram_api_key}",
        "Content-Type": "audio/webm",  # adjust based on actual format
    }
    params = {
        "model": "nova-2",
        "language": "fr",
        "punctuate": "true",
        "paragraphs": "true",
    }

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            DEEPGRAM_URL,
            headers=headers,
            params=params,
            content=audio_data,
        )
        response.raise_for_status()
        data = response.json()

    # Extract transcript from Deepgram response
    channels = data.get("results", {}).get("channels", [])
    if not channels:
        return ""

    alternatives = channels[0].get("alternatives", [])
    if not alternatives:
        return ""

    return alternatives[0].get("transcript", "")
