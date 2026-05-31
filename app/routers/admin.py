import random as _random
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func
from app.database import get_db
from app.models.models import User, Recording, Feedback, TestTopic
from app.services.auth import require_admin, get_current_user

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ═══════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════

@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    total_users = db.query(func.count(User.id)).scalar()
    total_recordings = db.query(func.count(Recording.id)).scalar()
    avg_score = db.query(func.avg(Feedback.overall_score)).scalar() or 0

    recent = (
        db.query(Recording, User)
        .options(selectinload(Recording.feedback))
        .join(User, Recording.user_id == User.id)
        .order_by(Recording.created_at.desc())
        .limit(20)
        .all()
    )
    recent_list = []
    for r, u in recent:
        entry = {
            "id": r.id,
            "user_email": u.email,
            "status": r.status,
            "score": r.feedback.overall_score if r.feedback else None,
            "target_level": getattr(r, "target_level", None),
            "created_at": r.created_at.isoformat() if r.created_at else "",
        }
        recent_list.append(entry)

    return {
        "total_users": total_users,
        "total_recordings": total_recordings,
        "avg_score": round(avg_score, 1),
        "recent_recordings": recent_list,
    }


# ═══════════════════════════════════════
# USERS
# ═══════════════════════════════════════

@router.get("/users")
def list_users(
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    # Single aggregate subquery: recording count + avg score per user.
    agg = (
        db.query(
            Recording.user_id,
            func.count(Recording.id).label("rec_count"),
            func.avg(Feedback.overall_score).label("avg_score"),
        )
        .outerjoin(Feedback, Feedback.recording_id == Recording.id)
        .group_by(Recording.user_id)
        .subquery()
    )
    rows = (
        db.query(User, agg.c.rec_count, agg.c.avg_score)
        .outerjoin(agg, agg.c.user_id == User.id)
        .order_by(User.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "is_admin": u.is_admin,
            "recordings_count": rec_count or 0,
            "avg_score": round(avg_score, 1) if avg_score else None,
            "created_at": u.created_at.isoformat() if u.created_at else "",
        }
        for u, rec_count, avg_score in rows
    ]


# ═══════════════════════════════════════
# THEMES
# ═══════════════════════════════════════

@router.get("/themes")
def list_themes(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Returns list of themes with topic counts."""
    rows = (
        db.query(TestTopic.theme, func.count(TestTopic.id))
        .filter(TestTopic.is_active == True)
        .group_by(TestTopic.theme)
        .order_by(TestTopic.theme)
        .all()
    )
    return [{"theme": theme, "count": count} for theme, count in rows if theme]


# ═══════════════════════════════════════
# TOPICS
# ═══════════════════════════════════════

@router.get("/topics")
def list_topics(
    theme: str = Query(None, description="Filter by theme"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """List topics, optionally filtered by theme."""
    q = db.query(TestTopic).filter(TestTopic.is_active == True)
    if theme:
        q = q.filter(TestTopic.theme == theme)
    q = q.order_by(TestTopic.title)
    topics = q.all()
    return [
        {
            "id": t.id,
            "title": t.title,
            "theme": t.theme,
            "sous_theme": getattr(t, "sous_theme", None),
            "description": t.description if hasattr(t, "description") else "",
        }
        for t in topics
    ]


@router.post("/topics")
def create_topic(
    title: str,
    theme: str = "Société",
    sous_theme: str = "",
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Create a new topic with theme and optional sous_theme."""
    topic = TestTopic(title=title, theme=theme)
    if sous_theme:
        topic.sous_theme = sous_theme
    # Set defaults for legacy fields if they exist on the model
    if hasattr(topic, "level"):
        topic.level = "B2"
    if hasattr(topic, "is_active"):
        topic.is_active = True
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return {"id": topic.id, "title": topic.title, "theme": topic.theme}


@router.delete("/topics/{topic_id}")
def delete_topic(
    topic_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Soft-delete a topic (set is_active=False). Falls back to hard delete."""
    topic = db.query(TestTopic).filter(TestTopic.id == topic_id).first()
    if not topic:
        raise HTTPException(404, "Topic not found")
    if hasattr(topic, "is_active"):
        topic.is_active = False
        db.commit()
    else:
        db.delete(topic)
        db.commit()
    return {"ok": True, "id": topic_id}


# ═══════════════════════════════════════
# RANDOM TOPIC
# ═══════════════════════════════════════

@router.get("/random-topic")
def random_topic(
    theme: str = Query(None, description="Filter by theme"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Return a random active topic, optionally filtered by theme."""
    q = db.query(TestTopic).filter(TestTopic.is_active == True)
    if theme:
        q = q.filter(TestTopic.theme == theme)
    topics = q.all()
    if not topics:
        raise HTTPException(404, "No topics found")
    t = _random.choice(topics)
    return {
        "id": t.id,
        "title": t.title,
        "theme": t.theme,
        "sous_theme": getattr(t, "sous_theme", None),
    }
