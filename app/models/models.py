import datetime
from sqlalchemy import Column, Integer, String, Text, Float, Date, DateTime, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), default="")
    # UI language ("en" / "es"). Frontend onboarding sends this as
    # `interface_language` in the POST /api/users/onboarding payload — same
    # concept, preserved here as ui_language to avoid duplicating columns.
    ui_language = Column(String(5), default="en")
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # F-060: onboarding persistence. All nullable — existing users who signed
    # up pre-onboarding leave these empty until they complete the flow.
    target_level = Column(String(10), nullable=True)        # "C1", "B2", "CLB 7", ...
    exam_profile = Column(String(50), nullable=True)        # "tcf_canada" | "tcf_general" | "tef" | "delf"
    exam_date = Column(Date, nullable=True)                 # null when user picked a quick bucket
    goal = Column(String(100), nullable=True)               # "immigration" | "studies" | "general"
    current_level = Column(String(20), nullable=True)       # self-reported CEFR band

    recordings = relationship("Recording", back_populates="user")


class Recording(Base):
    __tablename__ = "recordings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("test_topics.id"), nullable=True)
    target_level = Column(String(10), default="B2")
    audio_path = Column(String(500), nullable=False)
    duration_seconds = Column(Float, default=0)
    transcript = Column(Text, default="")
    word_count = Column(Integer, default=0)
    stt_confidence = Column(Float, default=0)
    low_confidence_words = Column(Text, default="[]")  # JSON array
    argument_structure = Column(Text, default="")  # AI-generated scaffold from Argument Assistant
    # F-002: student-confirmed transcript (may equal original if they clicked
    # "Use it anyway"). Empty for legacy rows / old /upload path.
    corrected_transcript = Column(Text, default="")
    # True when the student went through the correction loop (either edited
    # or confirmed "Use it anyway"). False for legacy and old /upload path.
    transcript_confirmed = Column(Boolean, default=False)
    # F-038: fluency assessment (JSON). Populated from STT word-level timing.
    # NULL for writing submissions and any recording that predates F-038.
    fluency = Column(Text, default="")
    # F-047: Tâche mode — "tache_1" | "tache_2" | "tache_3" | "writing" | "legacy".
    # Required on new inserts (enforced at router layer). Backfilled to "legacy"
    # for rows that predate per-Tâche routing. No default here on purpose —
    # callers must be explicit.
    tache_mode = Column(String(20), nullable=True)
    status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="recordings")
    topic = relationship("TestTopic")
    feedback = relationship("Feedback", back_populates="recording", uselist=False)


