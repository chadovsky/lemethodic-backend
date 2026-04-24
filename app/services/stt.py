import asyncio
import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


async def transcribe_audio(audio_path: str) -> dict:
    """
    Send audio to AssemblyAI and return transcript + word-level confidence.
    """
    api_key = settings.ASSEMBLYAI_API_KEY

    if not api_key:
        return {
            "transcript": "[MODE DEMO] Configurez ASSEMBLYAI_API_KEY dans .env",
            "confidence": 0.0,
            "words": [],
            "low_confidence_words": [],
            "total_words": 0,
        }

    with open(audio_path, "rb") as f:
        audio_data = f.read()

    async with httpx.AsyncClient(timeout=120) as client:
        # Step 1: Upload audio
        upload_resp = await client.post(
            "https://api.assemblyai.com/v2/upload",
            headers={
                "authorization": api_key,
                "content-type": "application/octet-stream",
            },
            content=audio_data,
        )
        if upload_resp.status_code != 200:
            print(f"[STT] Upload failed: {upload_resp.status_code} {upload_resp.text}")
            raise Exception(f"Upload failed: {upload_resp.status_code}")

        audio_url = upload_resp.json()["upload_url"]
        print(f"[STT] Upload OK: {audio_url}")

        # Step 2: Request transcription
        transcript_resp = await client.post(
            "https://api.assemblyai.com/v2/transcript",
            headers={
                "authorization": api_key,
                "content-type": "application/json",
            },
            json={
                "audio_url": audio_url,
                "language_code": "fr",
                "speech_models": ["universal-2"],
            },
        )
        if transcript_resp.status_code != 200:
            print(f"[STT] Transcript request failed: {transcript_resp.status_code} {transcript_resp.text}")
            raise Exception(f"Transcription failed: {transcript_resp.status_code}")

        transcript_id = transcript_resp.json()["id"]
        print(f"[STT] Transcript requested: {transcript_id}")

        # Step 3: Poll until complete
        while True:
            poll_resp = await client.get(
                f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
                headers={"authorization": api_key},
            )
            poll_resp.raise_for_status()
            result = poll_resp.json()

            if result["status"] == "completed":
                raw_words = result.get("words", [])
                words = [
                    {
                        "text": w.get("text", ""),
                        "confidence": w.get("confidence", 0),
                        "start": w.get("start", 0),
                        "end": w.get("end", 0),
                    }
                    for w in raw_words
                ]

                # F-002: threshold bumped from 0.65 → 0.75 per ticket.
                # Tuning window: log per-recording stats for the first 5-10
                # real sessions to see whether 0.75 over-flags accented speech.
                CONFIDENCE_THRESHOLD = 0.75
                low_confidence = [
                    {"text": w["text"], "confidence": round(w["confidence"], 2)}
                    for w in words
                    if w["confidence"] < CONFIDENCE_THRESHOLD
                    and len(w["text"]) > 2
                ]

                overall_conf = result.get("confidence", 0.0)
                total = len(words)
                pct = (len(low_confidence) / total * 100) if total else 0.0
                logger.info(
                    f"[F-002 stats] total_words={total} flagged={len(low_confidence)} "
                    f"pct={pct:.1f}% threshold={CONFIDENCE_THRESHOLD}"
                )

                return {
                    "transcript": result.get("text", ""),
                    "confidence": overall_conf,
                    "words": words,
                    "low_confidence_words": low_confidence,
                    "total_words": total,
                }
            elif result["status"] == "error":
                print(f"[STT] Error: {result.get('error')}")
                raise Exception(f"Transcription error: {result.get('error', 'Unknown')}")

            await asyncio.sleep(1.5)
