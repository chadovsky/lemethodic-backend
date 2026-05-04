"""F-224 — seed writing prompts for the /writing track.

Re-runnable. Idempotent (matches on prompt_text — re-runs don't duplicate).
Run once after Alembic migrations have created `writing_prompts`:

    docker-compose up -d
    alembic upgrade head
    python -m scripts.seed_writing_prompts

Production seeding: run the same command against the prod DB once
F-224 BE ships and Chadi has confirmed the prompt set. Same pattern
as scripts/seed_b1_b2_path.py + scripts/ingest_b1_b2_cluster_content.py.

History: superseded the root-level `seed_writing_prompts.py` from
the pre-rebrand era (Base.metadata.create_all + ASCII-stripped
French). This file restores correct accents, drops the schema-create
(Alembic owns it post-F-077), and lives under `scripts/` per the
post-rebrand convention.

Phase 1 inventory: 7 B1 + 7 B2 + 4 C1 = 18 prompts across argumentative
/ essay / formal_letter / opinion_essay types.
"""
from __future__ import annotations

import sys

from app.database import SessionLocal
# Import models.User first so SQLAlchemy can resolve WritingSubmission's
# user relationship at mapper-configuration time. Side-effect import; the
# `User` symbol itself is unused here but the module load registers User
# in the declarative base.
from app.models.models import User as _User  # noqa: F401
from app.models.writing import WritingPrompt


