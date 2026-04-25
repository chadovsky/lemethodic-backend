"""F-080b — Remediation module library helpers.

Three responsibilities, kept in one module so the validation logic
(fetch_valid_module_ids) shared between the prompt builder and the
persistence helper doesn't drift across files:

1. ``fetch_active_modules_for_prompt(db)`` — render the active library
   into a compact text block for injection into Claude analysis prompts.
   Token cost grows linearly with library size; ~600 tokens per 2 modules
   today, ~9k tokens projected at 30 modules. The F-080 ticket pack flags
   this for revisit at 25+ modules — at that point we'll switch to
   per-Tâche category subsetting rather than full-library injection.

2. ``fetch_valid_module_ids(db)`` — set of active module ids. Used by
   the persistence helper to reject hallucinated module_ids before
   insert; also re-used implicitly when validating prompt-side coverage
   in tests.

3. ``persist_detected_modules(...)`` — single source of truth for
   writing detection rows. Called from BOTH finalize paths
   (conversations.py for T1/T2 via /end; recordings.py for T3 via
   /upload). Hallucinated ids are logged and skipped. The row matching
   ``primary_module_id`` is marked is_primary=1; everything else is 0.
"""
from __future__ import annotations

import logging
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from app.models.models import RemediationModule, SessionDetectedModule

logger = logging.getLogger(__name__)


# Per-module rendering format. Compact on purpose — the goal is enough
# signal for Claude to match candidate transcript patterns to module ids
# without dragging the full L1_interference_description / examples /
# content_refs into context (those are diagnostic-page concerns, not
# detection concerns).
_MODULE_BLOCK_TEMPLATE = (
    "MODULE_ID: {id}\n"
    "  name: {name_en}\n"
    "  category: {category}, severity: {severity}\n"
    "  keywords_wrong: {keywords_wrong}\n"
    "  grammatical_signals:\n{grammatical_signals}\n"
    "  contextual_triggers:\n{contextual_triggers}\n"
)


def _bullet_list(items: Iterable[str]) -> str:
    """Render a list as `    - line` for compact prompt indentation."""
    items = [str(x).strip() for x in (items or []) if str(x).strip()]
    if not items:
        return "    - (none)"
    return "\n".join(f"    - {item}" for item in items)


def fetch_active_modules_for_prompt(db: Session) -> str:
    """Return the active module library as a compact text block.

    Empty string when the library is empty — callers should treat this
    as "skip module detection" rather than "force-detect with no
    options". The detector.py wrapper enforces that.

    F-080b post-ship fix (Path A): ordering is alphabetical-by-id rather
    than severity-DESC. Severity-ordered injection biased the model to
    anchor on the first vivid surface-visible match (e.g. nuance_reflex
    severity 5) and underweight subtler conditional ones (e.g.
    gerondif_confusion severity 3). Alphabetical is deterministic
    (avoids the run-to-run variance that random ordering introduced)
    and category/severity-neutral.
    """
    import json

    rows = (
        db.query(RemediationModule)
        .filter(RemediationModule.active == True)  # noqa: E712
        .order_by(RemediationModule.id)
        .all()
    )
    if not rows:
        return ""

    blocks: list[str] = []
    for row in rows:
        try:
            criteria = json.loads(row.detection_criteria or "{}")
        except json.JSONDecodeError:
            logger.warning(
                "Module %s has malformed detection_criteria JSON; "
                "skipping for prompt injection.",
                row.id,
            )
            continue

        keywords = criteria.get("keywords_wrong", []) or []
        grammatical = criteria.get("grammatical_signals", []) or []
        contextual = criteria.get("contextual_triggers", []) or []

        block = _MODULE_BLOCK_TEMPLATE.format(
            id=row.id,
            name_en=row.name_en or row.id,
            category=row.category,
            severity=row.severity,
            keywords_wrong=", ".join(str(k) for k in keywords) or "(none)",
            grammatical_signals=_bullet_list(grammatical),
            contextual_triggers=_bullet_list(contextual),
        )
        blocks.append(block)

    return "\n".join(blocks)


def fetch_valid_module_ids(db: Session) -> set[str]:
    """Set of active module ids — used to reject hallucinated detections
    before they hit ``session_detected_modules``. Inactive ids are
    excluded so Claude can't re-surface a deprecated module by id."""
    rows = (
        db.query(RemediationModule.id)
        .filter(RemediationModule.active == True)  # noqa: E712
        .all()
    )
    return {r[0] for r in rows}


