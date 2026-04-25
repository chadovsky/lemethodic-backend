"""F-048/F-049 — Conversation endpoints.

Server-side state: each /turn call rebuilds the conversation from the
DB. We never trust client-sent history — the router ignores any
conversation state in the request body beyond the ID and the uploaded
audio.

Endpoints:
- POST /api/conversations/start     — create conversation + (Tâche 1 only) opening turn
- POST /api/conversations/{id}/turn — upload candidate audio, append
                                      candidate + next examiner turns,
                                      auto-end if at mode-specific max
- POST /api/conversations/{id}/end  — manual end, trigger analysis
- GET  /api/conversations/{id}      — hydrate UI from DB (refresh resume)
- GET  /api/conversations/scenarios — F-049: Tâche 2 scenario catalog
                                      filtered by the user's raccourci gate
"""
from __future__ import annotations

import datetime
import json
import logging
import os
import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.models import (
    Conversation,
    ConversationTurn,
    Feedback,
    Recording,
    Tache1Opening,
    Tache2Scenario,
    TestTopic,
    User,
)
from app.services.auth import get_current_user
from app.services.fluency import compute_fluency
from app.services.pattern_catalog import log_unknown_pattern_keys
from app.services.raccourci_gating import is_above_a2 as _raccourci_is_above_a2
from app.services.scoring_profiles import (
    compute_weighted_note_globale,
    is_valid_mode,
)
from app.services.stt import transcribe_audio
from app.services.tache_1 import (
    analyze_tache_1,
    generate_examiner_turn as generate_examiner_turn_t1,
)
from app.services.tache_2 import (
    analyze_tache_2,
    generate_examiner_turn as generate_examiner_turn_t2,
)
from app.services.module_library import persist_detected_modules
from app.services.tts import synthesize as tts_synthesize
from app.services.personas.tache_1_examiner import (
    MAX_CANDIDATE_TURNS as T1_MAX_CANDIDATE_TURNS,
    MIN_CANDIDATE_TURNS as T1_MIN_CANDIDATE_TURNS,
    random_opening as t1_random_opening_fallback,
)
from app.services.personas.tache_2_examiner import (
    MAX_CANDIDATE_TURNS_HARD as T2_MAX_CANDIDATE_TURNS_HARD,
    MAX_CANDIDATE_TURNS_HINT as T2_MAX_CANDIDATE_TURNS_HINT,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# F-049: now includes tache_2. tache_3 doesn't use conversation plumbing
# (it's a single monologue upload via the recordings router).
_CONVERSATION_MODES: tuple[str, ...] = ("tache_1", "tache_2")


def _is_above_a2(user: User, db: Session) -> bool:
    """F-053: delegate to the Le Raccourci gating service. Replaces the
    F-049 stub that returned False unconditionally."""
    return _raccourci_is_above_a2(user, db)


def _scenarios_for_user(db: Session, user: User) -> list[Tache2Scenario]:
    """Return the active scenarios visible to this user, filtered by
    the raccourci gate. Ordered so pickers show A2_B1 content first
    (the familiar ramp)."""
    q = db.query(Tache2Scenario).filter(Tache2Scenario.is_active == True)  # noqa: E712
    allowed = {"A2_B1"}
    if _is_above_a2(user, db):
        allowed.update({"B1_B2", "B2_C1"})
    rows = [s for s in q.all() if (s.difficulty or "A2_B1") in allowed]
    difficulty_order = {"A2_B1": 0, "B1_B2": 1, "B2_C1": 2}
    rows.sort(key=lambda s: (difficulty_order.get(s.difficulty or "A2_B1", 9), s.id))
    return rows


def _serialize_scenario(scenario: Tache2Scenario, ui_language: str = "en") -> dict:
    try:
        data_targets = json.loads(scenario.data_targets or "[]")
        if not isinstance(data_targets, list):
            data_targets = []
    except json.JSONDecodeError:
        data_targets = []
    return {
        "id": scenario.id,
        "code": scenario.code,
        "title_fr": scenario.title_fr or "",
        "title_en": scenario.title_en or "",
        "title_es": scenario.title_es or "",
        "candidate_brief_fr": scenario.candidate_brief_fr or "",
        "candidate_brief_en": scenario.candidate_brief_en or "",
        "candidate_brief_es": scenario.candidate_brief_es or "",
        "register": scenario.register or "formel",
        "difficulty": scenario.difficulty or "A2_B1",
        "data_targets": data_targets,
    }


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _require_owner(db: Session, conversation_id: str, user: User) -> Conversation:
    conv = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == user.id)
        .first()
    )
    if not conv:
        raise HTTPException(404, "Conversation not found")
    return conv


