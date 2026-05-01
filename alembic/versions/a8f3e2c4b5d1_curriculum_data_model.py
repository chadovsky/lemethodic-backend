"""P-202 / P-203 / P-204 — curriculum data model

Adds the curriculum, path, and user-progress data model from
LEMETHODIC-CURRICULUM v0.2 (mirrored at docs/LEMETHODIC-CURRICULUM.md).

Tables created (creation order matters for FKs):

  vocabulary_themes        — P-202 — taxonomy table, seeded with §5.1 themes
  clusters                 — P-202 — atomic curriculum unit (§5)
  paths                    — P-203 — A2→B1, B1→B2, etc. (§4)
  phases                   — P-203 — ordered phases within a path
  path_clusters            — P-203 — join + ordering of clusters within a phase
  user_path_enrollments    — P-204 — user's active/completed path enrollments
  user_cluster_statuses    — P-204 — per-user-per-cluster snapshot
  user_cluster_events      — P-204 — append-only history log of status transitions

i18n convention: short UI strings (labels / tagline / description) are
JSONB shaped {"fr": "...", "en": "..."}. NOT the legacy _fr / _en column
pattern from User / Recording. Phase 1 authoring writes the "fr" key;
additional locales fill in as content is translated.

Lesson body content (lesson_markdown / lesson_asset_url) is single-language
plain text/varchar for Phase 1 — content is FR-only, JSONB on a 5+ kB
markdown body adds real cost for zero current benefit. Promote to JSONB
in a follow-up migration when Italian / German / Spanish lesson content
actually exists.

marker_id format (locked): {level}.{phase_num}.C{cluster_num}.{letter} —
e.g. "B1.1.C1.a" = level B1, phase B1.1, cluster C1, marker letter a.
The 3-segment form ("B1.1.a") seen in some authored cluster docs is an
authoring error to be normalized; backend treats only the 4-segment form
as canonical.

Detection rubric stub shape (clusters.detection_rubric):

    {
      "markers": [
        {
          "marker_id": "B1.1.C1.a",
          "name": "Flat narrative",
          "firing_condition": {
            "type": "ratio_threshold",
            "metric": "imparfait_ratio",
            "operator": "<",
            "value": 0.15,
            "context": "narrative_60s+"
          },
          "severity": "high",
          "ceiling_level": "B1"
        }
      ],
      "status_logic": {
        "absorbed":       "all_markers_silent_for_2_consecutive",
        "partial":        "max_1_marker_firing",
        "needs_revisit":  "2+_markers_firing_OR_high_severity_alone"
      }
    }

This stub is intentionally loose; the final shape evolves with P-200
detector implementation. P-211 cluster authoring should follow this shape;
runtime validation will live in a Pydantic model attached to P-200.

Revision ID: a8f3e2c4b5d1   ← PLACEHOLDER. Regenerate via
                              `alembic revision --autogenerate -m "..."`
                              before applying, OR keep this ID if approved
                              as-is.
Revises: 57c313935953
Create Date: 2026-05-01

NOTE — model classes for these tables (Cluster, VocabularyTheme, Path,
Phase, PathCluster, UserPathEnrollment, UserClusterStatus,
UserClusterEvent) are NOT yet declared in app/models/models.py. They land
in the follow-up commit alongside this migration. Until then,
`alembic revision --autogenerate` will see drift (Base.metadata has no
record of the new tables) — do not autogenerate again until the model
classes are added.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'a8f3e2c4b5d1'
down_revision: Union[str, None] = '57c313935953'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ── Vocabulary theme seed (curriculum doc §5.1) ─────────────────────────
# 27 themes from the canonical Vocabulaire Progressif organization. Slugs
# are stable — content authoring (P-211) and seed scripts reference them
# by slug, not by id.
VOCABULARY_THEME_SEED: list[dict[str, object]] = [
    {"slug": "usages_politesse",            "labels": {"fr": "Les usages / La politesse",                                  "en": "Manners / Politeness"}},
    {"slug": "famille",                     "labels": {"fr": "La famille",                                                  "en": "Family"}},
    {"slug": "amour_sentiments",            "labels": {"fr": "L'amour / Les sentiments",                                    "en": "Love / Feelings"}},
    {"slug": "caractere_personnalite",      "labels": {"fr": "Le caractère / La personnalité",                              "en": "Character / Personality"}},
    {"slug": "communication",               "labels": {"fr": "La communication",                                            "en": "Communication"}},
    {"slug": "corps_mouvements_sante",      "labels": {"fr": "Le corps / Les mouvements / La santé",                        "en": "Body / Movement / Health"}},
    {"slug": "description_physique",        "labels": {"fr": "La description physique / L'apparence",                       "en": "Physical description / Appearance"}},
    {"slug": "vetements_mode_couleurs",     "labels": {"fr": "Les vêtements / La mode / Les couleurs",                      "en": "Clothing / Fashion / Colors"}},
    {"slug": "maison_logement",             "labels": {"fr": "La maison / Le logement",                                     "en": "Home / Housing"}},
    {"slug": "activites_quotidiennes",      "labels": {"fr": "Les activités quotidiennes",                                  "en": "Daily activities"}},
    {"slug": "alimentation_courses",        "labels": {"fr": "Les produits alimentaires / Les commerces / Faire les courses", "en": "Food / Shops / Grocery shopping"}},
    {"slug": "cuisine_repas_restaurant",    "labels": {"fr": "La cuisine / Les repas / Le restaurant",                      "en": "Cooking / Meals / Restaurants"}},
    {"slug": "temps_climat",                "labels": {"fr": "Le temps qui passe / Le temps qu'il fait / Le climat",        "en": "Time / Weather / Climate"}},
    {"slug": "ecole_enseignement",          "labels": {"fr": "L'école / L'enseignement",                                    "en": "School / Education"}},
    {"slug": "professions_vie_pro",         "labels": {"fr": "Les professions / La vie professionnelle",                    "en": "Professions / Working life"}},
    {"slug": "technologie_medias",          "labels": {"fr": "La technologie / Les médias",                                 "en": "Technology / Media"}},
    {"slug": "argent_banque",               "labels": {"fr": "L'argent / La banque",                                        "en": "Money / Banking"}},
    {"slug": "poste_services_admin",        "labels": {"fr": "La poste / Les services / L'administration",                  "en": "Mail / Services / Administration"}},
    {"slug": "geographie_francophonie",     "labels": {"fr": "La géographie / La francophonie",                             "en": "Geography / Francophonie"}},
    {"slug": "ville_campagne_directions",   "labels": {"fr": "La ville / La campagne / Les directions",                     "en": "City / Countryside / Directions"}},
    {"slug": "transports_circulation",      "labels": {"fr": "Les transports / La circulation",                             "en": "Transportation / Traffic"}},
    {"slug": "tourisme_voyages",            "labels": {"fr": "Le tourisme / Les voyages / Les vacances",                    "en": "Tourism / Travel / Holidays"}},
    {"slug": "loisirs_sports_jeux",         "labels": {"fr": "Les loisirs / Les sports / Les jeux",                         "en": "Leisure / Sports / Games"}},
    {"slug": "arts_culture",                "labels": {"fr": "Les arts / Les spectacles / La culture",                      "en": "Arts / Performances / Culture"}},
    {"slug": "nature_environnement",        "labels": {"fr": "Nature et environnement",                                     "en": "Nature and environment"}},
    {"slug": "diversite_politique_societe", "labels": {"fr": "Diversité / Politique / Société",                              "en": "Diversity / Politics / Society"}},
    {"slug": "debats_opinions",             "labels": {"fr": "Débats et opinions",                                          "en": "Debates and opinions"}},
]


def upgrade() -> None:
    # ── vocabulary_themes ───────────────────────────────────────────────
    op.create_table(
        'vocabulary_themes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('slug', sa.String(length=60), nullable=False),
        sa.Column('labels', JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_vocabulary_themes_id'),   'vocabulary_themes', ['id'],   unique=False)
    op.create_index(op.f('ix_vocabulary_themes_slug'), 'vocabulary_themes', ['slug'], unique=True)

    # Seed §5.1 themes inline so dependent ticket work (P-210 path seed,
    # P-211 cluster authoring) has the vocabulary picker available
    # immediately after this migration runs.
    vocabulary_themes_table = sa.table(
        'vocabulary_themes',
        sa.column('slug',   sa.String),
        sa.column('labels', JSONB),
    )
    op.bulk_insert(vocabulary_themes_table, VOCABULARY_THEME_SEED)

    # ── clusters ────────────────────────────────────────────────────────
    op.create_table(
        'clusters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('slug', sa.String(length=80), nullable=False),
        # Display labels — i18n JSONB. e.g. {"fr": "Pronoms COD/COI", "en": "Direct/indirect object pronouns"}
        sa.Column('labels', JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        # Grammar topic — French canonical name, doubles as a grouping key across clusters.
        sa.Column('grammar_topic', sa.String(length=120), nullable=False),
        # Vocabulary theme — FK to the seeded taxonomy. Nullable: pure-grammar
        # clusters (e.g. Pronoms toniques) may not pin to a single theme.
        sa.Column('vocabulary_theme_id', sa.Integer(), nullable=True),
        # "tache_1" | "tache_2" | "tache_3" — speaking-only for Phase 1.
        # "writing" gets added in a follow-up migration when P-260 starts
        # (CHECK constraint expanded then).
        sa.Column('tache_application', sa.String(length=20), nullable=False),
        # "A2" | "B1" | "B2" | "C1" — intrinsic level of the cluster's content,
        # independent of which path it sits in (a B1 cluster can appear in
        # both A2→B1's last phase and B1→B2's first phase).
        sa.Column('cefr_level', sa.String(length=10), nullable=False),
        # §5.2 spiral revisits — self-FK to the first-encounter cluster.
        sa.Column('is_spiral_revisit', sa.Boolean(), nullable=True),
        sa.Column('parent_cluster_id', sa.Integer(), nullable=True),
        # "markdown" | "pdf" | "video" — decided per cluster at authoring (P-211).
        sa.Column('lesson_format', sa.String(length=20), nullable=False),
        # FR-only Phase 1 (see module docstring on i18n). Promote to JSONB
        # when non-FR lesson content is authored.
        sa.Column('lesson_markdown',  sa.Text(),               nullable=True),
        sa.Column('lesson_asset_url', sa.String(length=500),   nullable=True),
        # List of exercise objects: [{"type": "fill_blank", "prompt": "...", "answer": "..."}, ...]
        sa.Column('exercise_set',     JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        # Single Tâche-shaped prompt object.
        sa.Column('practice_prompt',  JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        # See module docstring for the stub shape; finalized with P-200.
        sa.Column('detection_rubric', JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "tache_application IN ('tache_1', 'tache_2', 'tache_3')",
            name='ck_clusters_tache_application',
        ),
        sa.ForeignKeyConstraint(['parent_cluster_id'],   ['clusters.id'],          name='fk_clusters_parent'),
        sa.ForeignKeyConstraint(['vocabulary_theme_id'], ['vocabulary_themes.id'], name='fk_clusters_vocab_theme'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_clusters_id'),         'clusters', ['id'],         unique=False)
    op.create_index(op.f('ix_clusters_slug'),       'clusters', ['slug'],       unique=True)
    op.create_index(op.f('ix_clusters_cefr_level'), 'clusters', ['cefr_level'], unique=False)

    # ── paths ───────────────────────────────────────────────────────────
    op.create_table(
        'paths',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('slug', sa.String(length=40), nullable=False),
        # {"fr": "Construire le moteur", "en": "Build the engine"}
        sa.Column('labels',  JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('tagline', JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('level_start',  sa.String(length=10), nullable=False),
        sa.Column('level_target', sa.String(length=10), nullable=False),
        # is_active=false → waitlist screen (§8.4, P-222)
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('estimated_weeks', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_paths_id'),   'paths', ['id'],   unique=False)
    op.create_index(op.f('ix_paths_slug'), 'paths', ['slug'], unique=True)

    # ── phases ──────────────────────────────────────────────────────────
    op.create_table(
        'phases',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('path_id', sa.Integer(), nullable=False),
        # 1-indexed within the path (1, 2, 3, ...).
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('slug', sa.String(length=40), nullable=False),
        sa.Column('labels',      JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('description', JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.ForeignKeyConstraint(['path_id'], ['paths.id'], name='fk_phases_path'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('path_id', 'position', name='uq_phase_path_position'),
        sa.UniqueConstraint('path_id', 'slug',     name='uq_phase_path_slug'),
    )
    op.create_index(op.f('ix_phases_id'),      'phases', ['id'],      unique=False)
    op.create_index(op.f('ix_phases_path_id'), 'phases', ['path_id'], unique=False)

    # ── path_clusters ───────────────────────────────────────────────────
    op.create_table(
        'path_clusters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('phase_id',   sa.Integer(), nullable=False),
        sa.Column('cluster_id', sa.Integer(), nullable=False),
        sa.Column('position',   sa.Integer(), nullable=False),
        # Skipped in Cram persona compression (§4.2).
        sa.Column('is_optional', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['cluster_id'], ['clusters.id'], name='fk_path_clusters_cluster'),
        sa.ForeignKeyConstraint(['phase_id'],   ['phases.id'],   name='fk_path_clusters_phase'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('phase_id', 'position',   name='uq_pc_phase_position'),
        sa.UniqueConstraint('phase_id', 'cluster_id', name='uq_pc_phase_cluster'),
    )
    op.create_index(op.f('ix_path_clusters_id'),       'path_clusters', ['id'],       unique=False)
    op.create_index(op.f('ix_path_clusters_phase_id'), 'path_clusters', ['phase_id'], unique=False)

    # ── user_path_enrollments ──────────────────────────────────────────
    op.create_table(
        'user_path_enrollments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('path_id', sa.Integer(), nullable=False),
        # Diagnostic snapshot at enrollment.
        sa.Column('enrolled_at_level',      sa.String(length=10), nullable=False),
        # "high" | "medium" | "low" — §6.3
        sa.Column('enrolled_at_confidence', sa.String(length=20), nullable=True),
        # Cached pointers — derivable from user_cluster_statuses + path_clusters
        # but cached here so "Today's recommended action" (P-240) is a single-row read.
        sa.Column('current_phase_id',   sa.Integer(), nullable=True),
        sa.Column('current_cluster_id', sa.Integer(), nullable=True),
        sa.Column('is_active',    sa.Boolean(),  nullable=True),
        sa.Column('enrolled_at',  sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['current_cluster_id'], ['clusters.id'], name='fk_enrollment_current_cluster'),
        sa.ForeignKeyConstraint(['current_phase_id'],   ['phases.id'],   name='fk_enrollment_current_phase'),
        sa.ForeignKeyConstraint(['path_id'],            ['paths.id'],    name='fk_enrollment_path'),
        sa.ForeignKeyConstraint(['user_id'],            ['users.id'],    name='fk_enrollment_user'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'path_id', name='uq_enrollment_user_path'),
    )
    op.create_index(op.f('ix_user_path_enrollments_id'),      'user_path_enrollments', ['id'],      unique=False)
    op.create_index(op.f('ix_user_path_enrollments_user_id'), 'user_path_enrollments', ['user_id'], unique=False)
    # Partial unique index — at most one ACTIVE enrollment per user.
    # Postgres-native; equivalent on SQLite would be app-level. Decision
    # logged in the LEMETHODIC schema review (2026-05-01).
    op.create_index(
        'uq_user_path_enrollments_one_active',
        'user_path_enrollments',
        ['user_id'],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
    )

    # ── user_cluster_statuses ──────────────────────────────────────────
    op.create_table(
        'user_cluster_statuses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id',    sa.Integer(), nullable=False),
        sa.Column('cluster_id', sa.Integer(), nullable=False),
        # "not_started" | "in_progress" | "absorbed" | "needs_revisit" (P-204 spec)
        sa.Column('status', sa.String(length=20), nullable=False, server_default=sa.text("'not_started'")),
        sa.Column('last_rubric_score',           sa.Float(),   nullable=True),
        sa.Column('last_evaluated_recording_id', sa.Integer(), nullable=True),
        sa.Column('revisit_count',               sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column('first_started_at',      sa.DateTime(), nullable=True),
        sa.Column('last_status_change_at', sa.DateTime(), nullable=True),
        sa.Column('absorbed_at',           sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['cluster_id'],                  ['clusters.id'],   name='fk_ucs_cluster'),
        sa.ForeignKeyConstraint(['last_evaluated_recording_id'], ['recordings.id'], name='fk_ucs_recording'),
        sa.ForeignKeyConstraint(['user_id'],                     ['users.id'],      name='fk_ucs_user'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'cluster_id', name='uq_user_cluster'),
    )
    op.create_index(op.f('ix_user_cluster_statuses_id'),      'user_cluster_statuses', ['id'],      unique=False)
    op.create_index(op.f('ix_user_cluster_statuses_user_id'), 'user_cluster_statuses', ['user_id'], unique=False)

    # ── user_cluster_events ─────────────────────────────────────────────
    # Append-only history log. Distinct from user_cluster_statuses (which
    # holds the current snapshot) so the dashboard's history view can
    # render a chronological log without losing data when status flips
    # back and forth (e.g., absorbed → needs_revisit → absorbed).
    op.create_table(
        'user_cluster_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id',    sa.Integer(), nullable=False),
        sa.Column('cluster_id', sa.Integer(), nullable=False),
        # NULL on first event (the "not_started" → first state transition).
        sa.Column('from_status', sa.String(length=20), nullable=True),
        sa.Column('to_status',   sa.String(length=20), nullable=False),
        sa.Column('triggered_by_recording_id', sa.Integer(), nullable=True),
        sa.Column('rubric_score', sa.Float(),    nullable=True),
        sa.Column('created_at',   sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['cluster_id'],                ['clusters.id'],   name='fk_uce_cluster'),
        sa.ForeignKeyConstraint(['triggered_by_recording_id'], ['recordings.id'], name='fk_uce_recording'),
        sa.ForeignKeyConstraint(['user_id'],                   ['users.id'],      name='fk_uce_user'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_user_cluster_events_id'),           'user_cluster_events', ['id'],                       unique=False)
    # Composite (user_id, created_at) — serves Block 7 Mistake Repository's
    # "all events for user X, newest first" query as a prefix scan + reverse
    # walk. Replaces a standalone user_id index (would be redundant).
    op.create_index(op.f('ix_user_cluster_events_user_created'), 'user_cluster_events', ['user_id', 'created_at'],    unique=False)
    op.create_index(op.f('ix_user_cluster_events_cluster_id'),   'user_cluster_events', ['cluster_id'],                unique=False)


def downgrade() -> None:
    # Reverse creation order so FKs come down cleanly.
    op.drop_index(op.f('ix_user_cluster_events_cluster_id'),   table_name='user_cluster_events')
    op.drop_index(op.f('ix_user_cluster_events_user_created'), table_name='user_cluster_events')
    op.drop_index(op.f('ix_user_cluster_events_id'),           table_name='user_cluster_events')
    op.drop_table('user_cluster_events')

    op.drop_index(op.f('ix_user_cluster_statuses_user_id'), table_name='user_cluster_statuses')
    op.drop_index(op.f('ix_user_cluster_statuses_id'),      table_name='user_cluster_statuses')
    op.drop_table('user_cluster_statuses')

    op.drop_index('uq_user_path_enrollments_one_active',     table_name='user_path_enrollments')
    op.drop_index(op.f('ix_user_path_enrollments_user_id'),  table_name='user_path_enrollments')
    op.drop_index(op.f('ix_user_path_enrollments_id'),       table_name='user_path_enrollments')
    op.drop_table('user_path_enrollments')

    op.drop_index(op.f('ix_path_clusters_phase_id'), table_name='path_clusters')
    op.drop_index(op.f('ix_path_clusters_id'),       table_name='path_clusters')
    op.drop_table('path_clusters')

    op.drop_index(op.f('ix_phases_path_id'), table_name='phases')
    op.drop_index(op.f('ix_phases_id'),      table_name='phases')
    op.drop_table('phases')

    op.drop_index(op.f('ix_paths_slug'), table_name='paths')
    op.drop_index(op.f('ix_paths_id'),   table_name='paths')
    op.drop_table('paths')

    op.drop_index(op.f('ix_clusters_cefr_level'), table_name='clusters')
    op.drop_index(op.f('ix_clusters_slug'),       table_name='clusters')
    op.drop_index(op.f('ix_clusters_id'),         table_name='clusters')
    op.drop_table('clusters')

    op.drop_index(op.f('ix_vocabulary_themes_slug'), table_name='vocabulary_themes')
    op.drop_index(op.f('ix_vocabulary_themes_id'),   table_name='vocabulary_themes')
    op.drop_table('vocabulary_themes')
