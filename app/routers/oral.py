from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import User, TestTopic
from app.services.auth import get_current_user
from app.services.argument_assistant import generate_structure

router = APIRouter(prefix="/api/oral", tags=["oral"])


class GenerateStructureRequest(BaseModel):
    topic_id: int
    student_arguments: str
    target_level: str = "B2"


@router.post("/generate-structure")
async def generate_argument_structure(
    req: GenerateStructureRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate a structured argument paragraph from student's rough ideas."""
    # Validate arguments are not empty
    args = req.student_arguments.strip()
    if not args:
        raise HTTPException(400, "Arguments cannot be empty")

    # Get topic text
    topic_text = ""
    if req.topic_id:
        topic = db.query(TestTopic).filter(TestTopic.id == req.topic_id).first()
        if topic:
            topic_text = topic.title

    result = await generate_structure(
        topic=topic_text,
        student_arguments=args,
        target_level=req.target_level,
    )

    if "error" in result and not result.get("structure"):
        raise HTTPException(500, f"Structure generation failed: {result['error']}")

    return result
