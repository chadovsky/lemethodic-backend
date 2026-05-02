import os, json, logging
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

logger = logging.getLogger(__name__)
from app.database import get_db
from app.models.models import (
    User,
    Recording,
    Feedback,
    TestTopic,
    RemediationModule,
    SessionDetectedModule,
)
from app.services.auth import get_current_user
from app.services.stt import transcribe_audio
from app.services import storage
from app.services.analysis import analyze_transcript, analyze_recording
from app.services.fluency import compute_fluency
from app.services.exam_profiles import get_profile
from app.services.scoring_profiles import (
    ALLOWED_TACHE_MODES,
    is_valid_mode,
    compute_weighted_note_globale,
)
from app.services.pattern_catalog import log_unknown_pattern_keys
from app.services.module_library import persist_detected_modules
from app.services.cluster_status_persistence import persist_detection_result
from app.schemas.detection import empty_payload
from app.services.scoring_maps import cefr_from_score, clb_from_cefr
from app.services.transcript_suggestions import suggest_corrections
from app.services.couche_labels import couches_array
from app.config import settings


# F-075a — defensive route-level size check (Layer B). Layer A in
# main.py rejects on Content-Length before the body is buffered;
# this catches spoofed / chunked / missing-header cases. Raises a
# clean 413 so the frontend can show the same "too large" message
# regardless of which layer fired.
def _enforce_audio_size_cap(content: bytes) -> None:
    cap = settings.MAX_AUDIO_UPLOAD_BYTES
    if len(content) > cap:
        cap_mb = cap // (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"Audio file exceeds maximum allowed size of {cap_mb} MB",
        )

router = APIRouter(prefix="/api/recordings", tags=["recordings"])

# F-078: writes go through app.services.storage which creates parent
# dirs in the local-disk fallback and is a no-op for the Spaces backend.
# The legacy os.makedirs(UPLOAD_DIR) at module-import time is no longer
# necessary.

# Oral endpoints may only create oral Recording rows. "writing" is a valid
# enum value (F-047) but its dispatch lives behind the writing router, so
# the oral endpoints reject it explicitly rather than silently mis-routing.
_ORAL_TACHE_MODES: tuple[str, ...] = ("tache_1", "tache_2", "tache_3", "legacy")


def _validate_tache_mode_for_oral(tache_mode: str | None) -> str:
    """Validate ``tache_mode`` against the F-047 enum for oral endpoints.

    Raises HTTPException(400) when missing or invalid. Returns the
    validated mode on success.
    """
    if not tache_mode:
        raise HTTPException(
            400,
            "tache_mode is required. Choose one of: "
            + ", ".join(_ORAL_TACHE_MODES),
        )
    if not is_valid_mode(tache_mode):
        raise HTTPException(
            400,
            f"Invalid tache_mode '{tache_mode}'. Allowed: "
            + ", ".join(ALLOWED_TACHE_MODES),
        )
    if tache_mode == "writing":
        raise HTTPException(
            400,
            "tache_mode='writing' is not valid on /api/recordings; "
            "writing submissions use /api/writing.",
        )
    return tache_mode


