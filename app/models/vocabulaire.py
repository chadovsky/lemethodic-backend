"""F-320 — ORM models for Le Vocabulaire (content store + personal lists).

Schema lives in alembic migration i7g8h9i0j1k2_f320_vocabulaire_schema.py;
this module is the SQLAlchemy mirror for query-side use.

Convention (mirror of app/models/writing.py + app/models/auth_tokens.py):
the migration is the source of truth for column shapes + CHECK constraints
+ indices; this file declares what the app reads/writes so Base.metadata
stays consistent (autogenerate parity) and routers/services can import
ORM classes without crossing into the migration package.

──────────────────────────────────────────────────────────────────────
Namespace note (F-320 Decision D1, approved 2026-05-12):

`vocab_topics` here is intentionally DISTINCT from the pre-existing
`vocabulary_themes` table (P-202, app/models/models.py:VocabularyTheme).
They are different concepts:

  vocabulary_themes — curriculum-cluster lexical-area tagging. Each
    Cluster row optionally FK's to one. Lifecycle: authored once per
    P-202 seed, mutated only by curriculum revisions.

  vocab_topics — Le Vocabulaire content-browse catalog with corpus
    partition (free_general vs exam_tagged_*). Each VocabChunk FK's
    to one. Lifecycle: grows as F-321 ingest pipeline + Chadi-authored
    artifacts seed new content.

Conflating them would force corpus_partition + cefr_level_min/max onto
curriculum rows and bleed Le Vocabulaire content semantics into
P-202/P-203/P-204 progression code. Keep separate.

──────────────────────────────────────────────────────────────────────
Source-type enum note (F-320 Decision D2, approved 2026-05-12):

`source_type` values inherit from the parent F-330 ticket:
  CC_corpus | chadi_authored | book_lab | third_party_publisher_DO_NOT_EXTRACT

The earlier BACKLOG.md F-320 sub-entry text (`oqlf | academie | curated`)
predates F-312 Path C lock-in and is corrected to match the parent
ticket in the same commit as this migration.

Rows tagged `third_party_publisher_DO_NOT_EXTRACT` are corpus
provenance pointers ONLY — never reproduced verbatim in app output,
never embedded for retrieval. The enum value is in the schema so we
can catalogue references without ever serving them.

`source` (free-text URL or docx filename) is a separate column. CC_corpus
rows MUST populate `source` for CC BY-SA attribution at retrieval time;
enforcement lives in the F-321 ingest pipeline, not the DB layer.

──────────────────────────────────────────────────────────────────────
Tier-gate contract (F-320 Decision D12, documented here, enforced at
F-322/F-323 router layer):

  Browse vocab_topics where corpus_partition = 'free_general':
    Depends(get_current_user) — open to all authenticated users.
  Browse vocab_topics where corpus_partition starts with 'exam_tagged_':
    Depends(require_tier("subscription")) — paid surface.
  Personal-list CRUD + progress writes:
    Depends(require_tier("subscription")) — paid surface.

Schema is tier-agnostic; the contract is documented here so router
implementers in F-322/F-323 inherit it without re-deriving.
"""
from __future__ import annotations