def _serialize_turn(turn: ConversationTurn) -> dict:
    # F-052: expose examiner audio_url (a public /tts_audio/<hash>.mp3
    # URL) to the client. We deliberately do NOT expose candidate
    # audio_url — those are raw filesystem paths to ``./uploads`` and
    # aren't web-servable.
    examiner_audio = None
    if turn.speaker == "examiner" and (turn.audio_url or "").startswith("/tts_audio/"):
        examiner_audio = turn.audio_url
    return {
        "turn_number": turn.turn_number,
        "speaker": turn.speaker,
        "text": turn.text or "",
        "has_audio": bool(turn.audio_url),
        "examiner_audio_url": examiner_audio,
        "created_at": turn.created_at.isoformat() if turn.created_at else "",
        # F-062.3: supersede state. Frontend can use this to render superseded
        # rows differently in debug views; normal rendering just filters them
        # out. superseded_at is ISO-8601 or null.
        "superseded_at": (
            turn.superseded_at.isoformat() if turn.superseded_at else None
        ),
        "superseded_by_turn_id": turn.superseded_by_turn_id,
    }


def _serialize_conversation(conv: Conversation) -> dict:
    scenario = conv.scenario if conv.tache_mode == "tache_2" else None
    result = {
        "conversation_id": conv.id,
        "tache_mode": conv.tache_mode,
        "target_level": conv.target_level,
        "ui_language": conv.ui_language,
        "exam_profile": conv.exam_profile,
        "status": conv.status,
        "recording_id": conv.recording_id,
        "started_at": conv.started_at.isoformat() if conv.started_at else "",
        "completed_at": conv.completed_at.isoformat() if conv.completed_at else None,
        "turns": [_serialize_turn(t) for t in conv.turns],
    }
    if conv.tache_mode == "tache_1":
        result["max_candidate_turns"] = T1_MAX_CANDIDATE_TURNS
        result["min_candidate_turns"] = T1_MIN_CANDIDATE_TURNS
    elif conv.tache_mode == "tache_2":
        result["max_candidate_turns_hard"] = T2_MAX_CANDIDATE_TURNS_HARD
        result["max_candidate_turns_hint"] = T2_MAX_CANDIDATE_TURNS_HINT
        result["scenario"] = _serialize_scenario(scenario, conv.ui_language) if scenario else None
    return result


def _candidate_turns(conv: Conversation) -> list[ConversationTurn]:
    """Active candidate turns only. F-062.3: superseded turns (from the
    Refaire cette prise flow) are excluded — they represent retakes the
    candidate abandoned and shouldn't feed into analysis or cap checks."""
    return [
        t for t in conv.turns
        if t.speaker == "candidate" and t.superseded_at is None
    ]


def _examiner_voice_for(conv: Conversation) -> str:
    """Pick the configured OpenAI voice for this conversation mode.
    Tâche 2 scenarios could later override per-character, but for F-052
    a single voice per mode is enough."""
    if conv.tache_mode == "tache_2":
        return settings.TTS_VOICE_TACHE_2
    return settings.TTS_VOICE_TACHE_1


def _pick_random_tache1_opening(db: Session) -> str | None:
    """F-063: return a random active opening prompt from tache1_openings.

    Returns None when the table is empty/missing — the caller falls back
    to the in-code OPENING_PROMPTS tuple from the persona module so a
    fresh DB still boots a usable Tâche 1 flow.
    """
    from sqlalchemy import func
    try:
        row = (
            db.query(Tache1Opening)
            .filter(Tache1Opening.is_active == True)  # noqa: E712
            .order_by(func.random())
            .first()
        )
    except Exception as exc:
        # Table doesn't exist yet (pre-migration) or other DB-level issue —
        # let the fallback kick in rather than 500 the session.
        logger.warning("F-063 DB lookup failed, falling back to in-code opening: %s", exc)
        return None
    if row is None or not (row.opening_prompt_fr or "").strip():
        return None
    return row.opening_prompt_fr.strip()


