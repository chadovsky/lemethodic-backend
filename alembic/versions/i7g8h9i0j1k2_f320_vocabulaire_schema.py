"""F-320 — Le Vocabulaire DB schema (5 tables)

Adds the content store + personal-lists surface for Le Vocabulaire,
the third pillar alongside L'École and Le Diagnostic. Parent ticket
is F-330 (V2 enumeration tracked there); F-321 owns the Phase 1
seed from Chadi's tutoring archive (BLOCKED on F-321.audit sample
audit at the time this migration ships — schema does NOT depend on
that block; table shape is the same whether populated by extraction
pipeline or manual curation).

Tables created (creation order matters for FKs):

  vocab_topics              — content-browse catalog with corpus partition.
                              Distinct from P-202 vocabulary_themes (per
                              F-320 Decision D1 approved 2026-05-12;
                              different concept, different lifecycle).
  vocab_chunks              — content unit (lexical chunk + EN gloss +
                              source + register + exam_tag + cefr_level).
                              FK to vocab_topics.
  user_vocab_lists          — personal list metadata, owned by a user.
                              FK to users with CASCADE.
  user_vocab_list_chunks    — join row, chunk-in-list membership. CASCADE
                              on both list deletion and chunk deletion.
  user_vocab_progress       — per-user-per-chunk practice progress.
                              CASCADE on users and chunks.

Enum domains (CHECK-enforced, mirrored in ORM __table_args__):

  vocab_topics.corpus_partition:
    free_general | exam_tagged_TCF | exam_tagged_DELF | exam_tagged_TEF

  vocab_chunks.source_type:
    CC_corpus | chadi_authored | book_lab |
    third_party_publisher_DO_NOT_EXTRACT
    (parent F-330 enum per Decision D2 approved 2026-05-12; supersedes
    the stale `oqlf|academie|curated` text in BACKLOG.md F-320 line
    1306, which is corrected in the same commit as this migration.)

  vocab_chunks.register:
    NULL | formel | semi_formel | informel | argotique
    (matches Tache2Scenario.register + `argotique` for vocab surface.)

  vocab_chunks.exam_tag:
    NULL | tcf | tef | delf | dalf

Indices:
  vocab_topics: PK id, UNIQUE slug, ix corpus_partition
  vocab_chunks: PK id, ix topic_id, ix exam_tag, composite
                (topic_id, cefr_level)
  user_vocab_lists: PK id, ix user_id, UNIQUE(user_id, name),
                    composite (user_id, created_at)
  user_vocab_list_chunks: PK id, ix list_id, ix chunk_id,
                          UNIQUE(list_id, chunk_id)
  user_vocab_progress: PK id, ix user_id, UNIQUE(user_id, chunk_id),
                       composite (user_id, last_seen_at)

Out of scope:
  - SRS scheduling columns (next_due_at, box_number) — F-330.lists V2.
  - pgvector / embedding column — F-312 hasn't landed; deferred to an
    additive follow-up migration. No CREATE EXTENSION in this file.
  - Seed data — F-321 owns the Phase 1 seed (Chadi tutoring archive
    + sample-audit gate). Tables ship empty.
  - Tier-gate enforcement — F-322/F-323 routers consume
    require_tier("subscription") DI from F-310 Phase A; schema is
    tier-agnostic.

Rollback safety:
  Pure additive — 5 CREATE TABLE, zero column changes on existing
  tables, zero DML. downgrade() drops the 5 new tables in reverse
  creation order; no data preservation needed because no production
  rows exist until F-321 seeds AFTER this lands. `alembic downgrade
  -1` is the emergency restore path; pg_dump from Chadi's pre-push
  step is the secondary backup.

Revision ID: i7g8h9i0j1k2
Revises: h6f7g8e9d0c1
Create Date: 2026-05-12 (F-320 Le Vocabulaire DB schema).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = "i7g8h9i0j1k2"
down_revision: Union[str, None] = "h6f7g8e9d0c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── vocab_topics ───────────────────────────────────────────────
    op.create_table(
        "vocab_topics",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column(
            "labels",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "description",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("corpus_partition", sa.String(length=40), nullable=False),
        sa.Column("cefr_level_min", sa.String(length=10), nullable=True),
        sa.Column("cefr_level_max", sa.String(length=10), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "corpus_partition IN ("
            "'free_general', 'exam_tagged_TCF', 'exam_tagged_DELF', 'exam_tagged_TEF'"
            ")",
            name="ck_vocab_topics_corpus_partition",
        ),
    )
    op.create_index(
        op.f("ix_vocab_topics_id"), "vocab_topics", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_vocab_topics_slug"), "vocab_topics", ["slug"], unique=True
    )
    op.create_index(
        op.f("ix_vocab_topics_corpus_partition"),
        "vocab_topics",
        ["corpus_partition"],
        unique=False,
    )

    # ── vocab_chunks ───────────────────────────────────────────────
    op.create_table(
        "vocab_chunks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("chunk_fr", sa.String(length=500), nullable=False),
        sa.Column("chunk_en", sa.String(length=500), nullable=True),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=500), nullable=True),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("register", sa.String(length=20), nullable=True),
        sa.Column("exam_tag", sa.String(length=20), nullable=True),
        sa.Column("cefr_level", sa.String(length=10), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["vocab_topics.id"],
            name="fk_vocab_chunks_topic",
        ),
        sa.CheckConstraint(
            "source_type IN ("
            "'CC_corpus', 'chadi_authored', 'book_lab', "
            "'third_party_publisher_DO_NOT_EXTRACT'"
            ")",
            name="ck_vocab_chunks_source_type",
        ),
        sa.CheckConstraint(
            "register IS NULL "
            "OR register IN ('formel', 'semi_formel', 'informel', 'argotique')",
            name="ck_vocab_chunks_register",
        ),
        sa.CheckConstraint(
            "exam_tag IS NULL "
            "OR exam_tag IN ('tcf', 'tef', 'delf', 'dalf')",
            name="ck_vocab_chunks_exam_tag",
        ),
    )
    op.create_index(
        op.f("ix_vocab_chunks_id"), "vocab_chunks", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_vocab_chunks_topic_id"),
        "vocab_chunks",
        ["topic_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_vocab_chunks_exam_tag"),
        "vocab_chunks",
        ["exam_tag"],
        unique=False,
    )
    # Composite — supports "topic page, filtered by level".
    op.create_index(
        "ix_vocab_chunks_topic_level",
        "vocab_chunks",
        ["topic_id", "cefr_level"],
        unique=False,
    )

    # ── user_vocab_lists ───────────────────────────────────────────
    op.create_table(
        "user_vocab_lists",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_vocab_lists_user",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "user_id", "name", name="uq_user_vocab_lists_user_name"
        ),
    )
    op.create_index(
        op.f("ix_user_vocab_lists_id"),
        "user_vocab_lists",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_vocab_lists_user_id"),
        "user_vocab_lists",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_user_vocab_lists_user_created",
        "user_vocab_lists",
        ["user_id", "created_at"],
        unique=False,
    )

    # ── user_vocab_list_chunks ─────────────────────────────────────
    op.create_table(
        "user_vocab_list_chunks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("list_id", sa.Integer(), nullable=False),
        sa.Column("chunk_id", sa.Integer(), nullable=False),
        sa.Column(
            "added_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(
            ["list_id"],
            ["user_vocab_lists.id"],
            name="fk_user_vocab_list_chunks_list",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id"],
            ["vocab_chunks.id"],
            name="fk_user_vocab_list_chunks_chunk",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "list_id",
            "chunk_id",
            name="uq_user_vocab_list_chunks_list_chunk",
        ),
    )
    op.create_index(
        op.f("ix_user_vocab_list_chunks_id"),
        "user_vocab_list_chunks",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_vocab_list_chunks_list_id"),
        "user_vocab_list_chunks",
        ["list_id"],
        unique=False,
    )
    op.create_index(
        "ix_user_vocab_list_chunks_chunk",
        "user_vocab_list_chunks",
        ["chunk_id"],
        unique=False,
    )

    # ── user_vocab_progress ────────────────────────────────────────
    op.create_table(
        "user_vocab_progress",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("chunk_id", sa.Integer(), nullable=False),
        sa.Column(
            "seen_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "correct_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_vocab_progress_user",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id"],
            ["vocab_chunks.id"],
            name="fk_user_vocab_progress_chunk",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "user_id",
            "chunk_id",
            name="uq_user_vocab_progress_user_chunk",
        ),
    )
    op.create_index(
        op.f("ix_user_vocab_progress_id"),
        "user_vocab_progress",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_vocab_progress_user_id"),
        "user_vocab_progress",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_user_vocab_progress_user_lastseen",
        "user_vocab_progress",
        ["user_id", "last_seen_at"],
        unique=False,
    )


def downgrade() -> None:
    # Reverse creation order so FK constraints unwind cleanly.

    # ── user_vocab_progress ────────────────────────────────────────
    op.drop_index(
        "ix_user_vocab_progress_user_lastseen",
        table_name="user_vocab_progress",
    )
    op.drop_index(
        op.f("ix_user_vocab_progress_user_id"),
        table_name="user_vocab_progress",
    )
    op.drop_index(
        op.f("ix_user_vocab_progress_id"), table_name="user_vocab_progress"
    )
    op.drop_table("user_vocab_progress")

    # ── user_vocab_list_chunks ─────────────────────────────────────
    op.drop_index(
        "ix_user_vocab_list_chunks_chunk",
        table_name="user_vocab_list_chunks",
    )
    op.drop_index(
        op.f("ix_user_vocab_list_chunks_list_id"),
        table_name="user_vocab_list_chunks",
    )
    op.drop_index(
        op.f("ix_user_vocab_list_chunks_id"),
        table_name="user_vocab_list_chunks",
    )
    op.drop_table("user_vocab_list_chunks")

    # ── user_vocab_lists ───────────────────────────────────────────
    op.drop_index(
        "ix_user_vocab_lists_user_created", table_name="user_vocab_lists"
    )
    op.drop_index(
        op.f("ix_user_vocab_lists_user_id"), table_name="user_vocab_lists"
    )
    op.drop_index(
        op.f("ix_user_vocab_lists_id"), table_name="user_vocab_lists"
    )
    op.drop_table("user_vocab_lists")

    # ── vocab_chunks ───────────────────────────────────────────────
    op.drop_index(
        "ix_vocab_chunks_topic_level", table_name="vocab_chunks"
    )
    op.drop_index(
        op.f("ix_vocab_chunks_exam_tag"), table_name="vocab_chunks"
    )
    op.drop_index(
        op.f("ix_vocab_chunks_topic_id"), table_name="vocab_chunks"
    )
    op.drop_index(op.f("ix_vocab_chunks_id"), table_name="vocab_chunks")
    op.drop_table("vocab_chunks")

    # ── vocab_topics ───────────────────────────────────────────────
    op.drop_index(
        op.f("ix_vocab_topics_corpus_partition"), table_name="vocab_topics"
    )
    op.drop_index(
        op.f("ix_vocab_topics_slug"), table_name="vocab_topics"
    )
    op.drop_index(op.f("ix_vocab_topics_id"), table_name="vocab_topics")
    op.drop_table("vocab_topics")
