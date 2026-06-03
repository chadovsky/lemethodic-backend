"""Seed scoring_rubrics with tcf_canada starting weights.

Idempotent upsert on (exam, level, couche_key). Safe to re-run — existing
rows are updated in place; weight/score_mapping are overwritten to the values
here.

Usage (LOCAL/DEV only — gate #7 applies for prod):
    python -m scripts.seed_scoring_rubrics

Prod execution: Chadi runs via DO console terminal after seed ASK approval.

Weights per level (must sum to 1.0):
    a2: le_propos 0.350, le_plan 0.100, la_construction 0.350,
        les_pieges_anglais 0.150, la_musique 0.050
    b1: le_propos 0.250, le_plan 0.200, la_construction 0.250,
        les_pieges_anglais 0.200, la_musique 0.100
    c1: le_propos 0.150, le_plan 0.250, la_construction 0.150,
        les_pieges_anglais 0.200, la_musique 0.250

These are starting values; calibration is a Chadi task tracked separately.
"""
import json
import sys
from decimal import Decimal

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import SessionLocal
from app.models.scoring_rubrics import ScoringRubric

SCORE_MAPPING_PLACEHOLDER = {"A": "0-4", "B": "5-9", "C": "10-14", "D": "15-20"}

ROWS = [
    # a2
    dict(exam="tcf_canada", level="a2", couche_key="le_propos",          weight=Decimal("0.350")),
    dict(exam="tcf_canada", level="a2", couche_key="le_plan",            weight=Decimal("0.100")),
    dict(exam="tcf_canada", level="a2", couche_key="la_construction",    weight=Decimal("0.350")),
    dict(exam="tcf_canada", level="a2", couche_key="les_pieges_anglais", weight=Decimal("0.150")),
    dict(exam="tcf_canada", level="a2", couche_key="la_musique",         weight=Decimal("0.050")),
    # b1
    dict(exam="tcf_canada", level="b1", couche_key="le_propos",          weight=Decimal("0.250")),
    dict(exam="tcf_canada", level="b1", couche_key="le_plan",            weight=Decimal("0.200")),
    dict(exam="tcf_canada", level="b1", couche_key="la_construction",    weight=Decimal("0.250")),
    dict(exam="tcf_canada", level="b1", couche_key="les_pieges_anglais", weight=Decimal("0.200")),
    dict(exam="tcf_canada", level="b1", couche_key="la_musique",         weight=Decimal("0.100")),
    # c1
    dict(exam="tcf_canada", level="c1", couche_key="le_propos",          weight=Decimal("0.150")),
    dict(exam="tcf_canada", level="c1", couche_key="le_plan",            weight=Decimal("0.250")),
    dict(exam="tcf_canada", level="c1", couche_key="la_construction",    weight=Decimal("0.150")),
    dict(exam="tcf_canada", level="c1", couche_key="les_pieges_anglais", weight=Decimal("0.200")),
    dict(exam="tcf_canada", level="c1", couche_key="la_musique",         weight=Decimal("0.250")),
]


def _verify_weights() -> None:
    """Assert weights sum to 1.0 per (exam, level) before touching the DB."""
    from collections import defaultdict
    sums: dict = defaultdict(Decimal)
    for row in ROWS:
        sums[(row["exam"], row["level"])] += row["weight"]
    errors = []
    for key, total in sums.items():
        if total != Decimal("1.000"):
            errors.append(f"  {key}: sum={total}")
    if errors:
        print("WEIGHT SUM ERROR — aborting:")
        for e in errors:
            print(e)
        sys.exit(1)


def main() -> None:
    _verify_weights()

    db = SessionLocal()
    try:
        upserted = 0
        for row in ROWS:
            stmt = (
                pg_insert(ScoringRubric)
                .values(
                    exam=row["exam"],
                    level=row["level"],
                    couche_key=row["couche_key"],
                    weight=row["weight"],
                    score_mapping=SCORE_MAPPING_PLACEHOLDER,
                )
                .on_conflict_do_update(
                    constraint="uq_scoring_rubrics_exam_level_couche",
                    set_={
                        "weight": row["weight"],
                        "score_mapping": SCORE_MAPPING_PLACEHOLDER,
                    },
                )
            )
            db.execute(stmt)
            upserted += 1

        db.commit()
        print(f"seed_scoring_rubrics: {upserted} rows upserted for exam=tcf_canada.")

        # Verification: print weight sums per level
        from sqlalchemy import func
        rows = (
            db.query(
                ScoringRubric.level,
                func.sum(ScoringRubric.weight).label("total_weight"),
                func.count(ScoringRubric.id).label("row_count"),
            )
            .filter(ScoringRubric.exam == "tcf_canada")
            .group_by(ScoringRubric.level)
            .order_by(ScoringRubric.level)
            .all()
        )
        print("\nVerification — weight sums per (exam=tcf_canada, level):")
        for r in rows:
            print(f"  level={r.level}  rows={r.row_count}  weight_sum={float(r.total_weight):.3f}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