async def _append_examiner_turn(
    conv: Conversation, db: Session
) -> ConversationTurn | None:
    """Generate + persist the next examiner turn. Returns None if the
    per-mode generator declines to speak (Tâche 2 before the candidate
    has said anything).

    F-052: after the text is generated, synthesize TTS audio and store
    the public URL on the turn's ``audio_url`` column. Returns the
    turn with whichever url TTS produced (None = text-only fallback,
    not an error).
    """
    next_number = len(conv.turns)
    if conv.tache_mode == "tache_2":
        scenario = conv.scenario
        text = await generate_examiner_turn_t2(conv, scenario)
    elif conv.tache_mode == "tache_1" and next_number == 0:
        # F-063: the Tâche 1 opening is a random pick from the
        # tache1_openings table (8 seeded variants) rather than the
        # persona module's hardcoded tuple. Fallback to the in-code
        # pool if the table is empty — nothing else in the flow has
        # to branch on DB state.
        text = _pick_random_tache1_opening(db) or t1_random_opening_fallback()
    else:
        text = await generate_examiner_turn_t1(conv)
    if not text:
        return None

    # F-052: synthesize voice. Non-fatal — ``synthesize`` returns None
    # on missing key / network error, and the UI falls back to
    # text-only for that turn.
    audio_url: str | None = None
    try:
        audio_url = await tts_synthesize(text, voice=_examiner_voice_for(conv))
    except Exception as exc:
        logger.warning("F-052 TTS synth failed for conversation %s: %s", conv.id, exc)
        audio_url = None

    turn = ConversationTurn(
        conversation_id=conv.id,
        turn_number=next_number,
        speaker="examiner",
        text=text,
        audio_url=audio_url,
    )
    db.add(turn)
    db.commit()
    db.refresh(turn)
    db.refresh(conv)
    return turn


