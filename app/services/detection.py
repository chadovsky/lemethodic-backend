"""P-200 — cluster detection engine.

Modeled on app/services/module_detector.py (F-080b). Same patterns,
different domain:
  - module_detector evaluates against the RemediationModule library
    (L1 interference patterns, "what's wrong with this French")
  - detect_clusters evaluates against Cluster.detection_rubric
    (curriculum cluster firings, "which clusters need revisit")

Both can fire on the same recording — they're orthogonal lenses.

ONE Claude call per recording (per Q2 decision). All matching clusters'
rubrics are injected into the system prompt; output is structured JSON
with one entry per cluster.

Cluster filtering:
  WHERE tache_application = recording.tache_mode
  AND   detection_rubric->'markers' is non-empty (skips placeholders)

Per-cluster best-effort parsing (per the 2026-05-02 robustness call):
if Claude returns 6 cluster findings and 1 has malformed shape, parse
the 5 valid ones and skip the 1. Don't all-or-nothing.

Never raises — degrades to empty_payload() on any failure.
"""
from __future__ import annotations

import json
import logging
from typing import Iterable, Literal

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import settings
from app.models.models import Cluster
from app.schemas.detection import (
    ClusterFinding,
    DetectionPayload,
    empty_payload,
)
from app.services.analysis import _call_claude


logger = logging.getLogger(__name__)


TacheModeForDetection = Literal["tache_1", "tache_2", "tache_3"]


# Sonnet-4 — matches the model used by the existing analyzers.
_DEFAULT_MODEL = "claude-sonnet-4-20250514"


_DETECTION_SYSTEM = """You are a French-language cluster detection engine for LeMethodic, a TCF Expression Orale prep app for English speakers learning French.

Your job: given a French candidate's transcript and a list of CURRICULUM CLUSTER RUBRICS, evaluate each rubric against the transcript. For each cluster, decide which markers are firing, which status_logic branch matches, and assign a per-cluster detection_result.

═══════════════════════════════════════════════════════════
CLUSTER RUBRICS (all clusters relevant to this Tâche)
═══════════════════════════════════════════════════════════

{cluster_rubrics}

═══════════════════════════════════════════════════════════
DETECTION RULES
═══════════════════════════════════════════════════════════

For EACH cluster above:

1. Read the cluster's markers. Each marker has:
   - marker_id: stable ID, e.g. "B1.1.C1.a"
   - severity: "high" or "medium"
   - firing_condition_prose: prose describing what fires this marker

2. For each marker, decide if it's FIRING in the transcript by reading the firing_condition_prose and matching it against the transcript content. A marker fires when the candidate's speech exhibits the pattern described.

3. Cite EVIDENCE — when a marker fires, supply a verbatim quote from the transcript that triggered it. No paraphrasing. If you cannot point to a verbatim quote, the marker DOES NOT fire.

4. Apply the cluster's status_logic to the set of fired markers:
   - "absorbed" branch: typically all markers silent (read the prose for exact criteria)
   - "partial" branch: typically 1 marker firing (read the prose for exact criteria)
   - "needs_revisit" branch: typically 2+ markers firing OR a specific high-severity marker alone (read the prose)

5. Map status_logic_path → detection_result:
   - status_logic_path == "absorbed"      → detection_result = "clean"
   - status_logic_path == "partial"       → detection_result = "wobble"
   - status_logic_path == "needs_revisit" → detection_result = "fail"

6. SPECIAL CASE — "not_observed": if the transcript doesn't contain enough material to evaluate this cluster (e.g. the cluster requires a 60+ second narrative but the transcript is only 30 seconds, or the cluster targets dialogue patterns and the transcript is a monologue with no interaction), set:
   - detection_result = "not_observed"
   - status_logic_path = null
   - rubric_score = null
   - fired_markers = []
   - silent_markers = [all marker_ids from the cluster, since none could be evaluated]
   Use this sparingly — prefer "clean" when markers are silent because they didn't fire, not because they couldn't be checked.

7. rubric_score: a float in [0, 1], or null when not_observed:
   - clean (no markers firing): 1.0
   - wobble (1 medium-severity marker firing): 0.5
   - wobble (1 high-severity marker firing alone, NOT named in needs_revisit): 0.3
   - fail (1 high-severity marker firing alone, named as a sole-trigger in needs_revisit): 0.0
   - fail (2+ markers firing): 0.0 to 0.2 depending on severity mix
   - not_observed: null

═══════════════════════════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════════════════════════

Return ONLY a JSON object, no preamble, no code fences. Use single braces (this is literal JSON, not a format-string template):

{
  "cluster_findings": [
    {
      "cluster_slug": "<slug from rubrics above>",
      "detection_result": "clean" | "wobble" | "fail" | "not_observed",
      "fired_markers": [
        {"marker_id": "<exact id>", "severity": "high" | "medium", "evidence": "<verbatim quote>"}
      ],
      "silent_markers": ["<marker_id>", ...],
      "status_logic_path": "absorbed" | "partial" | "needs_revisit" | null,
      "rubric_score": <float 0..1 or null>
    }
  ]
}

CRITICAL RULES:
- Emit ONE entry per cluster in the rubrics. Don't omit any cluster.
- cluster_slug must match EXACTLY one of the slugs above (case-sensitive, e.g. "B1.1.C1").
- marker_id values in fired_markers MUST come from the cluster's markers array. Don't invent.
- evidence must be a VERBATIM quote from the transcript. No paraphrasing. No synthesis.
- Empty fired_markers is valid (clean detection). Empty silent_markers is also valid (everything fired, fail detection).
- Return cluster_findings entries in the same order as the rubrics above.
"""