PROMPTS: list[dict] = [
    # ── B1 (7 prompts) ────────────────────────────────────────────
    {
        "level": "B1",
        "theme": "Vie quotidienne",
        "prompt_type": "formal_letter",
        "prompt_text": "Vous avez commandé un produit en ligne mais vous avez reçu le mauvais article. Écrivez une lettre au service client pour expliquer le problème et demander un échange ou un remboursement. (160-180 mots)",
        "min_words": 160,
        "max_words": 180,
        "time_limit_minutes": 30,
    },
    {
        "level": "B1",
        "theme": "Éducation",
        "prompt_type": "essay",
        "prompt_text": "Un magazine pour jeunes vous demande d'écrire un article sur les avantages et les inconvénients des cours en ligne. Donnez votre opinion avec des exemples concrets. (160-180 mots)",
        "min_words": 160,
        "max_words": 180,
        "time_limit_minutes": 30,
    },
    {
        "level": "B1",
        "theme": "Société",
        "prompt_type": "argumentative",
        "prompt_text": "Pensez-vous que les transports en commun devraient être gratuits pour tout le monde ? Justifiez votre point de vue avec des arguments et des exemples. (160-180 mots)",
        "min_words": 160,
        "max_words": 180,
        "time_limit_minutes": 30,
    },
    {
        "level": "B1",
        "theme": "Travail",
        "prompt_type": "formal_letter",
        "prompt_text": "Vous souhaitez faire un stage dans une entreprise francophone. Écrivez une lettre de motivation dans laquelle vous vous présentez, expliquez vos compétences et votre motivation. (160-180 mots)",
        "min_words": 160,
        "max_words": 180,
        "time_limit_minutes": 30,
    },
    {
        "level": "B1",
        "theme": "Société",
        "prompt_type": "opinion_essay",
        "prompt_text": "L'argent fait-il le bonheur ? Qu'en pensez-vous ?",
        "min_words": 150,
        "max_words": 200,
        "time_limit_minutes": 30,
    },
    {
        "level": "B1",
        "theme": "Technologie",
        "prompt_type": "argumentative",
        "prompt_text": "Les enfants passent-ils trop de temps devant les écrans ?",
        "min_words": 150,
        "max_words": 200,
        "time_limit_minutes": 30,
    },
    {
        "level": "B1",
        "theme": "Santé",
        "prompt_type": "argumentative",
        "prompt_text": "Comment inciter les gens à faire davantage de sport ?",
        "min_words": 150,
        "max_words": 200,
        "time_limit_minutes": 30,
    },

    # ── B2 (7 prompts) ────────────────────────────────────────────
    {
        "level": "B2",
        "theme": "Technologie",
        "prompt_type": "argumentative",
        "prompt_text": "L'intelligence artificielle représente-t-elle une menace ou une opportunité pour le marché du travail ? Présentez les deux points de vue et donnez votre opinion personnelle argumentée. (250-300 mots)",
        "min_words": 250,
        "max_words": 300,
        "time_limit_minutes": 45,
    },
    {
        "level": "B2",
        "theme": "Environnement",
        "prompt_type": "formal_letter",
        "prompt_text": "En tant que résident de votre quartier, écrivez une lettre au maire pour proposer des mesures concrètes afin de réduire la pollution et améliorer la qualité de vie. Structurez votre lettre de manière formelle. (250-300 mots)",
        "min_words": 250,
        "max_words": 300,
        "time_limit_minutes": 45,
    },
    {
        "level": "B2",
        "theme": "Culture",
        "prompt_type": "essay",
        "prompt_text": "Les réseaux sociaux ont-ils transformé notre rapport à la culture et à l'art ? Analysez les effets positifs et négatifs de cette évolution en vous appuyant sur des exemples précis. (250-300 mots)",
        "min_words": 250,
        "max_words": 300,
        "time_limit_minutes": 45,
    },
    {
        "level": "B2",
        "theme": "Société",
        "prompt_type": "argumentative",
        "prompt_text": "Le télétravail devrait-il devenir la norme dans les entreprises ? Discutez les avantages et les limites de ce mode de travail en prenant position de manière argumentée. (250-300 mots)",
        "min_words": 250,
        "max_words": 300,
        "time_limit_minutes": 45,
    },
    {
        "level": "B2",
        "theme": "Technologie",
        "prompt_type": "argumentative",
        "prompt_text": "Les réseaux sociaux rendent-ils les gens solitaires, ou permettent-ils de créer des liens ?",
        "min_words": 200,
        "max_words": 250,
        "time_limit_minutes": 45,
    },
    {
        "level": "B2",
        "theme": "Société",
        "prompt_type": "argumentative",
        "prompt_text": "Vivre en ville est plus stressant qu'à la campagne. Êtes-vous d'accord ?",
        "min_words": 200,
        "max_words": 250,
        "time_limit_minutes": 45,
    },
    {
        "level": "B2",
        "theme": "Technologie",
        "prompt_type": "argumentative",
        "prompt_text": "Peut-on vivre sans technologie ?",
        "min_words": 200,
        "max_words": 250,
        "time_limit_minutes": 45,
    },

    # ── C1 (4 prompts) ────────────────────────────────────────────
    {
        "level": "C1",
        "theme": "Société",
        "prompt_type": "argumentative",
        "prompt_text": "Dans quelle mesure la liberté d'expression doit-elle être limitée dans une démocratie ? Appuyez votre réflexion sur des exemples précis et proposez une synthèse nuancée de la question. (350-400 mots)",
        "min_words": 350,
        "max_words": 400,
        "time_limit_minutes": 60,
    },
    {
        "level": "C1",
        "theme": "Éducation",
        "prompt_type": "essay",
        "prompt_text": "Le système éducatif actuel prépare-t-il adéquatement les jeunes aux défis du XXIe siècle ? Analysez les forces et les faiblesses du modèle éducatif et proposez des pistes de réforme argumentées. (350-400 mots)",
        "min_words": 350,
        "max_words": 400,
        "time_limit_minutes": 60,
    },
    {
        "level": "C1",
        "theme": "Environnement",
        "prompt_type": "formal_letter",
        "prompt_text": "En tant que représentant d'une association écologiste, rédigez une lettre ouverte à la presse dans laquelle vous dénoncez l'inaction des gouvernements face au changement climatique et proposez un programme d'action concret. (350-400 mots)",
        "min_words": 350,
        "max_words": 400,
        "time_limit_minutes": 60,
    },
    {
        "level": "C1",
        "theme": "Technologie",
        "prompt_type": "essay",
        "prompt_text": "La surveillance numérique est-elle compatible avec les valeurs démocratiques ? À travers une analyse des enjeux éthiques, politiques et sociaux, développez une argumentation structurée sur cette question. (350-400 mots)",
        "min_words": 350,
        "max_words": 400,
        "time_limit_minutes": 60,
    },
]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    db = SessionLocal()
    try:
        added = 0
        skipped = 0
        for p in PROMPTS:
            existing = (
                db.query(WritingPrompt)
                .filter(WritingPrompt.prompt_text == p["prompt_text"])
                .first()
            )
            if existing is not None:
                skipped += 1
                continue
            db.add(WritingPrompt(**p))
            added += 1
        db.commit()

        total = db.query(WritingPrompt).count()
        print(f"writing prompts: +{added} added, {skipped} unchanged. Total: {total}")
        for level in ("B1", "B2", "C1"):
            n = db.query(WritingPrompt).filter(WritingPrompt.level == level).count()
            print(f"  {level}: {n}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