async def _run_conversation_analysis_and_persist(
    conv: Conversation, db: Session
) -> Recording:
    """On completion, aggregate candidate turns into a Recording +
    Feedback row so the existing history / feedback page pipeline just
    works. Sets ``conv.recording_id`` on success.

    Dispatches to the per-mode analyzer (tache_1 or tache_2); each one
    returns a result dict that overlays a ``tache_1`` / ``tache_2``
    block on the standard 4-couche analysis output. Both get stashed
    inside ``feedback_grid`` so the frontend can render without new
    columns.

    The Recording's ``audio_path`` points at the first candidate turn's
    audio so any legacy "download audio" UI still resolves to a real
    file. The full turn-by-turn audio manifest stays on the
    ``ConversationTurn`` rows.
    """
    # Pull candidate turns once — used for combined-transcript + word count.
    candidates = _candidate_turns(conv)
    if not candidates:
        raise HTTPException(400, "No candidate turns to analyze")

    combined_transcript = "\n—\n".join((t.text or "").strip() for t in candidates if (t.text or "").strip())
    word_count = len(combined_transcript.split())

    # Low-confidence words aggregate — pronunciation analysis is shared
    # across all candidate turns.
    low_conf: list[dict] = []
    for t in candidates:
        try:
            fdata = json.loads(t.fluency or "null")
        except (json.JSONDecodeError, TypeError):
            fdata = None
        # per-turn low-confidence is stashed on the fluency payload under
        # the key "low_confidence_words" (we don't persist separately
        # for conv turns). Tolerate absence.
        if isinstance(fdata, dict):
            low_conf.extend(fdata.get("low_confidence_words", []) or [])

    # Aggregate fluency across candidate turns — weighted average of
    # per-turn scores by turn word count.
    fluency_scores = []
    total_wc = 0
    for t in candidates:
        try:
            fdata = json.loads(t.fluency or "null")
        except (json.JSONDecodeError, TypeError):
            fdata = None
        if isinstance(fdata, dict) and fdata.get("score") is not None:
            w = t.word_count or 0
            fluency_scores.append((float(fdata["score"]), w))
            total_wc += w
    if total_wc and fluency_scores:
        fluency_score: float | None = round(
            sum(s * w for s, w in fluency_scores) / total_wc, 1
        )
    else:
        fluency_score = None

    # F-044 Spanish fallback — mirror the existing recordings router
    # behavior. We don't know what Chadi's Spanish rollout status is
    # from here, so stick with English until told otherwise.
    effective_ui_language = conv.ui_language or "en"
    if effective_ui_language == "es":
        effective_ui_language = "en"

    analyzer = analyze_tache_1 if conv.tache_mode == "tache_1" else analyze_tache_2
    analysis = await analyzer(
        conversation=conv,
        target_level=conv.target_level or "B2",
        ui_language=effective_ui_language,
        low_confidence_words=low_conf,
        exam_profile=conv.exam_profile or "tcf_canada",
        fluency_score=fluency_score,
        # F-080b: thread the DB session into the analyzer so the
        # module_detector can query the active library. analyzer returns
        # detected_modules + primary_module on the result dict.
        db=db,
    )
    log_unknown_pattern_keys(analysis)

    # Build the aggregated Recording row. The audio_path constraint is
    # NOT NULL; point it at the first candidate's audio so the UI's
    # playback affordances still resolve.
    first_audio = candidates[0].audio_url or ""
    total_duration = 0.0
    # Conversation duration isn't currently tracked per-turn precisely
    # — leave at 0; the UI surfaces per-turn audio separately.

    rec = Recording(
        user_id=conv.user_id,
        topic_id=conv.topic_id,
        target_level=conv.target_level or "B2",
        audio_path=first_audio or f"conversation:{conv.id}",
        duration_seconds=total_duration,
        transcript=combined_transcript,
        word_count=word_count,
        stt_confidence=0.0,
        low_confidence_words=json.dumps(low_conf, ensure_ascii=False),
        tache_mode=conv.tache_mode,
        status="done",
        fluency=(
            json.dumps({"score": fluency_score}, ensure_ascii=False)
            if fluency_score is not None
            else ""
        ),
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    # Persist Feedback using the same field set the recordings router uses.
    carte = analysis.get("la_carte", {}) or {}
    goulet = analysis.get("le_goulet", {}) or {}
    par_couche = analysis.get("analyse_par_couche", {}) or {}
    prononciation = analysis.get("prononciation", {}) or {}
    profile_eval = analysis.get("exam_profile", {}) or {}
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

    weighted_overall = compute_weighted_note_globale(
        conv.tache_mode, carte, fluency_score
    )
    analysis["note_globale"] = weighted_overall
    analysis["overall_score"] = weighted_overall

    feedback = Feedback(
        recording_id=rec.id,
        note_globale=weighted_overall,
        score_le_fond=carte.get("le_fond", 0) or 0,
        score_les_moules_des_idees=carte.get("les_moules_des_idees", 0) or 0,
        score_les_moules=carte.get("les_moules", 0) or 0,
        score_les_reflexes_anglais=carte.get("les_reflexes_anglais", 0) or 0,
        score_prononciation=prononciation.get("score", 0) or 0,
        prononciation_data=json.dumps(prononciation, ensure_ascii=False),
        goulet_couche=goulet.get("couche", 0) or 0,
        goulet_nom=goulet.get("nom", "") or "",
        goulet_explication=goulet.get("explication", "") or "",
        ce_qui_marche=analysis.get("ce_qui_marche", "") or "",
        analyse_le_fond=par_couche.get("le_fond", "") or "",
        analyse_les_moules_des_idees=par_couche.get("les_moules_des_idees", "") or "",
        analyse_les_moules=par_couche.get("les_moules", "") or "",
        analyse_les_reflexes_anglais=par_couche.get("les_reflexes_anglais", "") or "",
        la_prochaine_etape=next_step_value or "",
        transcription_corrigee=analysis.get("transcription_corrigee", "") or "",
        patterns_detectes=json.dumps(analysis.get("patterns_detectes", []), ensure_ascii=False),
        patterns_manquants=json.dumps(analysis.get("patterns_manquants", []), ensure_ascii=False),
        reflexes_detectes=json.dumps(analysis.get("reflexes_detectes", []), ensure_ascii=False),
        corrections=json.dumps(analysis.get("corrections", []), ensure_ascii=False),
        ordonnance=json.dumps(analysis.get("ordonnance", {}), ensure_ascii=False),
        raw_llm_response=analysis.get("raw_response", ""),
        criteria_breakdown=json.dumps(profile_eval, ensure_ascii=False),
        cefr_level=profile_eval.get("cefr_level", "") or "",
        clb_level=profile_eval.get("secondary_framework_value"),
        exam_profile=conv.exam_profile or "tcf_canada",
        examiner_remarks=json.dumps(examiner_map, ensure_ascii=False),
        teacher_coaching=json.dumps(coaching_map, ensure_ascii=False),
        feedback_grid=json.dumps(par_couche, ensure_ascii=False),
        overall_score=weighted_overall,
        analysis_text=analysis.get("ce_qui_marche", "") or "",
    )
    db.add(feedback)

    # Hang the per-mode block (tache_1 / tache_2) inside feedback_grid —
    # the cleanest pre-existing JSON column to extend without another
    # migration. Stored under a distinct key per mode so the two blocks
    # can coexist without stomping on the 2x2 grid cells.
    try:
        grid = json.loads(feedback.feedback_grid) if feedback.feedback_grid else {}
    except json.JSONDecodeError:
        grid = {}
    if isinstance(grid, dict):
        if analysis.get("tache_1"):
            grid["tache_1"] = analysis["tache_1"]
        if analysis.get("tache_2"):
            grid["tache_2"] = analysis["tache_2"]
        feedback.feedback_grid = json.dumps(grid, ensure_ascii=False)

    conv.recording_id = rec.id
    conv.status = "completed"
    conv.completed_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(rec)

    # F-080b: persist module detections AFTER the Recording row is
    # committed (so the FK target exists). Hallucinated module_ids and
    # malformed entries are dropped with WARNING logs by the helper —
    # the helper never raises, so this is safe to call without a
    # try/except. Empty detected_modules list is logged as INFO and
    # produces zero rows.
    try:
        persist_detected_modules(
            recording_id=rec.id,
            detected_modules=analysis.get("detected_modules") or [],
            primary_module_id=analysis.get("primary_module"),
            db=db,
        )
    except Exception as exc:
        # Defensive belt-and-braces: detection persistence must not
        # crash session finalization. Log loudly and let /end return
        # the recording_id so the user still lands on /diagnostic.
        logger.exception(
            "F-080b: persist_detected_modules raised on recording_id=%s "
            "(%s); session finalize continues.",
            rec.id,
            exc,
        )

    return rec


# ═══════════════════════════════════════════════════════════════
# Request models
# ═══════════════════════════════════════════════════════════════

class StartConversationRequest(BaseModel):
    tache_mode: str
    topic_id: int | None = None
    # F-049: required when tache_mode == "tache_2"; ignored otherwise.
    scenario_code: str | None = None
    target_level: str = "B2"
    ui_language: str = "en"
    exam_profile: str = "tcf_canada"


# ═══════════════════════════════════════════════════════════════
# Endpoints
# ═══════════════════════════════════════════════════════════════

@router.get("/scenarios")
async def list_scenarios(
    ui_language: str = "en",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """F-049 — return the Tâche 2 scenarios the user is gated into.

    ``is_above_a2`` currently returns False (F-053 wires the gate), so
    today this only returns A2_B1 scenarios. UI still renders a
    "locked" hint for higher-difficulty rows if Chadi wants to preview
    them; for now we just don't send the locked ones.
    """
    rows = _scenarios_for_user(db, user)
    return {
        "scenarios": [_serialize_scenario(r, ui_language) for r in rows],
        "gates": {"above_a2": _is_above_a2(user, db)},
    }


@router.post("/start")
async def start_conversation(
    req: StartConversationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a conversation. For Tâche 1 the examiner opens; for
    Tâche 2 the candidate opens, so no examiner turn is generated
    here."""
    mode = (req.tache_mode or "").strip()
    if mode not in _CONVERSATION_MODES:
        if not is_valid_mode(mode):
            raise HTTPException(
                400,
                f"Invalid tache_mode '{mode}'. Allowed for conversations: "
                + ", ".join(_CONVERSATION_MODES),
            )
        raise HTTPException(
            400,
            f"tache_mode '{mode}' has no conversation engine yet. "
            f"Allowed: {', '.join(_CONVERSATION_MODES)}",
        )

    topic_id = req.topic_id if req.topic_id else None
    if topic_id:
        exists = db.query(TestTopic).filter(TestTopic.id == topic_id).first()
        if not exists:
            topic_id = None  # fail open: topic is optional for Tâche 1

    scenario = None
    scenario_id = None
    if mode == "tache_2":
        code = (req.scenario_code or "").strip()
        if not code:
            raise HTTPException(400, "scenario_code is required when tache_mode='tache_2'")
        scenario = (
            db.query(Tache2Scenario)
            .filter(Tache2Scenario.code == code, Tache2Scenario.is_active == True)  # noqa: E712
            .first()
        )
        if not scenario:
            raise HTTPException(404, f"Unknown or inactive scenario_code '{code}'")
        # Raccourci gate — keep the check even for direct API callers so
        # the stub can't be bypassed by crafting requests by hand.
        if (scenario.difficulty or "A2_B1") != "A2_B1" and not _is_above_a2(user, db):
            raise HTTPException(
                403,
                f"Scenario '{code}' requires above-A2 progression (gated by F-053).",
            )
        scenario_id = scenario.id

    conv = Conversation(
        id=str(uuid.uuid4()),
        user_id=user.id,
        tache_mode=mode,
        topic_id=topic_id,
        scenario_id=scenario_id,
        target_level=req.target_level or "B2",
        ui_language=req.ui_language or "en",
        exam_profile=req.exam_profile or "tcf_canada",
        status="in_progress",
        started_at=datetime.datetime.utcnow(),
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)

    opening: ConversationTurn | None = None
    if mode == "tache_1":
        # Opening turn — deterministic random pick, no API call.
        opening = await _append_examiner_turn(conv, db)
    # For Tâche 2 the candidate speaks first; no examiner turn yet.

    response: dict = {
        "conversation_id": conv.id,
        "examiner_turn_text": opening.text if opening else None,
        # F-052: populated when TTS succeeded; None means text-only fallback.
        "examiner_turn_audio_url": opening.audio_url if opening else None,
        "turn_number": opening.turn_number if opening else None,
        "conversation_status": conv.status,
        "tache_mode": mode,
    }
    if mode == "tache_1":
        response["max_candidate_turns"] = T1_MAX_CANDIDATE_TURNS
        response["min_candidate_turns"] = T1_MIN_CANDIDATE_TURNS
    else:
        response["max_candidate_turns_hard"] = T2_MAX_CANDIDATE_TURNS_HARD
        response["max_candidate_turns_hint"] = T2_MAX_CANDIDATE_TURNS_HINT
        response["scenario"] = _serialize_scenario(scenario, req.ui_language) if scenario else None
    return response


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Hydrate conversation state. Used for page refresh resume."""
    conv = _require_owner(db, conversation_id, user)
    return _serialize_conversation(conv)


@router.post("/{conversation_id}/turn")
async def append_turn(
    conversation_id: str,
    audio: UploadFile | None = File(default=None),
    transcript: str | None = Form(default=None),
    audio_url: str | None = Form(default=None),
    # F-050: optional client-measured STT metadata — used when the client
    # already hit /api/audio/upload and has fluency + confidence numbers
    # it would otherwise force us to recompute.
    stt_confidence_form: float | None = Form(default=None, alias="stt_confidence"),
    fluency_payload: str | None = Form(default=None, alias="fluency"),
    duration_seconds: float = Form(default=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Accept a candidate turn. Two input shapes:

    - F-048 path (Tâche 1, tap-to-record): send ``audio`` as multipart.
      The server stores it and runs STT before appending.
    - F-050 path (Tâche 2 PTT + review): the client already called
      ``/api/audio/upload`` to get a transcript + audio_url, then
      posts ``transcript`` (+ ``audio_url``) here so the server skips
      a second STT roundtrip.

    Validation:
    - If both ``audio`` and ``transcript`` arrive, prefer ``transcript``
      (don't re-run STT the client already paid for).
    - If neither arrives, 400.
    """
    conv = _require_owner(db, conversation_id, user)
    if conv.status != "in_progress":
        raise HTTPException(400, f"Conversation is {conv.status}; cannot add turns")

    use_prerendered = bool(transcript and transcript.strip())
    has_audio = bool(audio and audio.filename)
    if not use_prerendered and not has_audio:
        raise HTTPException(400, "Provide either an audio file or a transcript.")

    stt_confidence: float = 0.0
    fluency_json: str = ""
    low_conf_words: list = []
    turn_transcript: str = ""
    turn_audio_path: str | None = None

    if use_prerendered:
        turn_transcript = transcript.strip()
        # audio_url is optional on this path — if the client uploaded
        # audio separately it passes it through; otherwise the turn
        # carries text only.
        turn_audio_path = (audio_url or "").strip() or None
        if stt_confidence_form is not None:
            stt_confidence = float(stt_confidence_form)
        if fluency_payload:
            # Accept either raw JSON or a URL-safe opaque blob; we
            # persist whatever the client sent as long as it round-trips
            # back through json.loads.
            try:
                parsed = json.loads(fluency_payload)
                if isinstance(parsed, dict):
                    fluency_json = fluency_payload
                    low_conf_words = parsed.get("low_confidence_words", []) or []
            except (json.JSONDecodeError, TypeError):
                logger.warning(
                    "F-050 fluency payload was not valid JSON; ignoring."
                )
    else:
        # Legacy F-048 path: multipart audio, server-side STT.
        assert audio is not None  # narrowed by has_audio
        ext = (audio.filename or "clip.webm").split(".")[-1]
        filename = f"{uuid.uuid4()}.{ext}"
        filepath = os.path.join(settings.UPLOAD_DIR, filename)
        content = await audio.read()
        with open(filepath, "wb") as f:
            f.write(content)
        turn_audio_path = filepath

        try:
            stt_result = await transcribe_audio(filepath)
        except Exception as exc:
            logger.exception("F-048 STT failed for conversation %s", conv.id)
            raise HTTPException(500, f"Transcription failed: {exc}")

        turn_transcript = stt_result.get("transcript", "") or ""
        stt_confidence = stt_result.get("confidence", 0.0)
        fluency_data = compute_fluency(
            stt_result, recording_duration_sec=duration_seconds or None
        )
        if fluency_data is not None:
            # Stash low_confidence_words on the fluency payload so the
            # completion step can aggregate them without a second column.
            fluency_data["low_confidence_words"] = stt_result.get("low_confidence_words", [])
            fluency_json = json.dumps(fluency_data, ensure_ascii=False)
            low_conf_words = fluency_data["low_confidence_words"]

    candidate_turn = ConversationTurn(
        conversation_id=conv.id,
        turn_number=len(conv.turns),
        speaker="candidate",
        text=turn_transcript,
        audio_url=turn_audio_path,
        stt_confidence=stt_confidence,
        word_count=len(turn_transcript.split()) if turn_transcript else 0,
        fluency=fluency_json,
    )
    db.add(candidate_turn)
    db.commit()
    db.refresh(conv)

    # Per-mode hard cap. T1 auto-ends at its 4-turn max; T2 auto-ends
    # at its 12-turn hard cap and flips a wrap_up_hint after the
    # 8-turn soft cap so the UI can nudge the candidate.
    # F-062.3: count active (non-superseded) candidate turns only. A user
    # who re-records 3 times and then commits 6 shouldn't hit a 9-of-12
    # wrap_up_hint from this tighter cap — retakes don't count.
    candidate_count = len(_candidate_turns(conv))
    if conv.tache_mode == "tache_1":
        hard_cap = T1_MAX_CANDIDATE_TURNS
        soft_cap = T1_MAX_CANDIDATE_TURNS  # T1 has no distinct soft cap
    else:
        hard_cap = T2_MAX_CANDIDATE_TURNS_HARD
        soft_cap = T2_MAX_CANDIDATE_TURNS_HINT

    if candidate_count >= hard_cap:
        rec = await _run_conversation_analysis_and_persist(conv, db)
        return {
            "candidate_transcript": turn_transcript,
            # F-062.3: the candidate's own turn_number — frontend uses this
            # to know what row to call /supersede on if the user rejects the
            # transcript. Always present; null only in impossible states.
            "candidate_turn_number": candidate_turn.turn_number,
            "examiner_turn_text": None,
            "examiner_turn_audio_url": None,
            "examiner_turn_number": None,
            "conversation_status": conv.status,
            "recording_id": rec.id,
            "auto_ended": True,
            "wrap_up_hint": False,
        }

    # Otherwise — ask Claude for the next examiner turn.
    examiner_turn = await _append_examiner_turn(conv, db)
    wrap_up_hint = (
        conv.tache_mode == "tache_2" and candidate_count >= soft_cap
    )
    return {
        "candidate_transcript": turn_transcript,
        "candidate_turn_number": candidate_turn.turn_number,
        "examiner_turn_text": examiner_turn.text if examiner_turn else None,
        # F-052: None when TTS is unavailable (missing key, rate-limit, etc.)
        # — the client renders text-only with a "voice unavailable" note.
        "examiner_turn_audio_url": examiner_turn.audio_url if examiner_turn else None,
        "examiner_turn_number": examiner_turn.turn_number if examiner_turn else None,
        "conversation_status": conv.status,
        "recording_id": None,
        "auto_ended": False,
        "wrap_up_hint": wrap_up_hint,
    }


@router.post("/{conversation_id}/turn/{turn_number}/supersede")
async def supersede_turn(
    conversation_id: str,
    turn_number: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """F-062.3: mark a candidate turn as superseded so the candidate can
    re-record it. The row stays in the DB for audit; /end filters active
    turns only. Audio file is NOT deleted — cleanup is a future async job.

    Cascade: also supersedes the immediately-following examiner turn at
    turn_number + 1 if it exists and is active. That examiner reply was
    generated in response to the now-rejected candidate transcript, so it
    would be contextually stale if kept.

    Idempotent: calling /supersede twice on the same turn returns the
    original superseded_at; not an error.

    403 if the caller doesn't own the conversation.
    404 if the turn_number doesn't exist for this conversation.
    400 if the target is an examiner turn (candidate-only flow).
    400 if the conversation isn't in_progress (can't edit a completed one).
    """
    conv = _require_owner(db, conversation_id, user)
    if conv.status != "in_progress":
        raise HTTPException(
            400, f"Conversation is {conv.status}; cannot supersede turns"
        )

    target = next(
        (t for t in conv.turns if t.turn_number == turn_number),
        None,
    )
    if target is None:
        raise HTTPException(404, f"No turn at position {turn_number}")
    if target.speaker != "candidate":
        raise HTTPException(
            400,
            f"Turn {turn_number} is an examiner turn; only candidate turns "
            "can be superseded by the re-record flow",
        )

    # Idempotent: if already superseded, return the existing state.
    if target.superseded_at is not None:
        return {
            "superseded_turn_id": target.id,
            "superseded_turn_number": target.turn_number,
            "superseded_at": target.superseded_at.isoformat(),
            "cascaded_examiner_turn_numbers": [],
            "status": "superseded",
        }

    now = datetime.datetime.utcnow()
    target.superseded_at = now

    # Cascade to the immediately-following examiner turn, if any. Candidate
    # turn N is typically followed by examiner turn N+1 (generated inside
    # /turn). If the candidate is retaking turn N, that examiner reply was
    # responding to the rejected transcript and should not feed forward.
    cascaded: list[int] = []
    follower = next(
        (t for t in conv.turns if t.turn_number == turn_number + 1),
        None,
    )
    if (
        follower is not None
        and follower.speaker == "examiner"
        and follower.superseded_at is None
    ):
        follower.superseded_at = now
        cascaded.append(follower.turn_number)

    db.commit()
    db.refresh(target)

    return {
        "superseded_turn_id": target.id,
        "superseded_turn_number": target.turn_number,
        "superseded_at": target.superseded_at.isoformat(),
        "cascaded_examiner_turn_numbers": cascaded,
        "status": "superseded",
    }


@router.post("/{conversation_id}/end")
async def end_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Manual end — user pressed 'Terminer la conversation'. Requires at
    least one candidate turn; under MIN_CANDIDATE_TURNS the analysis
    still runs but the response flags it so the UI can warn."""
    conv = _require_owner(db, conversation_id, user)
    if conv.status == "completed":
        # Idempotent: if they double-click the button, return the same id.
        return {
            "conversation_status": conv.status,
            "recording_id": conv.recording_id,
            "under_min_turns": False,
        }
    if conv.status == "abandoned":
        raise HTTPException(400, "Conversation was abandoned")

    # F-062.3: same filter as /turn — superseded retakes don't count.
    candidate_count = len(_candidate_turns(conv))
    if candidate_count == 0:
        # Nothing to analyze. Mark abandoned so we don't leak
        # half-started conversations into history.
        conv.status = "abandoned"
        conv.completed_at = datetime.datetime.utcnow()
        db.commit()
        return {
            "conversation_status": conv.status,
            "recording_id": None,
            "under_min_turns": True,
        }

    rec = await _run_conversation_analysis_and_persist(conv, db)
    # Tâche 1 has a soft floor (min turns) so we can warn on the UI when
    # results are directional. Tâche 2 has no analogous floor — any
    # candidate-driven exchange with ≥1 turn is worth analyzing.
    if conv.tache_mode == "tache_1":
        under_min = candidate_count < T1_MIN_CANDIDATE_TURNS
    else:
        under_min = False
    return {
        "conversation_status": conv.status,
        "recording_id": rec.id,
        "under_min_turns": under_min,
    }