class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    recording_id = Column(Integer, ForeignKey("recordings.id"), nullable=False)

    # ── La Carte (4 couches × 0-5) ────────────────────────────
    note_globale = Column(Float, default=0)
    score_le_fond = Column(Float, default=0)
    score_les_moules_des_idees = Column(Float, default=0)
    score_les_moules = Column(Float, default=0)
    score_les_reflexes_anglais = Column(Float, default=0)

    # ── Prononciation ──────────────────────────────────────────
    score_prononciation = Column(Float, default=0)
    prononciation_data = Column(Text, default="{}")  # JSON

    # ── Le Goulet ──────────────────────────────────────────────
    goulet_couche = Column(Integer, default=0)
    goulet_nom = Column(String(50), default="")
    goulet_explication = Column(Text, default="")

    # ── Diagnostic text (bilingual, |||) ───────────────────────
    ce_qui_marche = Column(Text, default="")
    analyse_le_fond = Column(Text, default="")
    analyse_les_moules_des_idees = Column(Text, default="")
    analyse_les_moules = Column(Text, default="")
    analyse_les_reflexes_anglais = Column(Text, default="")
    la_prochaine_etape = Column(Text, default="")

    # ── Corrected transcription ────────────────────────────────
    transcription_corrigee = Column(Text, default="")

    # ── Patterns & Réflexes (JSON) ─────────────────────────────
    patterns_detectes = Column(Text, default="[]")
    patterns_manquants = Column(Text, default="[]")
    reflexes_detectes = Column(Text, default="[]")

    # ── Corrections & Ordonnance (JSON) ────────────────────────
    corrections = Column(Text, default="[]")
    ordonnance = Column(Text, default="{}")

    # ── Raw ────────────────────────────────────────────────────
    raw_llm_response = Column(Text, default="")

    # ── TCF Canada (or other exam profile) five-criterion scoring ──
    # JSON: [{criterion_key, score, feedback}, ...] for the active profile.
    criteria_breakdown = Column(Text, default="")
    cefr_level = Column(String(20), default="")  # "B2", "A1 not achieved", ...
    clb_level = Column(Integer, nullable=True)   # IRCC CLB (None if n/a)
    exam_profile = Column(String(50), default="tcf_canada")

    # ── Dual-channel feedback (F-032) ──────────────────────────
    # Redundant with criteria_breakdown (which also embeds these keyed
    # rows) but kept as dedicated columns for SQL-level inspection and
    # to make it cheap to query "did this voice generation succeed".
    examiner_remarks = Column(Text, default="{}")  # JSON: {criterion_key: "FR remark"}
    teacher_coaching = Column(Text, default="{}")  # JSON: {criterion_key: {coaching_en, coaching_fr, transformation}}
    feedback_grid = Column(Text, default="{}")     # JSON: {what_works, what_doesnt_work, english_habits, structure_quality}

    # ── Backward compat ────────────────────────────────────────
    # note_globale above is the LEGACY 4-couche holistic score; the new
    # profile-driven overall lives in criteria_breakdown (+ cefr/clb_level).
    # overall_score here mirrors note_globale for legacy consumers.
    overall_score = Column(Float, default=0)
    analysis_text = Column(Text, default="")

    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    recording = relationship("Recording", back_populates="feedback")


class TestTopic(Base):
    __tablename__ = "test_topics"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    theme = Column(String(100), default="")
    sous_theme = Column(String(200), default="")
    # F-051: Tâche 3 specific metadata. Formal prompt phrasing (one per
    # UI language), plus a difficulty tag mirroring the Tâche 2 scenario
    # gate. Columns are nullable because the legacy topic set predates
    # Tâche 3 routing; rows without a ``tache_3_prompt_fr`` are skipped
    # by the Tâche 3 picker.
    tache_3_prompt_fr = Column(Text, default="")
    tache_3_prompt_en = Column(Text, default="")
    tache_3_prompt_es = Column(Text, default="")
    # A2_B1 | B1_B2 | B2_C1 — gates by L'École progression (F-053).
    tache_3_difficulty = Column(String(10), default="B1_B2")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


# ───────────────────────────────────────────────────────────────
# F-048 — multi-turn conversation state (Tâche 1, later Tâche 2).
# A conversation is created when the candidate starts a Tâche 1 session;
# it accumulates alternating examiner + candidate turns, then on
# completion links to a Recording row that holds the aggregated
# analysis/Feedback via the existing Recording→Feedback relationship.
# ───────────────────────────────────────────────────────────────

