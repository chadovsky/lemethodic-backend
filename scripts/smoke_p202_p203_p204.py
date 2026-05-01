"""Smoke test for the P-202/P-203/P-204 migration.

Run with: python -m scripts.smoke_p202_p203_p204
Expected: prints PASS lines and exits 0. Cleans up its own test rows.
"""
from __future__ import annotations

import sys

from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.models import (
    Cluster,
    Path,
    PathCluster,
    Phase,
    Recording,
    User,
    UserClusterEvent,
    UserClusterStatus,
    UserPathEnrollment,
    VocabularyTheme,
)


engine = create_engine(
    "postgresql+psycopg://fluentpath:fluentpath_local_dev@localhost:5432/fluentpath"
)

errors: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    extra = f" -- {detail}" if detail else ""
    print(f"  [{status}] {name}{extra}")
    if not ok:
        errors.append(name)


def main() -> int:
    print("Step 1: 8 new tables exist")
    expected = {
        "vocabulary_themes",
        "clusters",
        "paths",
        "phases",
        "path_clusters",
        "user_path_enrollments",
        "user_cluster_statuses",
        "user_cluster_events",
    }
    with engine.connect() as c:
        rows = c.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = ANY(:t)"
            ),
            {"t": list(expected)},
        ).fetchall()
    found = {r[0] for r in rows}
    check(
        "8 tables present",
        found == expected,
        f"missing: {expected - found}" if expected - found else "all 8",
    )

    print("\nStep 2: vocabulary_themes seed")
    with engine.connect() as c:
        n = c.execute(text("SELECT count(*) FROM vocabulary_themes")).scalar()
    check("27 themes seeded", n == 27, f"got {n}")
    with engine.connect() as c:
        sample = c.execute(
            text("SELECT slug, labels FROM vocabulary_themes WHERE slug = 'temps_climat'")
        ).fetchone()
    check(
        "seed labels JSONB shape",
        sample is not None and "fr" in sample[1] and "en" in sample[1],
        f"labels = {sample[1] if sample else None}",
    )

    print("\nSetup: ensure a test user + recording exist")
    with Session(engine) as s:
        u = s.query(User).filter_by(email="smoke@p202.local").first()
        if not u:
            u = User(email="smoke@p202.local", hashed_password="x", full_name="Smoke")
            s.add(u)
            s.commit()
            s.refresh(u)
        r = s.query(Recording).filter_by(user_id=u.id).first()
        if not r:
            r = Recording(
                user_id=u.id,
                audio_path="smoke/test.wav",
                target_level="B1",
                tache_mode="tache_3",
            )
            s.add(r)
            s.commit()
            s.refresh(r)
        user_id, rec_id = u.id, r.id
    print(f"  user_id={user_id} recording_id={rec_id}")

    print("\nStep 3: ORM round-trip -- VocabularyTheme")
    with Session(engine) as s:
        theme = s.query(VocabularyTheme).filter_by(slug="temps_climat").first()
        theme_id = theme.id
    check(
        "VocabularyTheme readable",
        theme is not None and theme.labels.get("fr").startswith("Le temps"),
    )

    print("\nStep 4: ORM round-trip -- Cluster + Path + Phase + PathCluster")
    with Session(engine) as s:
        cluster = Cluster(
            slug="b1_1_c1_imparfait_pc",
            labels={"fr": "Imparfait vs PC", "en": "Imparfait vs Passe compose"},
            grammar_topic="Imparfait vs PC",
            vocabulary_theme_id=theme_id,
            tache_application="tache_3",
            cefr_level="B1",
            lesson_format="markdown",
            lesson_markdown="# Imparfait vs PC\n\nNarrative tense distinction...",
            detection_rubric={
                "markers": [
                    {
                        "marker_id": "B1.1.C1.a",
                        "name": "Flat narrative",
                        "firing_condition": {
                            "type": "ratio_threshold",
                            "metric": "imparfait_ratio",
                            "operator": "<",
                            "value": 0.15,
                            "context": "narrative_60s+",
                        },
                        "severity": "high",
                        "ceiling_level": "B1",
                    }
                ],
                "status_logic": {
                    "absorbed": "all_markers_silent_for_2_consecutive",
                    "partial": "max_1_marker_firing",
                    "needs_revisit": "2+_markers_firing_OR_high_severity_alone",
                },
            },
        )
        s.add(cluster)
        s.commit()
        s.refresh(cluster)
        cluster_id = cluster.id

        path = Path(
            slug="b1_to_b2",
            labels={"fr": "Stop translating, start structuring", "en": "Stop translating, start structuring"},
            tagline={"fr": "Detacher de l'anglais", "en": "Detach from English"},
            level_start="B1",
            level_target="B2",
            is_active=True,
            estimated_weeks=8,
        )
        s.add(path)
        s.commit()
        s.refresh(path)
        path_id = path.id

        phase = Phase(
            path_id=path_id,
            position=1,
            slug="b1_1_tense_mastery",
            labels={"fr": "Tense mastery", "en": "Tense mastery"},
        )
        s.add(phase)
        s.commit()
        s.refresh(phase)
        phase_id = phase.id

        pc = PathCluster(phase_id=phase_id, cluster_id=cluster_id, position=1)
        s.add(pc)
        s.commit()

        fresh = s.get(Path, path_id)
        rt_ok = (
            len(fresh.phases) == 1
            and len(fresh.phases[0].path_clusters) == 1
            and fresh.phases[0].path_clusters[0].cluster.detection_rubric["markers"][0][
                "marker_id"
            ]
            == "B1.1.C1.a"
        )
    check("Path -> Phase -> PathCluster -> Cluster round-trip", rt_ok)

    print("\nStep 5: ORM round-trip -- UserPathEnrollment + UserClusterStatus + UserClusterEvent")
    with Session(engine) as s:
        enrollment = UserPathEnrollment(
            user_id=user_id,
            path_id=path_id,
            enrolled_at_level="B1",
            enrolled_at_confidence="medium",
            current_phase_id=phase_id,
            current_cluster_id=cluster_id,
            is_active=True,
        )
        s.add(enrollment)
        s.commit()

        status_row = UserClusterStatus(
            user_id=user_id, cluster_id=cluster_id, status="in_progress"
        )
        s.add(status_row)
        s.commit()

        event = UserClusterEvent(
            user_id=user_id,
            cluster_id=cluster_id,
            from_status=None,
            to_status="in_progress",
            triggered_by_recording_id=rec_id,
        )
        s.add(event)
        s.commit()
    check("3 user-progress tables round-trip OK", True)

    print("\nStep 6: Partial unique index -- 2nd active enrollment for same user MUST fail")
    with Session(engine) as s:
        p2 = Path(
            slug="a2_to_b1",
            labels={"fr": "X"},
            tagline={"fr": "X"},
            level_start="A2",
            level_target="B1",
            is_active=False,
        )
        s.add(p2)
        s.commit()
        s.refresh(p2)
        e2 = UserPathEnrollment(
            user_id=user_id, path_id=p2.id, enrolled_at_level="A2", is_active=True
        )
        s.add(e2)
        try:
            s.commit()
            check(
                "partial unique index rejects 2nd active enrollment",
                False,
                "INSERT succeeded -- index not enforcing",
            )
        except IntegrityError:
            check("partial unique index rejects 2nd active enrollment", True)
            s.rollback()

    print("\nStep 7: CHECK constraint -- tache_application='writing' MUST fail")
    with Session(engine) as s:
        bad = Cluster(
            slug="bad_writing_cluster",
            labels={"fr": "X"},
            grammar_topic="X",
            tache_application="writing",
            cefr_level="B1",
            lesson_format="markdown",
        )
        s.add(bad)
        try:
            s.commit()
            check(
                "CHECK ck_clusters_tache_application rejects 'writing'",
                False,
                "INSERT succeeded -- constraint not enforcing",
            )
        except IntegrityError:
            check("CHECK ck_clusters_tache_application rejects 'writing'", True)
            s.rollback()

    print("\nStep 8: composite index ix_user_cluster_events_user_created exists")
    with engine.connect() as c:
        n = c.execute(
            text(
                "SELECT count(*) FROM pg_indexes "
                "WHERE tablename = 'user_cluster_events' "
                "  AND indexname = 'ix_user_cluster_events_user_created'"
            )
        ).scalar()
    check("composite index present", n == 1)

    print("\nStep 9: partial unique index has WHERE clause")
    with engine.connect() as c:
        idx = c.execute(
            text(
                "SELECT indexdef FROM pg_indexes "
                "WHERE indexname = 'uq_user_path_enrollments_one_active'"
            )
        ).scalar()
    check(
        "partial index WHERE is_active = true",
        idx is not None and "is_active = true" in idx,
        f"def: {idx}",
    )

    print("\nCleanup")
    with engine.connect() as c:
        c.execute(text("DELETE FROM user_cluster_events WHERE user_id = :u"), {"u": user_id})
        c.execute(text("DELETE FROM user_cluster_statuses WHERE user_id = :u"), {"u": user_id})
        c.execute(text("DELETE FROM user_path_enrollments WHERE user_id = :u"), {"u": user_id})
        c.execute(text("DELETE FROM path_clusters"))
        c.execute(text("DELETE FROM phases"))
        c.execute(text("DELETE FROM paths"))
        c.execute(text("DELETE FROM clusters"))
        c.execute(text("DELETE FROM recordings WHERE user_id = :u"), {"u": user_id})
        c.execute(text("DELETE FROM users WHERE id = :u"), {"u": user_id})
        c.commit()
    print("  test rows removed")

    print()
    if errors:
        print(f"FAILURES: {errors}")
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