# ── JSON extraction (duplicated from module_detector.py for now) ──
# Kept as a sibling instead of a shared helper to keep the F-080b
# detector stable. Hoist to app/services/_claude_helpers.py if a third
# consumer ever needs it.

def _extract_first_json_object(s: str) -> dict | None:
    """Extract the first balanced ``{...}`` JSON object from a string,
    tolerant of leading/trailing prose."""
    if not isinstance(s, str):
        return None
    start = s.find("{")
    if start == -1:
        return None
    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(s)):
        c = s[i]
        if escape:
            escape = False
            continue
        if in_str:
            if c == "\\":
                escape = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                candidate = s[start : i + 1]
                try:
                    parsed = json.loads(candidate)
                except json.JSONDecodeError:
                    return None
                return parsed if isinstance(parsed, dict) else None
    return None


# ── Cluster fetch + filter ─────────────────────────────────────


def _fetch_active_clusters(db: Session, tache_mode: str) -> list[Cluster]:
    """Return clusters whose tache_application matches AND have non-empty
    rubric markers. Placeholder clusters (B1.4.* / B1.5.*) are excluded
    because they have detection_rubric == {}.

    Filtering is Python-side after the SQL filter — at 13 clusters total
    in Phase 1 the cost is negligible, and the readability beats a
    JSONB-aware WHERE clause."""
    candidates = (
        db.query(Cluster)
        .filter(Cluster.tache_application == tache_mode)
        .order_by(Cluster.slug)
        .all()
    )
    return [
        c
        for c in candidates
        if isinstance(c.detection_rubric, dict)
        and c.detection_rubric.get("markers")
    ]


def _format_cluster_rubrics_for_prompt(clusters: Iterable[Cluster]) -> str:
    """Render rubrics into the prompt blob. Concise but lossless — every
    field that informs detection is present."""
    sections: list[str] = []
    for c in clusters:
        rubric = c.detection_rubric or {}
        markers_lines = []
        for m in rubric.get("markers", []) or []:
            markers_lines.append(
                f"  - {m.get('marker_id', '?')}: "
                f"[{m.get('severity', '?')}] "
                f"{m.get('name', '')} — "
                f"{m.get('firing_condition_prose', '')}"
            )
        markers_text = "\n".join(markers_lines) if markers_lines else "  (none)"

        signals_lines = []
        for s in rubric.get("quantitative_signals", []) or []:
            signals_lines.append(
                f"  - {s.get('name', '?')}: "
                f"{s.get('computation', '')} → "
                f"{s.get('threshold', '')}"
            )
        signals_text = (
            "\n".join(signals_lines) if signals_lines else "  (none)"
        )

        sl = rubric.get("status_logic", {}) or {}
        status_logic_text = (
            f"  - absorbed:      {sl.get('absorbed', '')}\n"
            f"  - partial:       {sl.get('partial', '')}\n"
            f"  - needs_revisit: {sl.get('needs_revisit', '')}"
        )

        labels = c.labels or {}
        title = labels.get("en") or labels.get("fr") or c.slug

        sections.append(
            f"─── Cluster {c.slug} — {title} "
            f"(level: {c.cefr_level}, tache: {c.tache_application}) ───\n"
            f"Markers:\n{markers_text}\n"
            f"Quantitative signals:\n{signals_text}\n"
            f"Status logic:\n{status_logic_text}"
        )
    return "\n\n".join(sections)


# ── Coerce + best-effort parse ─────────────────────────────────