class Conversation(Base):
    __tablename__ = "conversations"

    # UUID string primary key so clients can start a conversation and
    # pass the id around without guessing an auto-increment value.
    id = Column(String(36), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # Denormalized so we can query "all tache_1 conversations for user X"
    # without joining Recording. Values mirror Recording.tache_mode.
    tache_mode = Column(String(20), nullable=False)
    topic_id = Column(Integer, ForeignKey("test_topics.id"), nullable=True)
    target_level = Column(String(10), default="B2")
    ui_language = Column(String(5), default="en")
    exam_profile = Column(String(50), default="tcf_canada")
    # in_progress | completed | abandoned
    status = Column(String(20), default="in_progress", index=True)
    # Populated when status flips to completed and the aggregated
    # Recording + Feedback rows are created.
    recording_id = Column(Integer, ForeignKey("recordings.id"), nullable=True)
    # F-049: link to Tache2Scenario when tache_mode == "tache_2".
    # Nullable because tache_1 doesn't use scenarios.
    scenario_id = Column(Integer, ForeignKey("tache2_scenarios.id"), nullable=True)
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    turns = relationship(
        "ConversationTurn",
        back_populates="conversation",
        order_by="ConversationTurn.turn_number",
        cascade="all, delete-orphan",
    )
    recording = relationship("Recording")
    topic = relationship("TestTopic")
    scenario = relationship("Tache2Scenario")


class ConversationTurn(Base):
    __tablename__ = "conversation_turns"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(
        String(36), ForeignKey("conversations.id"), nullable=False, index=True
    )
    # 0-indexed. Examiner opens at turn 0, candidate replies at turn 1, etc.
    # Monotonic across supersedes — a re-recorded turn gets a NEW turn_number;
    # the superseded row keeps its original number.
    turn_number = Column(Integer, nullable=False)
    # "examiner" | "candidate"
    speaker = Column(String(20), nullable=False)
    text = Column(Text, default="")
    # Candidate turns store the uploaded audio path; examiner turns leave
    # this NULL until F-052 wires TTS.
    audio_url = Column(String(500), nullable=True)
    # Per-turn STT + fluency, captured so the aggregated analyzer can
    # reason about pacing and elaboration without re-running STT.
    stt_confidence = Column(Float, nullable=True)
    word_count = Column(Integer, default=0)
    # JSON — shape matches the payload from app.services.fluency.compute_fluency.
    fluency = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    # F-062.3 supersede tracking. NULL = active turn. When the candidate
    # re-records (Refaire cette prise), the frontend calls /supersede on the
    # bad turn and the row's superseded_at flips to now(). /end analysis
    # filters these out. superseded_by_turn_id is a soft pointer to the
    # replacement row — set after the replacement is committed; self-FK not
    # enforced at the DB layer (SQLite can't add FK via ALTER COLUMN).
    superseded_at = Column(DateTime, nullable=True, index=True)
    superseded_by_turn_id = Column(Integer, nullable=True)

    conversation = relationship("Conversation", back_populates="turns")


# ───────────────────────────────────────────────────────────────
# F-063 — Tâche 1 opening prompt catalog.
# Unlike Tâche 2 (role-play with distinct personas), Tâche 1 is always the
# same "tell me about yourself" interview — only the examiner's opening
# phrasing varies so sessions don't feel canned. Rows are picked at random
# at conversation /start time; the rest of the interview is driven by the
# examiner persona in app/services/personas/tache_1_examiner.
# ───────────────────────────────────────────────────────────────

class Tache1Opening(Base):
    __tablename__ = "tache1_openings"

    id = Column(Integer, primary_key=True, index=True)
    # Examiner's actual spoken line — always French. EN/ES columns mirror
    # the Tâche 2 scenario table's multi-language pattern; kept available
    # for any future bilingual-subtitle display. Examiner TTS synthesis
    # only reads the _fr column.
    opening_prompt_fr = Column(Text, nullable=False)
    opening_prompt_en = Column(Text, default="")
    opening_prompt_es = Column(Text, default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


# ───────────────────────────────────────────────────────────────
# F-080a — Remediation module library.
# Named L1-interference modules that Claude's analysis engine tags
# sessions against. The full ticket spec lives in BACKLOG.md under
# "F-080 — Module Library + Intelligence Layer"; authoritative schema
# lives in app/schemas/modules.py (pydantic) + scripts/add_remediation_modules.py
# (DDL with CHECK constraints the ORM can't express on SQLite).
#
# JSON-blob TEXT columns (detection_criteria, examples, content_refs,
# drill_ids, prerequisite_module_ids) are parsed at the pydantic layer —
# we don't use SQLAlchemy hybrid_property here because every read path
# that needs the structured shape goes through the pydantic response
# model already (CRUD endpoints, seeder, analysis prompt builder).
# ───────────────────────────────────────────────────────────────

class RemediationModule(Base):
    __tablename__ = "remediation_modules"

    id = Column(String(64), primary_key=True, index=True)
    name_fr = Column(String(200), nullable=False)
    name_en = Column(String(200), nullable=False)
    # Category and severity CHECK constraints are declared in the migration
    # DDL, not here — SQLAlchemy's portable CheckConstraint doesn't map
    # cleanly to SQLite's IN(...) form. The seeder validates via pydantic
    # before insert, so an out-of-range value can only slip in via a raw
    # INSERT that bypasses both layers.
    category = Column(String(40), nullable=False)
    severity = Column(Integer, nullable=False)
    active = Column(Boolean, nullable=False, default=True)

    L1_interference_description_fr = Column(Text, nullable=False)
    L1_interference_description_en = Column(Text, nullable=False)

    detection_criteria = Column(Text, nullable=False)          # JSON object
    examples = Column(Text, nullable=False)                    # JSON array
    content_refs = Column(Text, nullable=False, default="[]")  # JSON array
    drill_ids = Column(Text, nullable=False, default="[]")     # JSON array of int
    prerequisite_module_ids = Column(Text, nullable=False, default="[]")  # JSON array of str

    # Optional canonical École lesson this module maps to. Most
    # modules leave this null — modules and École lessons are
    # independent bodies of content. When set, the F-080d École tab
    # shows a "Your gap" badge on that lesson.
    ecole_lesson_id = Column(
        Integer, ForeignKey("ecole_lessons.id"), nullable=True
    )

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)

    ecole_lesson = relationship("EcoleLesson")


class SessionDetectedModule(Base):
    __tablename__ = "session_detected_modules"

    id = Column(Integer, primary_key=True, index=True)
    recording_id = Column(
        Integer, ForeignKey("recordings.id"), nullable=False, index=True
    )
    module_id = Column(
        String(64), ForeignKey("remediation_modules.id"), nullable=False, index=True
    )
    # Exactly one row per recording should have is_primary=1. Enforced at
    # the insert site in the /end handler (F-080b), not at the DB layer —
    # SQLite partial unique indexes on "one row per recording where
    # is_primary=1" are supported but add complexity the analyzer already
    # guarantees.
    is_primary = Column(Boolean, nullable=False, default=False)
    confidence_score = Column(Float, nullable=True)
    supporting_quote = Column(Text, nullable=True)
    detected_at = Column(DateTime, default=datetime.datetime.utcnow)

    recording = relationship("Recording")
    module = relationship("RemediationModule")


# ───────────────────────────────────────────────────────────────
# F-049 — Tâche 2 scenario catalog.
# Each row is a role-play situation (agence de voyages, déménagement, etc.).
# The examiner's persona + data targets are authored by Chadi and plug
# into the Tâche 2 examiner prompt at runtime.
# ───────────────────────────────────────────────────────────────

class Tache2Scenario(Base):
    __tablename__ = "tache2_scenarios"

    id = Column(Integer, primary_key=True, index=True)
    # Stable identifier the seed script + router look up by.
    code = Column(String(64), unique=True, nullable=False, index=True)
    # Display titles per UI language.
    title_fr = Column(String(200), default="")
    title_en = Column(String(200), default="")
    title_es = Column(String(200), default="")
    # The brief shown to the candidate before they start recording —
    # who they are, what they're trying to find out. 3-5 sentences in
    # each language.
    candidate_brief_fr = Column(Text, default="")
    candidate_brief_en = Column(Text, default="")
    candidate_brief_es = Column(Text, default="")
    # Free-form persona description spliced into the examiner system
    # prompt (see app.services.personas.tache_2_examiner.build_persona).
    # Each scenario's examiner is a different character.
    examiner_persona = Column(Text, default="")
    # JSON-encoded list of data points the candidate is expected to
    # extract during the conversation. Used by the Yarden analyzer to
    # score completeness and by the "targets hit/missed" feedback block.
    data_targets = Column(Text, default="[]")
    # formel | semi_formel | informel — drives tu/vous + tone in the
    # examiner prompt.
    register = Column(String(20), default="formel")
    # A2_B1 | B1_B2 | B2_C1 — gates per L'École progression
    # (F-053 wires the actual gate; this field is the source of truth).
    difficulty = Column(String(10), default="A2_B1")
    # Provenance so Chadi can track which Yarden doc a scenario came from.
    seeded_from = Column(String(120), default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


# ───────────────────────────────────────────────────────────────
# F-053 — L'École (named curriculum for anglophone learners).
# 16 locked lessons. Completion of all 16 unlocks "above A2" gating
# that the rest of the app uses to filter advanced content (Tâche 2
# scenarios, Tâche 3 prompts). Vocabulary path is a separate future
# module and lives outside L'École.
# ───────────────────────────────────────────────────────────────

class EcoleLesson(Base):
    __tablename__ = "ecole_lessons"

    id = Column(Integer, primary_key=True, index=True)
    # 1-27 in the locked sequence (16 in Phase 1 Fondations + 11 in
    # Phase 2 Approfondissement, per F-087). Unique so the seeder's
    # ordering is a proper key, and so `prerequisite_lesson_number`
    # FK-by-convention can point at it.
    lesson_number = Column(Integer, unique=True, nullable=False, index=True)
    # Stable slug. Preferred over the integer in URLs and analytics.
    code = Column(String(64), unique=True, nullable=False, index=True)
    title_fr = Column(String(200), default="")
    title_en = Column(String(200), default="")
    title_es = Column(String(200), default="")
    # Home-screen / lesson-card copy (2-3 sentences).
    short_description_fr = Column(Text, default="")
    short_description_en = Column(Text, default="")
    short_description_es = Column(Text, default="")
    # Full teaching content (markdown-friendly text). EN is deliberately
    # NOT a direct translation of FR — it addresses anglophone-specific
    # confusion points.
    detailed_content_fr = Column(Text, default="")
    detailed_content_en = Column(Text, default="")
    detailed_content_es = Column(Text, nullable=True)
    # null for lesson 1, else lesson_number - 1. Used for both lock
    # checks and for surfacing "you'll need X first" hints.
    prerequisite_lesson_number = Column(Integer, nullable=True)
    estimated_duration_minutes = Column(Integer, default=15)
    is_active = Column(Boolean, default=True)
    # F-087: Phase 1 Fondations (1-16) vs Phase 2 Approfondissement (17-27).
    # Drives the visual separator on the home tab + /ecole list page.
    # Default 1 so legacy rows (pre-F-087) and any manually-inserted row
    # without the column lands as Fondations.
    phase = Column(Integer, default=1)
    # F-087 (rendered by F-089): deadpan English subline shown beneath
    # the lesson title on cards. Authored, not derived. Always populated
    # by the seeder; nullable here only because pre-F-087 rows wouldn't
    # have had it.
    subline_en = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    questions = relationship(
        "EcoleQuizQuestion",
        back_populates="lesson",
        cascade="all, delete-orphan",
        order_by="EcoleQuizQuestion.question_number",
    )


class EcoleQuizQuestion(Base):
    __tablename__ = "ecole_quiz_questions"

    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(
        Integer, ForeignKey("ecole_lessons.id"), nullable=False, index=True
    )
    # 1-10 within a lesson. Enforcing uniqueness per lesson is a
    # nice-to-have; the seeder + router sort by this value.
    question_number = Column(Integer, nullable=False)
    # multiple_choice | fill_blank | translate_en_fr | translate_fr_en |
    # correct_the_sentence
    question_type = Column(String(32), nullable=False)
    question_fr = Column(Text, default="")
    question_en = Column(Text, default="")
    question_es = Column(Text, default="")
    # The canonical accepted answer (French). Alternatives live in the
    # JSON column below.
    correct_answer = Column(Text, default="")
    accepted_alternatives = Column(Text, default="[]")  # JSON list
    explanation_fr = Column(Text, default="")
    explanation_en = Column(Text, default="")
    explanation_es = Column(Text, default="")
    # JSON list, only populated for multiple_choice; otherwise "[]".
    options = Column(Text, default="[]")

    lesson = relationship("EcoleLesson", back_populates="questions")


class UserEcoleProgress(Base):
    __tablename__ = "user_ecole_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "lesson_id", name="uq_user_lesson"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    lesson_id = Column(
        Integer, ForeignKey("ecole_lessons.id"), nullable=False, index=True
    )
    # locked | unlocked | in_progress | completed
    status = Column(String(20), default="locked")
    quiz_attempts = Column(Integer, default=0)
    # Best recorded percentage (0-100). Stays flat across attempts — we
    # don't penalise retries.
    quiz_best_score = Column(Integer, default=0)
    completed_at = Column(DateTime, nullable=True)
    unlocked_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User")
    lesson = relationship("EcoleLesson")