def persist_detected_modules(
    recording_id: int,
    detected_modules: list[dict],
    primary_module_id: Optional[str],
    db: Session,
) -> None:
    """Insert one ``session_detected_modules`` row per valid detection.

    Spec contract (F-080b verification gates):
    - hallucinated module_ids (not in the active library) are logged at
      WARNING and skipped — never inserted, never crash the caller
    - exactly one row gets is_primary=1, matching ``primary_module_id``
    - empty ``detected_modules`` is a valid result; no rows inserted,
      one INFO log line emitted for traceability
    - the caller has already committed the Recording row before this
      runs, so ``recording_id`` is a known-good FK target

    The function commits its own inserts. Failures during the Claude
    call upstream (malformed JSON, network errors) should produce
    ``detected_modules=[]`` at the analyzer layer — by the time we get
    here, an empty list means "honestly no detections," not "something
    broke."
    """
    if not detected_modules:
        logger.info(
            "F-080b: no modules detected for recording_id=%s (empty list).",
            recording_id,
        )
        return

    valid_ids = fetch_valid_module_ids(db)
    inserted = 0
    skipped_hallucinations: list[str] = []
    primary_actually_set = False

    for det in detected_modules:
        if not isinstance(det, dict):
            logger.warning(
                "F-080b: malformed detection entry on recording_id=%s "
                "(type=%s) — skipping.",
                recording_id,
                type(det).__name__,
            )
            continue

        module_id = det.get("module_id")
        if not isinstance(module_id, str) or not module_id.strip():
            logger.warning(
                "F-080b: detection on recording_id=%s missing module_id — skipping.",
                recording_id,
            )
            continue
        module_id = module_id.strip()

        if module_id not in valid_ids:
            # Hallucinated id (Claude invented something not in the
            # injected library). Log and skip — the F-080 spec is
            # explicit that false detections degrade trust more than
            # missed ones, so we'd rather drop than guess.
            skipped_hallucinations.append(module_id)
            continue

        is_primary = module_id == primary_module_id and not primary_actually_set
        if is_primary:
            primary_actually_set = True

        confidence = det.get("confidence")
        try:
            confidence_score = (
                float(confidence) if confidence is not None else None
            )
        except (TypeError, ValueError):
            logger.warning(
                "F-080b: detection on recording_id=%s for module %r had "
                "non-numeric confidence %r — storing NULL.",
                recording_id,
                module_id,
                confidence,
            )
            confidence_score = None

        supporting_quote = det.get("supporting_quote")
        if supporting_quote is not None and not isinstance(supporting_quote, str):
            supporting_quote = str(supporting_quote)

        row = SessionDetectedModule(
            recording_id=recording_id,
            module_id=module_id,
            is_primary=is_primary,
            confidence_score=confidence_score,
            supporting_quote=supporting_quote,
        )
        db.add(row)
        inserted += 1
        logger.info(
            "F-080b: detection inserted recording_id=%s module_id=%s "
            "confidence=%s is_primary=%s",
            recording_id,
            module_id,
            confidence_score,
            is_primary,
        )

    if skipped_hallucinations:
        logger.warning(
            "F-080b: skipped %d hallucinated module_id(s) on "
            "recording_id=%s: %s. Active library: %s",
            len(skipped_hallucinations),
            recording_id,
            skipped_hallucinations,
            sorted(valid_ids),
        )

    if (
        primary_module_id
        and primary_module_id in valid_ids
        and not primary_actually_set
    ):
        # primary_module_id pointed at a valid id but we didn't see a
        # matching detection in the list (shouldn't happen — Claude is
        # instructed to pick primary FROM the detected list — but stay
        # defensive). Log so the next iteration of the prompt can
        # tighten this.
        logger.warning(
            "F-080b: primary_module_id=%r on recording_id=%s did not "
            "match any detected_modules entry; no row marked is_primary.",
            primary_module_id,
            recording_id,
        )

    if inserted > 0:
        db.commit()
    else:
        # Nothing inserted (all hallucinations or all malformed) —
        # rollback is a no-op since we never added rows that committed,
        # but skip the commit for clarity.
        logger.info(
            "F-080b: no valid detections persisted for recording_id=%s "
            "(received %d entries, all rejected).",
            recording_id,
            len(detected_modules),
        )
