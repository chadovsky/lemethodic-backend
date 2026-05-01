"""P-210 — seed the B1→B2 path (1 path, 5 phases, 22 cluster slots).

Source of structure: LEMETHODIC-CURRICULUM v0.2 §4.2 (mirrored at
docs/LEMETHODIC-CURRICULUM.md). Cluster identifiers follow the
4-segment marker convention so a marker_id "B1.1.C1.a" maps cleanly
back to its cluster slug "B1.1.C1".

Idempotency: aborts early if a Path with slug "b1_to_b2" already exists.
Re-run is a no-op. All inserts run inside a single transaction — if any
step fails, no partial state lands.

Content fields are intentionally empty (lesson_markdown="",
lesson_asset_url="", detection_rubric={}); structure is what matters.
Content authoring lands in P-211 ingestion.

vocabulary_theme_id is left NULL on every cluster — the cluster→theme
mapping isn't finalized yet, especially for B1.4 / B1.5. P-211 ingestion
will fill these in.

tache_application defaults to "tache_3" (long monologue) — the dominant
practice mode for B1→B2. P-211 may override per cluster (e.g. B1.4.C17
"Question formation sous pression" is Tâche-2-specific per §4.2).

Run from project root after `alembic upgrade head`:
    python -m scripts.seed_b1_b2_path
"""
from __future__ import annotations

from app.database import SessionLocal
from app.models.models import Cluster, Path, PathCluster, Phase


PATH_SLUG = "b1_to_b2"


PATH_DEF = {
    "slug": PATH_SLUG,
    "labels": {
        "fr": "B1 → B2 — Cesser de traduire, structurer",
        "en": "B1 → B2 — Stop translating, start structuring",
    },
    "tagline": {
        "fr": "Détacher l'anglais, acquérir la subordination",
        "en": "Detach from English, acquire subordination",
    },
    "level_start": "B1",
    "level_target": "B2",
    "is_active": True,
    "estimated_weeks": 8,
}


PHASES = [
    {
        "slug": "b1_1_tense_mastery",
        "position": 1,
        "labels": {"fr": "B1.1 — Maîtrise des temps", "en": "B1.1 — Tense Mastery"},
    },
    {
        "slug": "b1_2_pronoun_automation",
        "position": 2,
        "labels": {"fr": "B1.2 — Automatisation des pronoms", "en": "B1.2 — Pronoun Automation"},
    },
    {
        "slug": "b1_3_subordination",
        "position": 3,
        "labels": {"fr": "B1.3 — Subordination", "en": "B1.3 — Subordination"},
    },
    {
        "slug": "b1_4_l1_detachment",
        "position": 4,
        "labels": {"fr": "B1.4 — Détachement L1", "en": "B1.4 — L1 Detachment"},
    },
    {
        "slug": "b1_5_spiral_revisit",
        "position": 5,
        "labels": {
            "fr": "B1.5 — Spirale + préparation B2",
            "en": "B1.5 — Spiral Revisit + B2 Entry-Test Prep",
        },
    },
]


