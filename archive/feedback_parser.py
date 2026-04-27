# Dead code from pre-routers async scaffold. Archived during F-077
# PostgreSQL migration to prevent accidental Alembic Base.metadata
# pollution. 5-minute insurance against accidental import.
"""
NEW FILE: app/services/feedback_parser.py

Extracts structured dashboard data from Claude's analysis response
and persists to the new dashboard tables.
"""

import json
import logging
from sqlalchemy.orm import Session

from app.models.models import (
    Feedback, GrammarSnapshot, InterferenceLog, MouleSnapshot,
    GRAMMAR_POINTS, CANONICAL_MOULES,
)

logger = logging.getLogger(__name__)


def parse_and_store_feedback(
    db: Session,
    feedback_id: int,
    llm_json: dict,
) -> None:
    """
    Takes the parsed dict from Claude's JSON response and populates
    the structured dashboard columns + detail tables.

    Call this AFTER saving the Feedback row. It's non-destructive:
    - Updates existing Feedback columns
    - Replaces detail table rows (idempotent)
    """
    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not feedback:
        logger.error(f"Feedback {feedback_id} not found")
        return

    # ── 1. Update Feedback with structured scores ──
    couches = llm_json.get("couches", {})
    feedback.couche1_contenu = couches.get("contenu", 0)
    feedback.couche2_discours = couches.get("discours", 0)
    feedback.couche3_phrase = couches.get("phrase", 0)
    feedback.couche4_interferences = couches.get("interferences", 0)

    feedback.detected_niveau = llm_json.get("detected_niveau", "")

    vocab = llm_json.get("vocabulaire", {})
    feedback.vocab_richesse = vocab.get("richesse", "")
    feedback.vocab_registre = vocab.get("registre", "")

    interferences_list = llm_json.get("interferences", [])
    moules_data = llm_json.get("moules", {})

    feedback.interference_count = len(interferences_list)
    feedback.moules_detected_count = len(moules_data.get("detected", []))
    feedback.moules_expected_count = (
        len(moules_data.get("detected", []))
        + len(moules_data.get("absent", []))
    )

    # ── 2. Grammar snapshots ──
    db.query(GrammarSnapshot).filter(
        GrammarSnapshot.feedback_id == feedback_id
    ).delete()

    for item in llm_json.get("inventaire_grammatical", []):
        point = item.get("point", "").lower().strip()
        status = item.get("status", "na").lower().strip()

        status_map = {
            "correct": "correct",
            "avec erreurs": "with_errors",
            "with_errors": "with_errors",
            "absent": "absent",
            "na": "na",
            "n/a": "na",
        }
        normalized_status = status_map.get(status, "na")

        snapshot = GrammarSnapshot(
            feedback_id=feedback_id,
            grammar_point=point,
            status=normalized_status,
            example=item.get("example", ""),
            correction=item.get("correction", ""),
        )
        db.add(snapshot)

    # ── 3. Interference logs ──
    db.query(InterferenceLog).filter(
        InterferenceLog.feedback_id == feedback_id
    ).delete()

    for interf in interferences_list:
        log = InterferenceLog(
            feedback_id=feedback_id,
            interference_type=interf.get("type", "calque_structural"),
            source_text=interf.get("source", ""),
            target_text=interf.get("target", ""),
            explanation=interf.get("explanation", ""),
            couche_tag=interf.get("couche", "C4"),
        )
        db.add(log)

    # ── 4. Moule snapshots ──
    db.query(MouleSnapshot).filter(
        MouleSnapshot.feedback_id == feedback_id
    ).delete()

    detected_moules = set(moules_data.get("detected", []))

    for moule_name in CANONICAL_MOULES:
        snapshot = MouleSnapshot(
            feedback_id=feedback_id,
            moule_name=moule_name,
            detected=moule_name in detected_moules,
        )
        db.add(snapshot)

    db.commit()
    logger.info(
        f"Dashboard data stored for feedback {feedback_id}: "
        f"niveau={feedback.detected_niveau}, "
        f"interferences={feedback.interference_count}, "
        f"moules={feedback.moules_detected_count}/{feedback.moules_expected_count}"
    )


def backfill_from_raw_responses(db: Session) -> int:
    """
    One-time migration: re-parse existing Feedback.raw_llm_response
    to populate dashboard tables retroactively.

    Usage:
        py -c "
        from app.database import SessionLocal
        from app.services.feedback_parser import backfill_from_raw_responses
        db = SessionLocal()
        count = backfill_from_raw_responses(db)
        print(f'Backfilled {count} sessions')
        db.close()
        "
    """
    feedbacks = db.query(Feedback).filter(
        Feedback.raw_llm_response != "",
        Feedback.raw_llm_response.isnot(None),
    ).all()

    parsed_count = 0
    for fb in feedbacks:
        try:
            raw = fb.raw_llm_response
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0]
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0]

            llm_json = json.loads(raw.strip())
            parse_and_store_feedback(db, feedback_id=fb.id, llm_json=llm_json)
            parsed_count += 1
        except (json.JSONDecodeError, IndexError, KeyError) as e:
            logger.warning(f"Could not backfill feedback {fb.id}: {e}")
            continue

    return parsed_count
