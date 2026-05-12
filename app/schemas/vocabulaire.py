"""F-320 — Pydantic schemas for Le Vocabulaire surface.

Request/response shapes consumed by F-322 (practice UI / personal
lists) + F-323 (test UI). Included in F-320 per scope line 1312
("Pydantic schemas + ORM models").

i18n fields use a `dict[str, str]` shape rather than a strict
TypedDict because the locale set is open (FR/EN/ES today, possibly
IT/DE/PT later). Empty dict is the default — FE falls back to slug
when a locale key is missing.

Tier gating is enforced at the router layer (Depends(require_tier(...)))
per the F-320 module docstring on app/models/vocabulaire.py — these
schemas are tier-agnostic.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


CorpusPartition = Literal[
    "free_general",
    "exam_tagged_TCF",
    "exam_tagged_DELF",
    "exam_tagged_TEF",
]

SourceType = Literal[
    "CC_corpus",
    "chadi_authored",
    "book_lab",
    "third_party_publisher_DO_NOT_EXTRACT",
]

Register = Literal["formel", "semi_formel", "informel", "argotique"]

ExamTag = Literal["tcf", "tef", "delf", "dalf"]


# ── vocab_topics ──────────────────────────────────────────────────


class VocabTopicRead(BaseModel):
    """Topic catalog row. FE topic picker consumes this list."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: int
    slug: str
    labels: dict[str, str] = Field(default_factory=dict)
    description: dict[str, str] = Field(default_factory=dict)
    corpus_partition: CorpusPartition
    cefr_level_min: Optional[str] = None
    cefr_level_max: Optional[str] = None
    created_at: datetime


# ── vocab_chunks ──────────────────────────────────────────────────


class VocabChunkRead(BaseModel):
    """Chunk row served by topic-detail + personal-list endpoints.

    `source` and `source_type` are surfaced so the FE can render the
    CC BY-SA attribution badge when source_type='CC_corpus'.
    Third-party-publisher rows are filtered out at the router layer
    (they exist only as provenance pointers, never served verbatim)."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: int
    chunk_fr: str
    chunk_en: Optional[str] = None
    topic_id: int
    source: Optional[str] = None
    source_type: SourceType
    register: Optional[Register] = None
    exam_tag: Optional[ExamTag] = None
    cefr_level: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ── user_vocab_lists ──────────────────────────────────────────────


class UserVocabListCreate(BaseModel):
    """POST /api/vocab/lists — create a new personal list."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)


class UserVocabListRead(BaseModel):
    """List metadata (without chunks). FE list-browser surface."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: int
    user_id: int
    name: str
    created_at: datetime
    updated_at: datetime


class UserVocabListWithChunks(UserVocabListRead):
    """List detail surface — includes the ordered chunk membership."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    chunks: list[VocabChunkRead] = Field(default_factory=list)


# ── user_vocab_list_chunks ────────────────────────────────────────


class UserVocabListChunkAdd(BaseModel):
    """POST /api/vocab/lists/{list_id}/chunks — add a chunk to a list."""

    model_config = ConfigDict(extra="forbid")

    chunk_id: int


# ── user_vocab_progress ───────────────────────────────────────────


class UserVocabProgressRead(BaseModel):
    """Practice progress row. FE practice review queue + dashboard."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    chunk_id: int
    seen_count: int
    correct_count: int
    last_seen_at: Optional[datetime] = None


class UserVocabProgressUpdate(BaseModel):
    """POST /api/vocab/progress/{chunk_id} — record a practice event.

    Caller passes whether the answer was correct; router increments
    seen_count + (optionally) correct_count + stamps last_seen_at.
    The SRS box-promotion logic (F-330.lists) reads these counts."""

    model_config = ConfigDict(extra="forbid")

    correct: bool