# (phase_slug, position_in_phase, cluster_slug, label_fr, label_en, grammar_topic)
CLUSTERS: list[tuple[str, int, str, str, str, str]] = [
    # Phase B1.1 — Tense Mastery (4 clusters, global C1–C4)
    ("b1_1_tense_mastery", 1, "B1.1.C1",
        "Imparfait vs Passé composé", "Imparfait vs Passé composé",
        "Imparfait vs passé composé"),
    ("b1_1_tense_mastery", 2, "B1.1.C2",
        "Plus-que-parfait", "Plus-que-parfait",
        "Plus-que-parfait"),
    ("b1_1_tense_mastery", 3, "B1.1.C3",
        "Futur simple + Futur antérieur", "Futur simple + Futur antérieur",
        "Futur simple et futur antérieur"),
    ("b1_1_tense_mastery", 4, "B1.1.C4",
        "Conditionnel présent (intro)", "Conditionnel présent (intro)",
        "Conditionnel présent"),

    # Phase B1.2 — Pronoun Automation (5 clusters, global C5–C9)
    ("b1_2_pronoun_automation", 1, "B1.2.C5",
        "COD", "COD",
        "Pronoms COD"),
    ("b1_2_pronoun_automation", 2, "B1.2.C6",
        "COI", "COI",
        "Pronoms COI"),
    ("b1_2_pronoun_automation", 3, "B1.2.C7",
        "Y et EN", "Y et EN",
        "Pronoms y / en"),
    ("b1_2_pronoun_automation", 4, "B1.2.C8",
        "Doubles pronoms", "Doubles pronoms",
        "Doubles pronoms"),
    ("b1_2_pronoun_automation", 5, "B1.2.C9",
        "Pronoms toniques", "Pronoms toniques",
        "Pronoms toniques"),

    # Phase B1.3 — Subordination (4 clusters, global C10–C13)
    ("b1_3_subordination", 1, "B1.3.C10",
        "Pronoms relatifs simples", "Pronoms relatifs simples",
        "Pronoms relatifs (qui, que, dont, où)"),
    ("b1_3_subordination", 2, "B1.3.C11",
        "Connecteurs intermédiaires", "Connecteurs intermédiaires",
        "Connecteurs intermédiaires"),
    ("b1_3_subordination", 3, "B1.3.C12",
        "Discours indirect au présent", "Discours indirect au présent",
        "Discours indirect au présent"),
    ("b1_3_subordination", 4, "B1.3.C13",
        "Expression de la cause", "Expression de la cause",
        "Expression de la cause"),

    # Phase B1.4 — L1 Detachment (5 clusters, global C14–C18)
    ("b1_4_l1_detachment", 1, "B1.4.C14",
        "Verbes-prépositions à/de + infinitif", "Verb-preposition pairs (à/de + infinitive)",
        "Verbes + à/de + infinitif"),
    ("b1_4_l1_detachment", 2, "B1.4.C15",
        "Prépositions idiomatiques", "Idiomatic prepositions",
        "Prépositions idiomatiques"),
    ("b1_4_l1_detachment", 3, "B1.4.C16",
        "Les Moules", "Les Moules (sentence architecture)",
        "Les Moules — sentence architecture"),
    ("b1_4_l1_detachment", 4, "B1.4.C17",
        "Question formation sous pression", "Question formation under pressure",
        "Question formation"),
    ("b1_4_l1_detachment", 5, "B1.4.C18",
        "Expression de la conséquence", "Expression de la conséquence",
        "Expression de la conséquence"),

    # Phase B1.5 — Spiral Revisit + B2 Entry-Test Prep (4 clusters, global C19–C22)
    ("b1_5_spiral_revisit", 1, "B1.5.C19",
        "Concordance des temps", "Concordance des temps",
        "Concordance des temps"),
    ("b1_5_spiral_revisit", 2, "B1.5.C20",
        "Subjonctif présent (intro)", "Subjonctif présent (intro)",
        "Subjonctif présent"),
    ("b1_5_spiral_revisit", 3, "B1.5.C21",
        "Le gérondif", "Le gérondif",
        "Gérondif"),
    ("b1_5_spiral_revisit", 4, "B1.5.C22",
        "Expression du but", "Expression du but",
        "Expression du but"),
]


def main() -> int:
    db = SessionLocal()
    try:
        existing = db.query(Path).filter(Path.slug == PATH_SLUG).first()
        if existing is not None:
            print(
                f"[seed_p210] path slug={PATH_SLUG} already seeded "
                f"(id={existing.id}); aborting."
            )
            return 0

        path = Path(**PATH_DEF)
        db.add(path)
        db.flush()
        print(f"[seed_p210] created path id={path.id} slug={path.slug}")

        phase_by_slug: dict[str, Phase] = {}
        for ph in PHASES:
            phase = Phase(path_id=path.id, **ph)
            db.add(phase)
            phase_by_slug[ph["slug"]] = phase
        db.flush()
        print(f"[seed_p210] created {len(PHASES)} phases")

        for phase_slug, position, cluster_slug, label_fr, label_en, grammar in CLUSTERS:
            cluster = Cluster(
                slug=cluster_slug,
                labels={"fr": label_fr, "en": label_en},
                grammar_topic=grammar,
                vocabulary_theme_id=None,
                tache_application="tache_3",
                cefr_level="B1",
                is_spiral_revisit=False,
                lesson_format="markdown",
                lesson_markdown="",
                lesson_asset_url="",
                exercise_set=[],
                practice_prompt={},
                detection_rubric={},
            )
            db.add(cluster)
            db.flush()

            phase = phase_by_slug[phase_slug]
            db.add(PathCluster(phase_id=phase.id, cluster_id=cluster.id, position=position))
        db.commit()

        # Verify counts and structure (post-commit, fresh query).
        db.expire_all()
        n_phases = db.query(Phase).filter(Phase.path_id == path.id).count()
        n_clusters_in_path = (
            db.query(PathCluster)
            .join(Phase, PathCluster.phase_id == Phase.id)
            .filter(Phase.path_id == path.id)
            .count()
        )
        print(
            f"[seed_p210] verified: path id={path.id}, "
            f"{n_phases} phases, {n_clusters_in_path} cluster slots"
        )
        if n_phases != 5 or n_clusters_in_path != 22:
            print(
                f"[seed_p210] FAIL — expected 5 phases / 22 clusters, "
                f"got {n_phases} / {n_clusters_in_path}"
            )
            return 1
    finally:
        db.close()

    print("[seed_p210] done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