async def _run_analysis_and_persist(
    rec: Recording,
    transcript_text: str,
    topic_text: str,
    target_level: str,
    ui_language: str,
    exam_profile_id: str,
    low_confidence_words: list,
    user_id: int,
    db: Session,
    tache_3_prompt: str | None = None,
) -> Feedback:
    """Run Claude analysis + persist Feedback row. Shared by /upload (legacy
    one-shot) and /confirm-transcript (F-002 two-step). Returns the Feedback
    row; raises HTTPException on failure and marks rec.status='error'."""
    try:
        profile = get_profile(exam_profile_id)
        # F-044 Spanish fallback.
        effective_ui_language = ui_language
        if ui_language == "es":
            logger.warning(
                f"Spanish content generation not yet implemented, "
                f"falling back to English for user_id={user_id}"
            )
            effective_ui_language = "en"
        # F-047: dispatch through analyze_recording so each mode hits its
        # own stub. rec.tache_mode is the source of truth — the router has
        # already validated and persisted it.
        tache_mode = rec.tache_mode or "legacy"
        analysis = await analyze_recording(
            tache_mode=tache_mode,
            transcript=transcript_text,
            topic=topic_text,
            target_level=target_level,
            ui_language=effective_ui_language,
            low_confidence_words=low_confidence_words,
            exam_profile=profile,
            # F-051: passed through to analyze_tache_3 when tache_mode == "tache_3"
            # so the argumentation sub-call can quote the prompt back.
            # Ignored by other modes — they don't read this kwarg.
            tache_3_prompt=tache_3_prompt,
            # F-080b: thread DB session into the per-mode analyzer so
            # module_detector can query the active library. T3 lives
            # entirely on this path (no /end), so this is the ONLY place
            # T3 sessions get module detection wired.
            db=db,
        )

        log_unknown_pattern_keys(analysis)

        carte = analysis.get("la_carte", {})
        goulet = analysis.get("le_goulet", {})
        par_couche = analysis.get("analyse_par_couche", {})
        prononciation = analysis.get("prononciation", {})
        profile_eval = analysis.get("exam_profile", {})

        criteria_rows = profile_eval.get("criteria_breakdown", []) or []
        examiner_map = {
            r.get("criterion_key"): r.get("examiner_remark_fr", "")
            for r in criteria_rows if isinstance(r, dict) and r.get("criterion_key")
        }
        coaching_map = {
            r.get("criterion_key"): r.get("teacher_coaching", {})
            for r in criteria_rows if isinstance(r, dict) and r.get("criterion_key")
        }
        next_step_value = analysis.get("next_step") or analysis.get("la_prochaine_etape", "")

        # F-047: recompute note_globale as a weighted sum using the
        # per-mode profile (4 couches on /5 scaled to /20, plus fluency on
        # /20). The LLM's raw note_globale is preserved in raw_response /
        # raw_llm_response via the analysis dict; the stored value is the
        # profile-weighted one so Tâche 1/2/3 overalls reflect their
        # different rubrics.
        fluency_score: float | None = None
        try:
            fluency_payload = json.loads(rec.fluency) if rec.fluency else None
            if isinstance(fluency_payload, dict):
                fluency_score = fluency_payload.get("score")
        except (json.JSONDecodeError, TypeError):
            fluency_score = None
        weighted_overall = compute_weighted_note_globale(
            tache_mode, carte, fluency_score
        )
        analysis["note_globale"] = weighted_overall
        analysis["overall_score"] = weighted_overall

        feedback = Feedback(
            recording_id=rec.id,
            note_globale=weighted_overall,
            score_le_fond=carte.get("le_fond", 0),
            score_les_moules_des_idees=carte.get("les_moules_des_idees", 0),
            score_les_moules=carte.get("les_moules", 0),
            score_les_reflexes_anglais=carte.get("les_reflexes_anglais", 0),
            score_prononciation=prononciation.get("score", 0),
            prononciation_data=json.dumps(prononciation, ensure_ascii=False),
            goulet_couche=goulet.get("couche", 0),
            goulet_nom=goulet.get("nom", ""),
            goulet_explication=goulet.get("explication", ""),
            ce_qui_marche=analysis.get("ce_qui_marche", ""),
            analyse_le_fond=par_couche.get("le_fond", ""),
            analyse_les_moules_des_idees=par_couche.get("les_moules_des_idees", ""),
            analyse_les_moules=par_couche.get("les_moules", ""),
            analyse_les_reflexes_anglais=par_couche.get("les_reflexes_anglais", ""),
            la_prochaine_etape=next_step_value,
            transcription_corrigee=analysis.get("transcription_corrigee", ""),
            patterns_detectes=json.dumps(analysis.get("patterns_detectes", []), ensure_ascii=False),
            patterns_manquants=json.dumps(analysis.get("patterns_manquants", []), ensure_ascii=False),
            reflexes_detectes=json.dumps(analysis.get("reflexes_detectes", []), ensure_ascii=False),
            corrections=json.dumps(analysis.get("corrections", []), ensure_ascii=False),
            ordonnance=json.dumps(analysis.get("ordonnance", {}), ensure_ascii=False),
            # F-083 — pedagogical rubric block; stored as a JSON blob.
            # Nullable: legacy rows + analyses that ran before F-083
            # land here as None and the frontend (F-084) renders
            # without the rubric panel.
            tache_rubric_data=(
                json.dumps(analysis["tache_rubric"], ensure_ascii=False)
                if isinstance(analysis.get("tache_rubric"), dict)
                else None
            ),
            # F-084 — narrative summary one-liner. Pulled out of the
            # rubric blob into its own column for queryability + clean
            # top-level API surface. Empty string from the rubric
            # fallback collapses to None for consistent legacy/empty
            # behavior on the frontend.
            narrative_summary=(
                (analysis["tache_rubric"].get("narrative_summary") or None)
                if isinstance(analysis.get("tache_rubric"), dict)
                else None
            ),
            raw_llm_response=analysis.get("raw_response", ""),
            criteria_breakdown=json.dumps(profile_eval, ensure_ascii=False),
            cefr_level=profile_eval.get("cefr_level", ""),
            clb_level=profile_eval.get("secondary_framework_value"),
            exam_profile=profile.id,
            examiner_remarks=json.dumps(examiner_map, ensure_ascii=False),
            teacher_coaching=json.dumps(coaching_map, ensure_ascii=False),
            feedback_grid=json.dumps(par_couche, ensure_ascii=False),
            overall_score=weighted_overall,
            analysis_text=analysis.get("ce_qui_marche", ""),
        )
        # F-051: overlay the Tâche 3 argumentation block into feedback_grid
        # (same slot pattern used by F-048/F-049 for the other Tâche extras).
        if analysis.get("tache_3"):
            try:
                grid = json.loads(feedback.feedback_grid) if feedback.feedback_grid else {}
            except json.JSONDecodeError:
                grid = {}
            if isinstance(grid, dict):
                grid["tache_3"] = analysis["tache_3"]
                feedback.feedback_grid = json.dumps(grid, ensure_ascii=False)

        db.add(feedback)
        rec.status = "done"
        db.commit()
        db.refresh(feedback)

        # F-080b: persist module detections AFTER the Recording + Feedback
        # rows are committed (FK target on session_detected_modules.recording_id
        # is rec.id, which exists by now). The helper logs and skips
        # hallucinated module_ids; it never raises. Wrap defensively
        # anyway — analysis success must not depend on detection success.
        try:
            persist_detected_modules(
                recording_id=rec.id,
                detected_modules=analysis.get("detected_modules") or [],
                primary_module_id=analysis.get("primary_module"),
                db=db,
            )
        except Exception as exc:
            logger.exception(
                "F-080b: persist_detected_modules raised on recording_id=%s "
                "(%s); upload completes regardless.",
                rec.id,
                exc,
            )

        # P-200: persist cluster detection results — same defensive
        # posture as F-080b above. Never lets detection failures
        # block the recording response.
        try:
            cluster_payload = analysis.get("cluster_findings_payload") or empty_payload()
            persist_detection_result(
                db=db,
                user_id=rec.user_id,
                recording=rec,
                payload=cluster_payload,
            )
            db.commit()
        except Exception as exc:
            db.rollback()
            logger.exception(
                "P-200: persist_detection_result raised on recording_id=%s "
                "(%s); upload completes regardless.",
                rec.id,
                exc,
            )

        return feedback
    except Exception as e:
        rec.status = "error"
        db.commit()
        raise HTTPException(500, f"Analysis failed: {str(e)}")


