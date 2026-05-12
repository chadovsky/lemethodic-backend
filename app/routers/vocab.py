"""F-325 — Le Vocabulaire vocab browse API.

Read-only endpoints on top of the F-320 schema. Surfaces the content
catalog (topics + chunks) for the FE topic browser. Personal-lists
endpoints (CRUD on user_vocab_lists / user_vocab_list_chunks /
user_vocab_progress) are NOT in this ticket — they ship under a
later dispatch.

Endpoints:
  GET /api/vocab/topics                          → list all topics + per-user locked flag
  GET /api/vocab/topics/{slug}                   → topic detail + chunk_count
  GET /api/vocab/topics/{slug}/chunks            → paginated chunk list with filters

Tier-gate contract (F-320 D12 / F-325 D3):
  - All endpoints require authentication via Depends(get_current_user).
  - GET /topics returns metadata for ALL partitions — the per-row
    `locked` flag tells the FE whether to render an upsell card.
    Decision: don't hide locked rows; they're the upsell surface.
  - GET /topics/{slug} and /chunks apply a per-slug runtime gate via
    enforce_min_tier(): topics with corpus_partition='free_general'
    are open to any auth user; topics with corpus_partition starting
    with 'exam_tagged_' require subscription tier or higher.
  - The gate is RUNTIME (not a DI factory) because the required tier
    depends on the target topic's partition, which isn't known until
    we read the row. enforce_min_tier raises HTTP 403 with the
    F-310 contract body shape ({"code": "tier_insufficient", ...}).

Third-party publisher rows (F-320 D4):
  Chunks with source_type='third_party_publisher_DO_NOT_EXTRACT' exist
  only as corpus provenance pointers — they're catalogued for source-
  attribution audits but NEVER served verbatim. Every chunk query
  applies a hard `source_type != ...` exclusion. The exclusion is
  silent (no public 403 surface) — those rows simply don't exist as
  far as the API is concerned. chunk_count on /topics/{slug} reflects
  the post-exclusion count for consistency.

Empty-DB shape contract:
  All 3 endpoints return 200 with empty arrays when no rows match.
  404 only fires on explicit slug-lookup misses on /topics/{slug}
  and /topics/{slug}/chunks. The catalog itself never 404s.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import User
from app.models.vocabulaire import VocabChunk, VocabTopic
from app.schemas.vocabulaire import (
    CorpusPartition,
    ExamTag,
    Register,
    VocabChunkPage,
    VocabChunkRead,
    VocabTopicDetail,
    VocabTopicListItem,
    VocabTopicListResponse,
)
from app.services.auth import get_current_user
from app.services.tiers import enforce_min_tier, user_tier_satisfies


router = APIRouter(prefix="/api/vocab", tags=["vocab"])


# Sentinel for the always-on third-party exclusion. Centralized as a
# constant so test-side parity checks (smoke + pytest) reference the
# same string the router does.
_PROVENANCE_ONLY_SOURCE_TYPE = "third_party_publisher_DO_NOT_EXTRACT"


def _is_exam_tagged(partition: str) -> bool:
    """corpus_partition string predicate. exam_tagged_TCF/DELF/TEF all
    share the same prefix; free_general is the only non-gated value."""
    return partition.startswith("exam_tagged_")


def _enforce_partition_gate(user: User, topic: VocabTopic) -> None:
    """Per-topic runtime tier gate. Raises 403 with F-310 contract
    body when the user's effective tier is below `subscription` for
    an exam_tagged_* topic. No-op for free_general."""
    if _is_exam_tagged(topic.corpus_partition):
        enforce_min_tier(user, "subscription")


def _count_chunks_for_topic(db: Session, topic_id: int) -> int:
    """Post-exclusion chunk count for a topic. Used both by
    /topics/{slug} chunk_count and as the `total` baseline for
    pagination on /chunks."""
    return (
        db.query(VocabChunk)
        .filter(
            VocabChunk.topic_id == topic_id,
            VocabChunk.source_type != _PROVENANCE_ONLY_SOURCE_TYPE,
        )
        .count()
    )


# ═══════════════════════════════════════════════════════════════
# GET /api/vocab/topics
# ═══════════════════════════════════════════════════════════════


@router.get("/topics", response_model=VocabTopicListResponse)
def list_topics(
    corpus_partition: Optional[CorpusPartition] = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> VocabTopicListResponse:
    """List all topics with a per-row `locked` flag.

    `locked=True` when the current user's tier doesn't permit chunk
    access (i.e., topic is exam_tagged_* AND user's tier < subscription).
    free_general topics always render `locked=False`. The endpoint
    returns rows for ALL partitions regardless of tier — locked rows
    are the FE upsell surface.

    Filter `corpus_partition` is optional; bad enum values are rejected
    by FastAPI as 422 before reaching the handler.
    """
    q = db.query(VocabTopic)
    if corpus_partition is not None:
        q = q.filter(VocabTopic.corpus_partition == corpus_partition)
    rows = q.order_by(VocabTopic.created_at.desc(), VocabTopic.id.desc()).all()

    has_subscription = user_tier_satisfies(user, "subscription")
    items = [
        VocabTopicListItem.model_validate(
            {
                "id": row.id,
                "slug": row.slug,
                "labels": row.labels or {},
                "description": row.description or {},
                "corpus_partition": row.corpus_partition,
                "cefr_level_min": row.cefr_level_min,
                "cefr_level_max": row.cefr_level_max,
                "created_at": row.created_at,
                "locked": _is_exam_tagged(row.corpus_partition)
                and not has_subscription,
            }
        )
        for row in rows
    ]
    return VocabTopicListResponse(topics=items)


# ═══════════════════════════════════════════════════════════════
# GET /api/vocab/topics/{slug}
# ═══════════════════════════════════════════════════════════════


@router.get("/topics/{slug}", response_model=VocabTopicDetail)
def get_topic(
    slug: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> VocabTopicDetail:
    """Topic detail + chunk_count. Runtime tier gate enforced per
    `corpus_partition` (see module docstring).

    404 on unknown slug; 403 with `tier_insufficient` body when an
    exam_tagged_* topic is requested by a sub-subscription user.
    """
    topic = db.query(VocabTopic).filter(VocabTopic.slug == slug).first()
    if topic is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Topic '{slug}' not found",
        )
    _enforce_partition_gate(user, topic)
    chunk_count = _count_chunks_for_topic(db, topic.id)
    return VocabTopicDetail.model_validate(
        {
            "id": topic.id,
            "slug": topic.slug,
            "labels": topic.labels or {},
            "description": topic.description or {},
            "corpus_partition": topic.corpus_partition,
            "cefr_level_min": topic.cefr_level_min,
            "cefr_level_max": topic.cefr_level_max,
            "created_at": topic.created_at,
            "chunk_count": chunk_count,
        }
    )


# ═══════════════════════════════════════════════════════════════
# GET /api/vocab/topics/{slug}/chunks
# ═══════════════════════════════════════════════════════════════


@router.get("/topics/{slug}/chunks", response_model=VocabChunkPage)
def list_chunks(
    slug: str,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    cefr_level: Optional[str] = Query(default=None),
    exam_tag: Optional[ExamTag] = Query(default=None),
    register: Optional[Register] = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> VocabChunkPage:
    """Paginated chunks under a topic. Filters: cefr_level (free-text
    string match; A1..C2), exam_tag (enum), register (enum). All
    optional; combined as AND.

    Always excludes third_party_publisher_DO_NOT_EXTRACT rows (F-320
    D4). `total` is the post-filter, post-exclusion row count.

    Ordering: id ASC for stable pagination. 404 on unknown topic slug;
    403 on tier mismatch (same contract as /topics/{slug}).
    """
    topic = db.query(VocabTopic).filter(VocabTopic.slug == slug).first()
    if topic is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Topic '{slug}' not found",
        )
    _enforce_partition_gate(user, topic)

    base_q = db.query(VocabChunk).filter(
        VocabChunk.topic_id == topic.id,
        VocabChunk.source_type != _PROVENANCE_ONLY_SOURCE_TYPE,
    )
    if cefr_level is not None:
        base_q = base_q.filter(VocabChunk.cefr_level == cefr_level)
    if exam_tag is not None:
        base_q = base_q.filter(VocabChunk.exam_tag == exam_tag)
    if register is not None:
        base_q = base_q.filter(VocabChunk.register == register)

    total = base_q.count()
    rows = (
        base_q.order_by(VocabChunk.id.asc()).limit(limit).offset(offset).all()
    )
    return VocabChunkPage(
        chunks=[VocabChunkRead.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )
