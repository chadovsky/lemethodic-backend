"""F-080a — Seed / re-seed the remediation_modules library from JSON.

Reads every ``*.json`` under ``seeds/modules/`` (at the backend repo
root), validates each one against ``app.schemas.modules.RemediationModule``,
and upserts by primary key ``id``. Re-running is safe and idempotent —
existing rows are updated in place with the new content (authoring-driven
pipeline: author edits the JSON, reruns seeder, DB reflects changes).

JSON-blob columns (detection_criteria, examples, content_refs, drill_ids,
prerequisite_module_ids) are serialized back to compact JSON strings
before persistence; the CRUD router parses them back on read.

Filename ↔ id: the seeder doesn't mechanically require them to match,
but by convention the file's stem equals the module id. Mismatch is
logged as a warning so authoring drift surfaces loudly.

Usage from project root:
    python -m scripts.seed_remediation_modules
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from pydantic import ValidationError

from app.database import SessionLocal
from app.models.models import RemediationModule
from app.schemas.modules import RemediationModule as ModuleSchema


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


SEEDS_DIR = Path(__file__).resolve().parent.parent / "seeds" / "modules"


def _serialize_for_db(parsed: ModuleSchema) -> dict:
    """Convert the pydantic model into the column-shaped dict the ORM
    takes. Multi-field JSON blobs are stringified here; scalars pass
    through untouched."""
    return {
        "id": parsed.id,
        "name_fr": parsed.name_fr,
        "name_en": parsed.name_en,
        "category": parsed.category,
        "severity": parsed.severity,
        "active": parsed.active,
        "L1_interference_description_fr": parsed.L1_interference_description_fr,
        "L1_interference_description_en": parsed.L1_interference_description_en,
        "detection_criteria": json.dumps(
            parsed.detection_criteria.model_dump(), ensure_ascii=False
        ),
        "examples": json.dumps(
            [e.model_dump() for e in parsed.examples], ensure_ascii=False
        ),
        "content_refs": json.dumps(
            [c.model_dump() for c in parsed.content_refs], ensure_ascii=False
        ),
        "drill_ids": json.dumps(parsed.drill_ids, ensure_ascii=False),
        "prerequisite_module_ids": json.dumps(
            parsed.prerequisite_module_ids, ensure_ascii=False
        ),
        "ecole_lesson_id": parsed.ecole_lesson_id,
    }


def _upsert(session, fields: dict) -> str:
    existing = (
        session.query(RemediationModule)
        .filter(RemediationModule.id == fields["id"])
        .first()
    )
    import datetime as _dt

    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
        existing.updated_at = _dt.datetime.utcnow()
        return "updated"
    session.add(RemediationModule(**fields))
    return "inserted"


def main() -> int:
    if not SEEDS_DIR.exists():
        logger.error("Seeds directory not found: %s", SEEDS_DIR)
        return 1

    json_files = sorted(SEEDS_DIR.glob("*.json"))
    if not json_files:
        logger.warning("No *.json files in %s — nothing to seed.", SEEDS_DIR)
        return 0

    session = SessionLocal()
    counts = {"inserted": 0, "updated": 0, "skipped": 0}
    try:
        for path in json_files:
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                logger.error("Skipping %s — invalid JSON: %s", path.name, exc)
                counts["skipped"] += 1
                continue

            try:
                parsed = ModuleSchema(**raw)
            except ValidationError as exc:
                logger.error(
                    "Skipping %s — schema validation failed:\n%s", path.name, exc
                )
                counts["skipped"] += 1
                continue

            # Warn on filename ↔ id drift but still accept.
            if path.stem != parsed.id:
                logger.warning(
                    "Filename stem %r does not match module id %r in %s",
                    path.stem,
                    parsed.id,
                    path.name,
                )

            action = _upsert(session, _serialize_for_db(parsed))
            counts[action] += 1
            logger.info("%s %s (%s)", action, parsed.id, path.name)

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    logger.info(
        "Seed summary: %d inserted, %d updated, %d skipped.",
        counts["inserted"],
        counts["updated"],
        counts["skipped"],
    )
    return 0 if counts["skipped"] == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