import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class VocabTopic(Base):
    """Le Vocabulaire content catalog topic. Browse unit in the FE
    topic picker. Each VocabChunk lives under exactly one topic.

    `corpus_partition` drives tier-gate selection at the router layer
    (see module docstring). Values are NOT NULL; CHECK enforces the
    4-value domain.
    """

    __tablename__ = "vocab_topics"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(80), unique=True, nullable=False, index=True)
    # i18n: {"fr": "...", "en": "...", "es": "..."}
    labels = Column(JSONB, nullable=False, default=dict)
    description = Column(JSONB, nullable=False, default=dict)
    # CHECK enforces: free_general | exam_tagged_TCF | exam_tagged_DELF | exam_tagged_TEF
    corpus_partition = Column(String(40), nullable=False, index=True)
    cefr_level_min = Column(String(10), nullable=True)
    cefr_level_max = Column(String(10), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    chunks = relationship("VocabChunk", back_populates="topic")

    __table_args__ = (
        CheckConstraint(
            "corpus_partition IN ("
            "'free_general', 'exam_tagged_TCF', 'exam_tagged_DELF', 'exam_tagged_TEF'"
            ")",
            name="ck_vocab_topics_corpus_partition",
        ),
    )


class VocabChunk(Base):
    """Le Vocabulaire content unit. A single lexical chunk — word,
    expression, idiom, collocation — with optional EN gloss for
    FR↔EN exercises.

    `source_type` is NOT NULL with the parent-ticket 4-value enum.
    `source` is the URL or docx filename and is nullable so chadi_authored
    rows without a public URL stay clean; CC_corpus ingest enforces
    `source` IS NOT NULL at write-time.

    `exam_tag` is single-string nullable per F-320 MVP scope. Promote
    to JSONB-array or junction-table only if usage shows chunks
    routinely serve multiple exams.

    `register` matches the existing Tache2Scenario.register 3-value set
    plus `argotique` for vocab-specific surface. CHECK enforces.
    """

    __tablename__ = "vocab_chunks"

    id = Column(Integer, primary_key=True, index=True)
    chunk_fr = Column(String(500), nullable=False)
    chunk_en = Column(String(500), nullable=True)
    topic_id = Column(
        Integer, ForeignKey("vocab_topics.id"), nullable=False, index=True
    )
    # Free-text: URL (Wiktionary, Tatoeba) or docx filename (Chadi archive)
    # or book_lab title. NULL only when no provenance pointer exists
    # (chadi_authored MVP entries where the archive file is irrelevant).
    source = Column(String(500), nullable=True)
    # CHECK enforces 4-val: CC_corpus | chadi_authored | book_lab |
    # third_party_publisher_DO_NOT_EXTRACT
    source_type = Column(String(40), nullable=False)
    # CHECK enforces nullable + 4-val: formel | semi_formel | informel | argotique
    register = Column(String(20), nullable=True)
    # CHECK enforces nullable + 4-val: tcf | tef | delf | dalf
    exam_tag = Column(String(20), nullable=True, index=True)
    # CEFR band: A1..C2. Nullable — F-321 ingest may stage rows without
    # leveling; leveling is a follow-up Chadi-curation pass.
    cefr_level = Column(String(10), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    topic = relationship("VocabTopic", back_populates="chunks")

    __table_args__ = (
        CheckConstraint(
            "source_type IN ("
            "'CC_corpus', 'chadi_authored', 'book_lab', "
            "'third_party_publisher_DO_NOT_EXTRACT'"
            ")",
            name="ck_vocab_chunks_source_type",
        ),
        CheckConstraint(
            "register IS NULL "
            "OR register IN ('formel', 'semi_formel', 'informel', 'argotique')",
            name="ck_vocab_chunks_register",
        ),
        CheckConstraint(
            "exam_tag IS NULL "
            "OR exam_tag IN ('tcf', 'tef', 'delf', 'dalf')",
            name="ck_vocab_chunks_exam_tag",
        ),
        # Composite — supports "topic page, filtered by level".
        Index(
            "ix_vocab_chunks_topic_level",
            "topic_id",
            "cefr_level",
        ),
    )


class UserVocabList(Base):
    """Personal vocab list owned by a single user. F-322 surfaces
    CRUD; F-330.lists later adds SRS scheduling on top of this.

    UNIQUE(user_id, name) — a user can't have two lists named "Mon
    TCF". Length cap 120 matches Cluster.grammar_topic.
    """

    __tablename__ = "user_vocab_lists"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(120), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    chunks = relationship(
        "UserVocabListChunk",
        back_populates="list",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_user_vocab_lists_user_name"),
        # "all lists for user X, newest first" — composite serves it as
        # a prefix scan + reverse walk. Same pattern as
        # ix_user_cluster_events_user_created (P-204).
        Index(
            "ix_user_vocab_lists_user_created",
            "user_id",
            "created_at",
        ),
    )


class UserVocabListChunk(Base):
    """Join row: chunk-in-list membership. CASCADE on list deletion
    so dropping a list reclaims its membership rows; CASCADE on
    chunk deletion so admin chunk cleanup doesn't leave dangling
    references."""

    __tablename__ = "user_vocab_list_chunks"

    id = Column(Integer, primary_key=True, index=True)
    list_id = Column(
        Integer,
        ForeignKey("user_vocab_lists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_id = Column(
        Integer,
        ForeignKey("vocab_chunks.id", ondelete="CASCADE"),
        nullable=False,
    )
    added_at = Column(DateTime, default=datetime.datetime.utcnow)

    list = relationship("UserVocabList", back_populates="chunks")
    chunk = relationship("VocabChunk")

    __table_args__ = (
        # A chunk can't appear twice in the same list. Enforced at the
        # DB layer (no app-side dedup needed in F-322 add endpoint).
        UniqueConstraint(
            "list_id", "chunk_id", name="uq_user_vocab_list_chunks_list_chunk"
        ),
        # Admin/analytics: "how many lists contain chunk X". Cheap
        # secondary index; the unique constraint above already covers
        # the (list_id, chunk_id) lookup path.
        Index("ix_user_vocab_list_chunks_chunk", "chunk_id"),
    )


class UserVocabProgress(Base):
    """Per-user-per-chunk practice progress. One row, mutated in
    place. Mirror of UserClusterStatus (P-204) pattern: surrogate
    PK + UNIQUE(user_id, chunk_id) so upserts are simple.

    SRS scheduling columns (next_due_at, box_number) are intentionally
    OUT OF SCOPE in F-320 — they land with F-330.lists. The shape here
    captures the raw signal (seen/correct/last_seen_at) that the SRS
    scheduler will consume."""

    __tablename__ = "user_vocab_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_id = Column(
        Integer,
        ForeignKey("vocab_chunks.id", ondelete="CASCADE"),
        nullable=False,
    )
    seen_count = Column(Integer, nullable=False, default=0)
    correct_count = Column(Integer, nullable=False, default=0)
    last_seen_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "user_id", "chunk_id", name="uq_user_vocab_progress_user_chunk"
        ),
        # "what did this user practice most recently" — F-322 review
        # queue + F-330.lists SRS scheduler both read this prefix.
        Index(
            "ix_user_vocab_progress_user_lastseen",
            "user_id",
            "last_seen_at",
        ),
    )