def _coerce_payload(raw, *, model: str) -> DetectionPayload:
    """Normalize whatever Claude returned into DetectionPayload, with
    per-cluster best-effort parsing.

    A single malformed cluster_findings entry is logged and skipped.
    Surviving entries land in the payload. If ZERO survive (or the
    overall envelope was malformed), returns empty_payload(model).
    """
    if isinstance(raw, str):
        try:
            raw = json.loads(
                raw.strip()
                .removeprefix("```json")
                .removeprefix("```")
                .removesuffix("```")
                .strip()
            )
        except json.JSONDecodeError:
            extracted = _extract_first_json_object(raw)
            if extracted is None:
                logger.warning(
                    "P-200 _coerce_payload: Claude returned non-JSON "
                    "(preview: %r); returning empty.",
                    str(raw)[:160],
                )
                return empty_payload(model=model)
            logger.info(
                "P-200 _coerce_payload: extracted JSON from prose preamble."
            )
            raw = extracted

    if not isinstance(raw, dict):
        logger.warning(
            "P-200 _coerce_payload: unexpected envelope shape (%s); "
            "returning empty.",
            type(raw).__name__,
        )
        return empty_payload(model=model)

    findings_raw = raw.get("cluster_findings", [])
    if not isinstance(findings_raw, list):
        logger.warning(
            "P-200 _coerce_payload: cluster_findings is not a list (%s); "
            "returning empty.",
            type(findings_raw).__name__,
        )
        return empty_payload(model=model)

    parsed: list[ClusterFinding] = []
    for entry in findings_raw:
        if not isinstance(entry, dict):
            logger.warning(
                "P-200 _coerce_payload: skipping non-dict finding entry: %r",
                str(entry)[:120],
            )
            continue
        try:
            parsed.append(ClusterFinding.model_validate(entry))
        except ValidationError as e:
            slug = entry.get("cluster_slug", "<unknown>")
            logger.warning(
                "P-200 _coerce_payload: skipping invalid finding for "
                "cluster_slug=%s: %s",
                slug,
                e.errors(include_url=False)[:1],
            )
            continue

    if not parsed:
        logger.warning(
            "P-200 _coerce_payload: zero valid findings parsed (saw %d "
            "raw entries); returning empty.",
            len(findings_raw),
        )

    return DetectionPayload(
        cluster_findings=parsed,
        model=model,
        input_tokens=None,
        output_tokens=None,
    )


# ── Public entry point ─────────────────────────────────────────


async def detect_clusters(
    transcript: str,
    tache_mode: TacheModeForDetection,
    db: Session,
) -> DetectionPayload:
    """Run cluster detection against a transcript. Never raises — degrades
    to empty_payload() on any failure path.

    Called from analyze_tache_1/2/3 after the existing 4-couche analysis
    + module_detector pipeline (commit 3 lands that wiring). Result is
    persisted via app.services.cluster_status_persistence.
    """
    transcript = (transcript or "").strip()
    if not transcript:
        logger.info(
            "P-200 detect_clusters: empty transcript for tache_mode=%s; "
            "returning empty result.",
            tache_mode,
        )
        return empty_payload(model=_DEFAULT_MODEL)

    if tache_mode not in ("tache_1", "tache_2", "tache_3"):
        logger.warning(
            "P-200 detect_clusters: unknown tache_mode=%r; returning empty.",
            tache_mode,
        )
        return empty_payload(model=_DEFAULT_MODEL)

    clusters = _fetch_active_clusters(db, tache_mode)
    if not clusters:
        logger.info(
            "P-200 detect_clusters: no active clusters for tache_mode=%s; "
            "returning empty result.",
            tache_mode,
        )
        return empty_payload(model=_DEFAULT_MODEL)

    if not settings.ANTHROPIC_API_KEY:
        # Demo mode: no fake findings. Honest empty result.
        logger.info(
            "P-200 detect_clusters: ANTHROPIC_API_KEY absent; returning "
            "empty result (demo mode)."
        )
        return empty_payload(model=_DEFAULT_MODEL)

    cluster_blob = _format_cluster_rubrics_for_prompt(clusters)
    system_prompt = _DETECTION_SYSTEM.replace("{cluster_rubrics}", cluster_blob)
    user_msg = (
        f"Tâche: {tache_mode}\n"
        f"Clusters being evaluated: {len(clusters)}\n\n"
        f'Candidate transcript:\n"""\n{transcript}\n"""'
    )

    try:
        raw = await _call_claude(system_prompt, user_msg)
    except Exception as exc:
        logger.warning(
            "P-200 detect_clusters: Claude call failed for tache_mode=%s "
            "(%s); returning empty result.",
            tache_mode,
            exc,
        )
        return empty_payload(model=_DEFAULT_MODEL)

    return _coerce_payload(raw, model=_DEFAULT_MODEL)
