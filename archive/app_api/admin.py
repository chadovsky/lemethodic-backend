# Dead code from pre-routers async scaffold. Archived during F-077
# PostgreSQL migration to prevent accidental Alembic Base.metadata
# pollution. 5-minute insurance against accidental import.
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.recording import Recording, Feedback

router = APIRouter(prefix="/api/admin", tags=["admin"])


def require_admin(user: User = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.get("/dashboard")
async def dashboard(
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    total_users = await db.scalar(select(func.count(User.id)))
    total_recordings = await db.scalar(select(func.count(Recording.id)))
    completed = await db.scalar(
        select(func.count(Recording.id)).where(Recording.status == "complete")
    )
    avg_score = await db.scalar(select(func.avg(Feedback.score)))

    return {
        "total_users": total_users,
        "total_recordings": total_recordings,
        "completed_recordings": completed,
        "average_score": round(avg_score, 1) if avg_score else None,
    }


@router.get("/students")
async def list_students(
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(
            User.id, User.email, User.full_name, User.created_at,
            func.count(Recording.id).label("recording_count"),
        )
        .outerjoin(Recording)
        .group_by(User.id)
        .order_by(desc(User.created_at))
    )
    rows = result.all()
    return [
        {
            "id": r.id,
            "email": r.email,
            "full_name": r.full_name,
            "created_at": str(r.created_at),
            "recording_count": r.recording_count,
        }
        for r in rows
    ]


@router.get("/recordings")
async def all_recordings(
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Recording, User.full_name, User.email)
        .join(User)
        .order_by(desc(Recording.created_at))
        .limit(100)
    )
    rows = result.all()
    return [
        {
            "id": rec.id,
            "student": name,
            "email": email,
            "topic": rec.topic,
            "status": rec.status,
            "created_at": str(rec.created_at),
        }
        for rec, name, email in rows
    ]
