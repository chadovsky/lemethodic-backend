"""F-050 — Audio upload + STT for the Tâche 2 push-to-talk flow.

One combined endpoint (``POST /api/audio/upload``) saves the blob and
runs STT in a single round-trip. The F-050 spec describes upload and
STT as two conceptually separate calls, but in practice the client
always wants both results together — running them as one call saves a
full audio-body upload (typically several hundred KB) and simplifies
client-side state. The returned payload carries both an ``audio_url``
(to later pass to ``/api/conversations/{id}/turn`` alongside the
confirmed transcript) and the STT result shape ``transcribe_audio``
already produces.
"""
from __future__ import annotations

import json
import logging
import os

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.models import User
from app.services import storage
from app.services.auth import get_current_user
from app.services.fluency import compute_fluency
from app.services.stt import transcribe_audio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/audio", tags=["audio"])

# F-078: writes go through app.services.storage; no module-level
# os.makedirs needed.


@router.post("/upload")
async def upload_and_transcribe(
    audio: UploadFile = File(...),
    duration_seconds: float = Form(default=0),
    # Optional owner stamping for the stored file — not used for auth
    # (FastAPI dependency injection already did that), just for any
    # future cleanup jobs.
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Store the uploaded audio and return ``{audio_url, transcript,
    low_confidence_words, confidence, words, total_words, fluency}``.

    The client uses the returned ``audio_url`` + ``transcript`` to
    build a Tâche 2 /turn request after the candidate confirms the
    transcription.
    """
    if not audio or not audio.filename:
        raise HTTPException(400, "Missing audio upload")

    ext = (audio.filename or "clip.webm").split(".")[-1].lower()
    # Guardrail: refuse ludicrously named extensions. The STT service
    # sniffs the actual MIME type, so the extension is only used for
    # file naming.
    if len(ext) > 10 or not ext.isalnum():
        ext = "webm"

    storage_key = storage.user_upload_key(user.id, ext)  # P-103: per-user prefix
    content = await audio.read()
    if not content:
        raise HTTPException(400, "Empty audio body")
    # F-075a Layer B — defensive size cap. Layer A middleware rejects
    # via Content-Length before the body is buffered; this catches
    # spoofed / chunked / missing-header cases.
    cap = settings.MAX_AUDIO_UPLOAD_BYTES
    if len(content) > cap:
        cap_mb = cap // (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"Audio file exceeds maximum allowed size of {cap_mb} MB",
        )
    storage.write_bytes(storage_key, content, content_type=(audio.content_type or "application/octet-stream"))

    try:
        stt_result = await transcribe_audio(content)
    except Exception as exc:
        logger.exception("F-050 STT failed for user=%s key=%s", user.id, storage_key)
        raise HTTPException(500, f"Transcription failed: {exc}")

    fluency_data = compute_fluency(
        stt_result, recording_duration_sec=duration_seconds or None
    )
    fluency_payload: str = ""
    if fluency_data is not None:
        # Mirror /api/conversations/{id}/turn behaviour: stash the
        # low-confidence word list inside the fluency payload so the
        # client only has to round-trip one blob back to us on /turn.
        fluency_data["low_confidence_words"] = stt_result.get("low_confidence_words", [])
        fluency_payload = json.dumps(fluency_data, ensure_ascii=False)

    return {
        # F-078: this is a storage KEY (e.g. uploads/<uuid>.webm), not
        # a filesystem path. The frontend treats it as opaque and
        # round-trips it back on /api/conversations/{id}/turn where it
        # lands in ConversationTurn.audio_url.
        "audio_url": storage_key,
        "transcript": stt_result.get("transcript", "") or "",
        "confidence": stt_result.get("confidence", 0.0),
        "words": stt_result.get("words", []),
        "low_confidence_words": stt_result.get("low_confidence_words", []),
        "total_words": stt_result.get("total_words", 0),
        # Pass-through blob — the client POSTs this back on /turn so we
        # don't have to recompute fluency server-side.
        "fluency": fluency_payload,
    }
