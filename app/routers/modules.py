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

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import RemediationModule as RemediationModuleORM
from app.schemas.modules import ModuleCategory, RemediationModule as RemediationModuleSchema

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


@router.get("/{module_id}")
async def get_module(
    module_id: str,
    db: Session = Depends(get_db),
):
    row = (
        db.query(RemediationModuleORM)
        .filter(RemediationModuleORM.id == module_id)
        .first()
    )
    if row is None:
        raise HTTPException(404, f"No module with id {module_id!r}")
    return _hydrate(row).model_dump()