@router.post("/upload")
async def upload_and_analyze(
    audio: UploadFile = File(...),
    topic_id: int = Form(default=0),
    target_level: str = Form(default="B2"),
    ui_language: str = Form(default="en"),
    duration_seconds: float = Form(default=0),
    argument_structure: str = Form(default=""),
    exam_profile: str = Form(default="tcf_canada"),
    tache_mode: str | None = Form(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # F-047: validate up front so we don't save an audio file for a
    # request that was never going to succeed.
    mode = _validate_tache_mode_for_oral(tache_mode)

    # ── Save audio ─────────────────────────────────────────────
    ext = audio.filename.split(".")[-1] if audio.filename else "webm"
    storage_key = storage.user_upload_key(user.id, ext)  # P-103: per-user prefix
    content = await audio.read()
    _enforce_audio_size_cap(content)  # F-075a Layer B
    storage.write_bytes(storage_key, content, content_type=(audio.content_type or "application/octet-stream"))

    # ── Create recording ───────────────────────────────────────
    rec = Recording(
        user_id=user.id,
        audio_path=storage_key,
        target_level=target_level,
        duration_seconds=duration_seconds,
        topic_id=topic_id if topic_id else None,
        argument_structure=argument_structure,
        tache_mode=mode,
        status="transcribing",
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    # ── Get topic text ─────────────────────────────────────────
    topic_text = ""
    tache_3_prompt: str | None = None
    if topic_id:
        topic = db.query(TestTopic).filter(TestTopic.id == topic_id).first()
        if topic:
            topic_text = topic.title
            # F-051: for Tâche 3 we prefer the full argumentative prompt
            # over the short topic title when available.
            if mode == "tache_3" and (topic.tache_3_prompt_fr or "").strip():
                tache_3_prompt = topic.tache_3_prompt_fr

    # ── Transcribe (now returns word confidence) ───────────────
    try:
        stt_result = await transcribe_audio(content)
        rec.transcript = stt_result["transcript"]
        rec.word_count = len(rec.transcript.split()) if rec.transcript else 0
        rec.stt_confidence = stt_result.get("confidence", 0)
        rec.low_confidence_words = json.dumps(
            stt_result.get("low_confidence_words", []), ensure_ascii=False
        )
        fluency_data = compute_fluency(
            stt_result, recording_duration_sec=rec.duration_seconds
        )
        rec.fluency = json.dumps(fluency_data, ensure_ascii=False) if fluency_data else ""
        rec.status = "analyzing"
        db.commit()
    except Exception as e:
        rec.status = "error"
        db.commit()
        raise HTTPException(500, f"Transcription failed: {str(e)}")

    # ── Analyze with La Méthode en Couches (legacy one-shot path) ─
    await _run_analysis_and_persist(
        rec=rec,
        transcript_text=rec.transcript,
        topic_text=topic_text,
        target_level=target_level,
        ui_language=ui_language,
        exam_profile_id=exam_profile,
        low_confidence_words=stt_result.get("low_confidence_words", []),
        user_id=user.id,
        db=db,
        tache_3_prompt=tache_3_prompt,
    )
    return _format_recording(rec)


# ══════════════════════════════════════════════════════════════════
# F-002: two-step transcribe → confirm → analyze flow
# ══════════════════════════════════════════════════════════════════

_RE_RECORD_THRESHOLD = 0.30  # low_conf_ratio above which we prompt re-record


@router.post("/transcribe")
async def transcribe_only(
    audio: UploadFile = File(...),
    topic_id: int = Form(default=0),
    target_level: str = Form(default="B2"),
    ui_language: str = Form(default="en"),
    duration_seconds: float = Form(default=0),
    argument_structure: str = Form(default=""),
    exam_profile: str = Form(default="tcf_canada"),
    tache_mode: str | None = Form(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Step 1 of the correction loop: upload + transcribe + Haiku suggestions.
    Does NOT run feedback analysis. The student reviews + confirms via
    /confirm-transcript, which then triggers the Claude Sonnet analysis."""
    # F-047: validate up front so we don't save an audio file for a
    # request that was never going to succeed.
    mode = _validate_tache_mode_for_oral(tache_mode)

    ext = audio.filename.split(".")[-1] if audio.filename else "webm"
    storage_key = storage.user_upload_key(user.id, ext)  # P-103: per-user prefix
    content = await audio.read()
    _enforce_audio_size_cap(content)  # F-075a Layer B
    storage.write_bytes(storage_key, content, content_type=(audio.content_type or "application/octet-stream"))

    rec = Recording(
        user_id=user.id,
        audio_path=storage_key,
        target_level=target_level,
        duration_seconds=duration_seconds,
        topic_id=topic_id if topic_id else None,
        argument_structure=argument_structure,
        tache_mode=mode,
        status="transcribing",
    )
    db.add(rec); db.commit(); db.refresh(rec)

    topic_text = ""
    if topic_id:
        topic = db.query(TestTopic).filter(TestTopic.id == topic_id).first()
        if topic:
            topic_text = topic.title

    try:
        stt_result = await transcribe_audio(content)
        rec.transcript = stt_result["transcript"]
        rec.word_count = len(rec.transcript.split()) if rec.transcript else 0
        rec.stt_confidence = stt_result.get("confidence", 0)
        rec.low_confidence_words = json.dumps(
            stt_result.get("low_confidence_words", []), ensure_ascii=False
        )
        fluency_data = compute_fluency(
            stt_result, recording_duration_sec=rec.duration_seconds
        )
        rec.fluency = json.dumps(fluency_data, ensure_ascii=False) if fluency_data else ""
        rec.status = "awaiting_confirmation"
        db.commit()
    except Exception as e:
        rec.status = "error"
        db.commit()
        raise HTTPException(500, f"Transcription failed: {str(e)}")

    words = stt_result.get("words", [])
    total = stt_result.get("total_words", len(words))
    low_conf_indices = [
        i for i, w in enumerate(words)
        if w.get("confidence", 0) < 0.75 and len(w.get("text", "")) > 2
    ]
    ratio = (len(low_conf_indices) / total) if total else 0.0
    trigger_re_record = ratio > _RE_RECORD_THRESHOLD

    # Only pay the Haiku tokens when the correction UI will actually be
    # shown (ratio under threshold). On high-noise audio the student
    # re-records or uses the original as-is.
    suggestions: dict[int, str] = {}
    if low_conf_indices and not trigger_re_record:
        suggestions = await suggest_corrections(
            transcript=rec.transcript,
            words=words,
            low_conf_indices=low_conf_indices,
            topic=topic_text,
        )

    words_out = []
    for i, w in enumerate(words):
        text = w.get("text", "")
        conf = w.get("confidence", 0)
        low = conf < 0.75 and len(text) > 2
        entry = {"i": i, "text": text, "conf": round(conf, 2), "low": low}
        if low and i in suggestions:
            entry["suggestion"] = suggestions[i]
        words_out.append(entry)

    # Carry through the fields /confirm-transcript needs so the frontend
    # can hand them back without re-deriving.
    return {
        "id": rec.id,
        "transcript": rec.transcript,
        "words": words_out,
        "low_conf_count": len(low_conf_indices),
        "low_conf_ratio": round(ratio, 3),
        "trigger_re_record": trigger_re_record,
        "stt_confidence": stt_result.get("confidence", 0),
        "total_words": total,
        "context": {
            "topic_id": topic_id,
            "target_level": target_level,
            "ui_language": ui_language,
            "exam_profile": exam_profile,
        },
    }


class ConfirmTranscriptRequest(BaseModel):
    corrected_transcript: str
    ui_language: str = "en"
    exam_profile: str = "tcf_canada"


@router.post("/{recording_id}/confirm-transcript")
async def confirm_transcript(
    recording_id: int,
    req: ConfirmTranscriptRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Step 2 of the correction loop: student submits their confirmed
    transcript (possibly edited). We persist it, run Claude analysis, and
    return the full recording + feedback payload."""
    rec = (
        db.query(Recording)
        .filter(Recording.id == recording_id, Recording.user_id == user.id)
        .first()
    )
    if not rec:
        raise HTTPException(404, "Recording not found")

    # Idempotency: if analysis already ran, return the existing formatted
    # response instead of re-calling Claude.
    if rec.status == "done" and rec.feedback is not None:
        return _format_recording(rec)

    corrected = (req.corrected_transcript or "").strip()
    if not corrected:
        raise HTTPException(400, "corrected_transcript must be non-empty")

    rec.corrected_transcript = corrected
    rec.transcript_confirmed = True
    rec.status = "analyzing"
    db.commit()

    topic_text = ""
    tache_3_prompt: str | None = None
    if rec.topic_id:
        topic = db.query(TestTopic).filter(TestTopic.id == rec.topic_id).first()
        if topic:
            topic_text = topic.title
            if (rec.tache_mode or "") == "tache_3" and (topic.tache_3_prompt_fr or "").strip():
                tache_3_prompt = topic.tache_3_prompt_fr

    try:
        lcw = json.loads(rec.low_confidence_words or "[]")
    except json.JSONDecodeError:
        lcw = []

    await _run_analysis_and_persist(
        rec=rec,
        transcript_text=corrected,
        topic_text=topic_text,
        target_level=rec.target_level or "B2",
        ui_language=req.ui_language,
        exam_profile_id=req.exam_profile,
        low_confidence_words=lcw,
        user_id=user.id,
        db=db,
        tache_3_prompt=tache_3_prompt,
    )
    return _format_recording(rec)


# ══════════════════════════════════════════════════════════════════
# F-051: Tâche 3 topic catalog
# ══════════════════════════════════════════════════════════════════

def _tache3_is_above_a2(user: User, db: Session) -> bool:
    """F-053: delegate to the ecole gating service — replaces the
    F-051 stub that always returned False."""
    from app.services.ecole_gating import is_above_a2
    return is_above_a2(user, db)


@router.get("/tache3-topics")
def list_tache3_topics(
    ui_language: str = "en",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return the Tâche 3 topic catalog filtered by the L'École
    gate. Only rows with a non-empty ``tache_3_prompt_fr`` are surfaced;
    seeded-but-un-prompted rows would confuse the picker."""
    allowed = {"A2_B1"}
    if _tache3_is_above_a2(user, db):
        allowed.update({"B1_B2", "B2_C1"})

    q = (
        db.query(TestTopic)
        .filter(TestTopic.is_active == True)  # noqa: E712
        .order_by(TestTopic.theme, TestTopic.id)
    )
    out = []
    for topic in q.all():
        prompt_fr = (topic.tache_3_prompt_fr or "").strip()
        if not prompt_fr:
            continue
        difficulty = (topic.tache_3_difficulty or "B1_B2")
        if difficulty not in allowed:
            continue
        out.append({
            "id": topic.id,
            "title": topic.title,
            "theme": topic.theme or "",
            "sous_theme": topic.sous_theme or "",
            "difficulty": difficulty,
            "prompt_fr": prompt_fr,
            "prompt_en": topic.tache_3_prompt_en or "",
            "prompt_es": topic.tache_3_prompt_es or "",
        })
    return {
        "topics": out,
        "gates": {"above_a2": _tache3_is_above_a2(user, db)},
    }


# ══════════════════════════════════════════════════════════════════
# F-110 — GET /api/recordings (lean list endpoint)
# ══════════════════════════════════════════════════════════════════
#
# REST-canonical list endpoint over the current user's recordings.
# Distinct from /history (which is the dashboard dump with topic +
# transcript preview + score breakdown + goulet); this one is a lean
# shape sized for the recordings list view in the new frontend.
#
# `joinedload(Recording.feedback)` issues a single LEFT OUTER JOIN
# so the per-row `r.feedback` access doesn't N+1. Topic isn't
# accessed here so we don't eager-load it.
@router.get("")
def list_recordings(
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return up to ``limit`` of the current user's recordings, newest
    first. Recordings without a Feedback row (status != "done") return
    null cefr_level/clb_level and an empty couches array — the lean
    shape stays uniform so the frontend can render in-flight rows
    without special-casing missing keys.
    """
    rows = (
        db.query(Recording)
        .options(joinedload(Recording.feedback))
        .filter(Recording.user_id == user.id)
        .order_by(Recording.created_at.desc())
        .limit(limit)
        .all()
    )

    out: list[dict] = []
    for r in rows:
        cefr_level: str | None = None
        clb_level: int | None = None
        couches: list[dict] = []
        if r.feedback is not None:
            profile_eval = _resolve_exam_profile_block(r.feedback)
            cefr_level = profile_eval["cefr_level"]
            clb_level = profile_eval["secondary_framework_value"]
            couches = couches_array({
                "le_fond": r.feedback.score_le_fond,
                "les_moules_des_idees": r.feedback.score_les_moules_des_idees,
                "les_moules": r.feedback.score_les_moules,
                "les_reflexes_anglais": r.feedback.score_les_reflexes_anglais,
            })

        out.append({
            "id": r.id,
            "tache_mode": r.tache_mode,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "cefr_level": cefr_level,
            "clb_level": clb_level,
            "couches": couches,
        })
    return out


@router.get("/history")
def get_history(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # F-002: hide orphaned recordings (awaiting_confirmation, abandoned
    # mid-correction, or failed analysis) from History. Rows remain in the DB
    # for a 24-48h recovery window — TODO: add a cleanup job in a later ticket.
    recs = (
        db.query(Recording)
        .filter(Recording.user_id == user.id)
        .filter(Recording.status == "done")
        .order_by(Recording.created_at.desc())
        .limit(50)
        .all()
    )
    results = []
    for r in recs:
        entry = {
            "id": r.id,
            "status": r.status,
            "target_level": r.target_level,
            "word_count": r.word_count,
            "duration_seconds": r.duration_seconds,
            "created_at": r.created_at.isoformat() if r.created_at else "",
            "transcript_preview": (r.transcript or "")[:100],
            "topic": r.topic.title if r.topic else None,
            "theme": r.topic.theme if r.topic else None,
        }
        if r.feedback:
            entry["note_globale"] = r.feedback.note_globale
            # F-088 — la_carte (internal-key dict) replaced with the
            # couches array (key + TCF display labels + score per
            # entry). See app/services/couche_labels.py for the
            # canonical mapping.
            entry["couches"] = couches_array({
                "le_fond": r.feedback.score_le_fond,
                "les_moules_des_idees": r.feedback.score_les_moules_des_idees,
                "les_moules": r.feedback.score_les_moules,
                "les_reflexes_anglais": r.feedback.score_les_reflexes_anglais,
            })
            entry["score_prononciation"] = r.feedback.score_prononciation
            entry["goulet_nom"] = r.feedback.goulet_nom
            entry["overall_score"] = r.feedback.note_globale
            # Exam profile summary for history list pills (backfilled for legacy rows)
            profile_eval = _resolve_exam_profile_block(r.feedback)
            entry["cefr_level"] = profile_eval["cefr_level"]
            entry["clb_level"] = profile_eval["secondary_framework_value"]
            entry["exam_profile_score"] = profile_eval["overall_score"]
        results.append(entry)
    return results


def _hydrate_module_for_response(row: RemediationModule) -> dict:
    """Parse the JSON-blob columns into the structured shape the
    frontend expects. Mirror of app.routers.modules._hydrate but
    returns a plain dict (not pydantic) since this endpoint composes
    several rows into a single response."""
    try:
        detection_criteria = json.loads(row.detection_criteria or "{}")
        examples = json.loads(row.examples or "[]")
        content_refs = json.loads(row.content_refs or "[]")
        drill_ids = json.loads(row.drill_ids or "[]")
        prerequisite_module_ids = json.loads(row.prerequisite_module_ids or "[]")
    except json.JSONDecodeError as exc:
        logger.error(
            "Module %s has malformed JSON in a blob column: %s — returning skeleton.",
            row.id,
            exc,
        )
        detection_criteria = {}
        examples = []
        content_refs = []
        drill_ids = []
        prerequisite_module_ids = []
    return {
        "id": row.id,
        "name_fr": row.name_fr,
        "name_en": row.name_en,
        "category": row.category,
        "severity": row.severity,
        "active": bool(row.active),
        "L1_interference_description_fr": row.L1_interference_description_fr,
        "L1_interference_description_en": row.L1_interference_description_en,
        "detection_criteria": detection_criteria,
        "examples": examples,
        "content_refs": content_refs,
        "drill_ids": drill_ids,
        "prerequisite_module_ids": prerequisite_module_ids,
        "ecole_lesson_id": row.ecole_lesson_id,
    }


@router.get("/{recording_id}/detected-modules")
def get_detected_modules(
    recording_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """F-080c — return the modules detected on this recording, hydrated
    with full module content for the diagnostic page.

    Response shape:
        {
          "primary_module": RemediationModule | null,
          "secondary_modules": [RemediationModule, ...],
          "detections": [
            {module_id, confidence_score, supporting_quote, is_primary}
          ]
        }

    Detections persisted by F-080b's persist_detected_modules helper
    skip hallucinated module_ids before insert, so any row in
    session_detected_modules is guaranteed to FK-resolve to an active
    module here. The endpoint returns module data only; couche scores
    flow through GET /api/recordings/{id} (existing).
    """
    rec = (
        db.query(Recording)
        .filter(Recording.id == recording_id, Recording.user_id == user.id)
        .first()
    )
    if not rec:
        raise HTTPException(404, "Recording not found")

    detection_rows = (
        db.query(SessionDetectedModule)
        .filter(SessionDetectedModule.recording_id == rec.id)
        .order_by(
            SessionDetectedModule.is_primary.desc(),
            SessionDetectedModule.id,
        )
        .all()
    )

    if not detection_rows:
        return {
            "primary_module": None,
            "secondary_modules": [],
            "detections": [],
        }

    # Hydrate referenced modules in one query (set keeps unique ids;
    # detection_rows can repeat the same module_id for multiple
    # supporting_quotes — F-080b's T1 avoir-misuse path emits 3 rows
    # with module_id="to_get_reflex").
    module_ids = {r.module_id for r in detection_rows}
    module_rows = (
        db.query(RemediationModule)
        .filter(RemediationModule.id.in_(module_ids))
        .all()
    )
    by_id = {m.id: m for m in module_rows}

    primary_module = None
    seen_secondary: set[str] = set()
    secondary_modules: list[dict] = []

    for det in detection_rows:
        mod = by_id.get(det.module_id)
        if mod is None:
            # FK existed at insert time but the module was deleted since.
            # Skip rather than 500 — log so the cleanup path surfaces.
            logger.warning(
                "F-080c: detection on recording_id=%s references missing "
                "module_id=%r; skipping in response.",
                rec.id,
                det.module_id,
            )
            continue
        if det.is_primary and primary_module is None:
            primary_module = _hydrate_module_for_response(mod)
            continue
        if mod.id in seen_secondary or (primary_module and primary_module["id"] == mod.id):
            continue
        secondary_modules.append(_hydrate_module_for_response(mod))
        seen_secondary.add(mod.id)

    detections = [
        {
            "module_id": det.module_id,
            "confidence_score": det.confidence_score,
            "supporting_quote": det.supporting_quote,
            "is_primary": bool(det.is_primary),
        }
        for det in detection_rows
        if det.module_id in by_id
    ]

    return {
        "primary_module": primary_module,
        "secondary_modules": secondary_modules,
        "detections": detections,
    }


@router.get("/{recording_id}")
def get_recording(
    recording_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rec = (
        db.query(Recording)
        .filter(Recording.id == recording_id, Recording.user_id == user.id)
        .first()
    )
    if not rec:
        raise HTTPException(404, "Recording not found")
    return _format_recording(rec)


def _format_recording(rec: Recording) -> dict:
    result = {
        "id": rec.id,
        "transcript": rec.transcript,
        "word_count": rec.word_count,
        "duration_seconds": rec.duration_seconds,
        "stt_confidence": rec.stt_confidence,
        "target_level": rec.target_level,
        "status": rec.status,
        "topic": rec.topic.title if rec.topic else None,
        "theme": rec.topic.theme if rec.topic else None,
        "created_at": rec.created_at.isoformat() if rec.created_at else "",
        "fluency": _safe_json_load(rec.fluency, default=None),
        "tache_mode": rec.tache_mode or "legacy",
        "conversation": _conversation_snapshot_for(rec),
    }
    if rec.feedback:
        fb = rec.feedback
        result["diagnostic"] = {
            "note_globale": fb.note_globale,
            # F-088 — la_carte replaced with the F-088 couches array
            # (key + display_label_en + display_label_fr + score per
            # entry). See app/services/couche_labels.py for the
            # canonical mapping.
            "couches": couches_array({
                "le_fond": fb.score_le_fond,
                "les_moules_des_idees": fb.score_les_moules_des_idees,
                "les_moules": fb.score_les_moules,
                "les_reflexes_anglais": fb.score_les_reflexes_anglais,
            }),
            "le_goulet": {
                "couche": fb.goulet_couche,
                "nom": fb.goulet_nom,
                "explication": fb.goulet_explication,
            },
            "ce_qui_marche": fb.ce_qui_marche,
            # Legacy per-couche shape, kept for pre-F-032 recordings.
            "analyse_par_couche_legacy": {
                "le_fond": fb.analyse_le_fond,
                "les_moules_des_idees": fb.analyse_les_moules_des_idees,
                "les_moules": fb.analyse_les_moules,
                "les_reflexes_anglais": fb.analyse_les_reflexes_anglais,
            },
            # F-032 2x2 grid (what_works / what_doesnt_work / english_habits /
            # structure_quality). Empty dict for legacy rows — frontend shows
            # a fallback notice in that case.
            "feedback_grid": _safe_json_load(fb.feedback_grid, default={}),
            "next_step": fb.la_prochaine_etape,
            "la_prochaine_etape": fb.la_prochaine_etape,
            "transcription_corrigee": fb.transcription_corrigee,
            "prononciation": json.loads(fb.prononciation_data) if fb.prononciation_data else {},
            # F-083 — pedagogical rubric (per-Tâche). None when the row
            # predates F-083 or when the rubric call failed; F-084
            # frontend renders without the panel in that case.
            "tache_rubric": _safe_json_load(fb.tache_rubric_data, default=None) if fb.tache_rubric_data else None,
            # F-084 — single-sentence diagnostic hero. None for legacy
            # rows; frontend falls back to "{cefr_band} on Tâche {n}"
            # when null.
            "narrative_summary": fb.narrative_summary,
            "patterns_detectes": json.loads(fb.patterns_detectes) if fb.patterns_detectes else [],
            "patterns_manquants": json.loads(fb.patterns_manquants) if fb.patterns_manquants else [],
            "reflexes_detectes": json.loads(fb.reflexes_detectes) if fb.reflexes_detectes else [],
            "corrections": json.loads(fb.corrections) if fb.corrections else [],
            "ordonnance": json.loads(fb.ordonnance) if fb.ordonnance else {},
        }
        result["exam_profile"] = _resolve_exam_profile_block(fb)
        result["feedback"] = {
            "overall_score": fb.note_globale,
            "analysis": fb.ce_qui_marche,
            "recommendations": fb.la_prochaine_etape,
        }
    return result


def _conversation_snapshot_for(rec: Recording) -> dict | None:
    """F-048/F-049: if this recording came from a multi-turn conversation,
    return its turns so the feedback page can show the full exchange.
    Returns None for non-conversation modes (tache_3, legacy, etc.)."""
    mode = (rec.tache_mode or "").lower()
    if mode not in ("tache_1", "tache_2"):
        return None
    # Avoid a circular import at module load time.
    from app.models.models import Conversation  # noqa: WPS433
    try:
        session = object.__getattribute__(rec, "_sa_instance_state").session
    except AttributeError:
        session = None
    if session is None:
        return None
    conv = (
        session.query(Conversation)
        .filter(Conversation.recording_id == rec.id)
        .first()
    )
    if not conv:
        return None
    return {
        "conversation_id": conv.id,
        "status": conv.status,
        # F-062.3: filter superseded turns. The diagnostic page shows the
        # committed conversation — retakes the candidate abandoned shouldn't
        # surface in the transcript replay.
        "turns": [
            {
                "turn_number": t.turn_number,
                "speaker": t.speaker,
                "text": t.text or "",
                "word_count": t.word_count or 0,
            }
            for t in conv.turns
            if t.superseded_at is None
        ],
    }


def _safe_json_load(raw: str | None, default):
    """Parse a JSON string column value, returning ``default`` on empty or
    malformed input. Used for feedback columns that may be legacy-empty."""
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


def _resolve_exam_profile_block(fb: Feedback) -> dict:
    """Return the exam-profile block for a feedback row, backfilling CEFR/CLB
    from note_globale for legacy recordings that predate 5-criterion scoring.
    Legacy rows get Score Overview pills but no criteria_breakdown rows — the
    frontend renders a 'Detailed breakdown not available' note in that case.
    """
    if fb.criteria_breakdown:
        try:
            block = json.loads(fb.criteria_breakdown)
            if isinstance(block, dict) and block.get("criteria_breakdown"):
                return block
        except json.JSONDecodeError:
            pass

    # Legacy row: derive CEFR/CLB from the holistic 4-couche score.
    score = float(fb.note_globale or 0)
    cefr = fb.cefr_level or cefr_from_score(score)
    clb = fb.clb_level if fb.clb_level is not None else clb_from_cefr(cefr)
    return {
        "profile_id": fb.exam_profile or "tcf_canada",
        "display_name": "TCF Canada",
        "frameworks_shown": ["raw20", "cefr", "clb"],
        "overall_score": score,
        "cefr_level": cefr,
        "secondary_framework_label": "CLB",
        "secondary_framework_value": clb,
        "criteria_breakdown": [],  # frontend shows fallback note when empty
        "legacy": True,
    }
