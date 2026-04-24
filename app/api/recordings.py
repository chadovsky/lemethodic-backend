import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.recording import Recording, Feedback

router = APIRouter(prefix="/api/recordings", tags=["recordings"])

UPLOAD_DIR = "uploads/audio"
os.makedirs(UPLOAD_DIR, exist_ok=True)


class RecordingResponse(BaseModel):
    id: int
    topic: str
    status: str
    audio_duration_sec: Optional[float] = None
    transcript: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


class FeedbackResponse(BaseModel):
    score: Optional[float] = None
    analysis: Optional[dict] = None
    corrections: Optional[str] = None

    class Config:
        from_attributes = True


class RecordingDetailResponse(BaseModel):
    recording: RecordingResponse
    feedback: Optional[FeedbackResponse] = None


@router.post("/upload", status_code=201)
async def upload_recording(
    background_tasks: BackgroundTasks,
    audio: UploadFile = File(...),
    topic: str = Form(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Save audio file locally (S3 in production)
    ext = audio.filename.split(".")[-1] if audio.filename else "webm"
    filename = f"{uuid.uuid4()}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    content = await audio.read()
    with open(filepath, "wb") as f:
        f.write(content)

    rec = Recording(
        user_id=user.id,
        topic=topic,
        audio_url=filepath,
        status="uploaded",
    )
    db.add(rec)
    await db.commit()
    await db.refresh(rec)

    # Trigger async processing pipeline
    background_tasks.add_task(process_recording, rec.id)

    return {"id": rec.id, "status": "uploaded", "message": "Processing started"}


async def process_recording(recording_id: int):
    """Background task: transcribe → analyze → generate feedback."""
    from app.core.database import async_session
    from app.services.transcription import transcribe_audio
    from app.services.analysis import analyze_transcript

    async with async_session() as db:
        result = await db.execute(select(Recording).where(Recording.id == recording_id))
        rec = result.scalar_one_or_none()
        if not rec:
            return

        try:
            # Step 1: Transcribe
            rec.status = "transcribing"
            await db.commit()

            transcript = await transcribe_audio(rec.audio_url)
            rec.transcript = transcript
            rec.status = "analyzing"
            await db.commit()

            # Step 2: Analyze with Les Moules
            analysis_result = await analyze_transcript(transcript, rec.topic)

            feedback = Feedback(
                recording_id=rec.id,
                score=analysis_result.get("score"),
                analysis=analysis_result.get("analysis"),
                corrections=analysis_result.get("corrections"),
                raw_response=analysis_result.get("raw"),
            )
            db.add(feedback)
            rec.status = "complete"
            await db.commit()

        except Exception as e:
            rec.status = "error"
            await db.commit()
            print(f"Error processing recording {recording_id}: {e}")


@router.get("/history")
async def get_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Recording)
        .where(Recording.user_id == user.id)
        .order_by(desc(Recording.created_at))
        .limit(50)
    )
    recordings = result.scalars().all()
    return [
        {
            "id": r.id,
            "topic": r.topic,
            "status": r.status,
            "created_at": str(r.created_at),
        }
        for r in recordings
    ]


@router.get("/{recording_id}")
async def get_recording(
    recording_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Recording).where(Recording.id == recording_id, Recording.user_id == user.id)
    )
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Recording not found")

    feedback_data = None
    if rec.feedback:
        feedback_data = {
            "score": rec.feedback.score,
            "analysis": rec.feedback.analysis,
            "corrections": rec.feedback.corrections,
        }

    return {
        "id": rec.id,
        "topic": rec.topic,
        "status": rec.status,
        "transcript": rec.transcript,
        "created_at": str(rec.created_at),
        "feedback": feedback_data,
    }
