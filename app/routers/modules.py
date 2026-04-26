"""F-080a — Remediation module CRUD endpoints.

Public-read endpoints for the authored module library. No auth gate in
V1 (modules are product-educational content, not per-user data). Users
don't typically call these directly — the diagnostic page (F-080c) and
Raccourci tab (F-080d) consume them.

Endpoints:
- GET /api/modules              → all active modules (optionally filtered by category)
- GET /api/modules/{id}         → single module, active or not

Mutation endpoints are deferred — authoring pipeline is JSON + seed
script (F-080a), not an admin UI. F-080.1 would add those if/when the
authoring UI ships.
"""
from __future__ import annotations

import datetime as _dt
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import (
    Recording,
    RemediationModule as RemediationModuleORM,
    SessionDetectedModule,
    User,
)
from app.schemas.modules import ModuleCategory, RemediationModule as RemediationModuleSchema
from app.services.auth import get_current_user_optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/modules", tags=["modules"])


def _hydrate(row: RemediationModuleORM) -> RemediationModuleSchema:
    """Parse JSON-blob columns back into structured pydantic shape. The
    seeder is the only writer today, and it goes through pydantic
    validation before persistence, so malformed JSON here would indicate
    a manual INSERT bypassing the pipeline — log and bail loudly rather
    than return a half-populated shape.
    """
    try:
        detection_criteria = json.loads(row.detection_criteria or "{}")
        examples = json.loads(row.examples or "[]")
        content_refs = json.loads(row.content_refs or "[]")
        drill_ids = json.loads(row.drill_ids or "[]")
        prerequisite_module_ids = json.loads(row.prerequisite_module_ids or "[]")
    except json.JSONDecodeError as exc:
        logger.error(
            "Module %s has malformed JSON in a blob column: %s", row.id, exc
        )
        raise HTTPException(
            500, f"Module {row.id} stored with malformed JSON — reseed to fix."
        )

    # Defer structural validation to the schema — if the stored blob has
    # drifted from the current schema (e.g. a field was renamed), the
    # ValidationError surfaces the exact issue.
    return RemediationModuleSchema(
        id=row.id,
        name_fr=row.name_fr,
        name_en=row.name_en,
        category=row.category,  # type: ignore[arg-type]
        severity=row.severity,
        active=bool(row.active),
        L1_interference_description_fr=row.L1_interference_description_fr,
        L1_interference_description_en=row.L1_interference_description_en,
        detection_criteria=detection_criteria,
        examples=examples,
        content_refs=content_refs,
        drill_ids=drill_ids,
        prerequisite_module_ids=prerequisite_module_ids,
        raccourci_lesson_id=row.raccourci_lesson_id,
    )


@router.get("")
async def list_modules(
    category: Optional[ModuleCategory] = Query(default=None),
    db: Session = Depends(get_db),
):
    """List active modules, optionally filtered by category.

    Inactive modules are always excluded from the list view — they
    remain addressable by id via GET /api/modules/{id} so admin/debug
    tooling can still introspect deprecated rows.
    """
    q = db.query(RemediationModuleORM).filter(
        RemediationModuleORM.active == True  # noqa: E712
    )
    if category is not None:
        q = q.filter(RemediationModuleORM.category == category)
    rows = q.order_by(
        RemediationModuleORM.severity.desc(),
        RemediationModuleORM.id,
    ).all()
    return {"modules": [_hydrate(r).model_dump() for r in rows]}


def _coerce_iso(value) -> str | None:
    """Same helper used by users.py for detected_at normalization."""
    if value is None:
        return None
    if isinstance(value, _dt.datetime):
        return value.isoformat()
    return str(value)


def _user_context_for(
    module_id: str, user: User | None, db: Session
) -> dict | None:
    """F-080d B2 — when an authenticated user has detections of this
    module, return the per-user history block; otherwise None.

    The ``user_context`` field is always present in the response (per
    spec); ``None`` distinguishes "no token" / "user has no detections"
    from "field omitted." Frontend treats null as cold state.
    """
    if user is None:
        return None
    agg = (
        db.query(
            func.count(distinct(SessionDetectedModule.recording_id)).label("recurrence_count"),
            func.min(SessionDetectedModule.detected_at).label("first_detected_at"),
            func.max(SessionDetectedModule.detected_at).label("last_detected_at"),
            func.group_concat(distinct(SessionDetectedModule.recording_id)).label("recording_ids_csv"),
        )
        .join(Recording, Recording.id == SessionDetectedModule.recording_id)
        .filter(
            SessionDetectedModule.module_id == module_id,
            Recording.user_id == user.id,
        )
        .first()
    )
    rcount = int(agg.recurrence_count or 0) if agg else 0
    if not rcount:
        return None
    recording_ids = sorted(
        int(x) for x in (agg.recording_ids_csv or "").split(",") if x
    )
    return {
        "recurrence_count": rcount,
        "first_detected_at": _coerce_iso(agg.first_detected_at),
        "last_detected_at": _coerce_iso(agg.last_detected_at),
        "detected_in_recordings": recording_ids,
    }


@router.get("/{module_id}")
async def get_module(
    module_id: str,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    """F-080a public read + F-080d B2 augmentation.

    Always returns the full module shape. When the request carries a
    valid auth token (cookie or Authorization header), an additional
    ``user_context`` field is populated with per-user detection history;
    when the token is missing or the user has no detections of this
    module, ``user_context`` is null.

    F-080d locked Q4 to Option A: pre-launch all visitors authenticate
    before reaching /learn/[id], so user_context will be present in
    practice. The optional-auth backend is ready for the post-launch
    public-glossary path (F-080d.y) without forcing a frontend rewrite.

    404 unchanged when module_id doesn't exist.
    """
    row = (
        db.query(RemediationModuleORM)
        .filter(RemediationModuleORM.id == module_id)
        .first()
    )
    if row is None:
        raise HTTPException(404, f"No module with id {module_id!r}")
    payload = _hydrate(row).model_dump()
    payload["user_context"] = _user_context_for(module_id, user, db)
    return payload
