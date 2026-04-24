"""F-063 — Seed the Tâche 1 opening-prompt catalog with 8 variants.

Each row is a different way the examiner opens the personal-interview
Tâche 1. Intent is identical across rows (open-ended self-presentation);
phrasing varies so repeat sessions feel fresh. Examiner always speaks
French — the EN/ES translations mirror the Tâche 2 scenario pattern and
are reserved for future bilingual-subtitle display.

Idempotency: runs match by ``opening_prompt_fr`` (natural key). Re-running
updates the same rows in place rather than duplicating.

Usage from project root:
    python -m scripts.seed_tache1_openings
"""
from __future__ import annotations

import sys

from app.database import SessionLocal
from app.models.models import Tache1Opening


OPENINGS: list[dict] = [
    {
        "fr": "Bonjour, pouvez-vous vous présenter brièvement ?",
        "en": "Hello, can you briefly introduce yourself?",
        "es": "Hola, ¿puede presentarse brevemente?",
    },
    {
        "fr": "Bonjour, parlez-moi un peu de vous.",
        "en": "Hello, tell me a little about yourself.",
        "es": "Hola, hábleme un poco de usted.",
    },
    {
        "fr": "Bonjour, présentez-vous, s'il vous plaît.",
        "en": "Hello, please introduce yourself.",
        "es": "Hola, preséntese, por favor.",
    },
    {
        "fr": "Bonjour, pouvez-vous me dire qui vous êtes ?",
        "en": "Hello, can you tell me who you are?",
        "es": "Hola, ¿puede decirme quién es usted?",
    },
    {
        "fr": "Bonjour, commencez par vous présenter.",
        "en": "Hello, start by introducing yourself.",
        "es": "Hola, empiece por presentarse.",
    },
    {
        "fr": "Bonjour, dites-moi qui vous êtes et ce que vous faites.",
        "en": "Hello, tell me who you are and what you do.",
        "es": "Hola, dígame quién es y a qué se dedica.",
    },
    {
        "fr": "Bonjour, pouvez-vous me parler un peu de votre parcours ?",
        "en": "Hello, can you tell me a bit about your background?",
        "es": "Hola, ¿puede hablarme un poco de su trayectoria?",
    },
    {
        "fr": "Bonjour, présentez-vous en quelques mots.",
        "en": "Hello, introduce yourself in a few words.",
        "es": "Hola, preséntese en pocas palabras.",
    },
]


def _apply_row(session, payload: dict) -> str:
    existing = (
        session.query(Tache1Opening)
        .filter(Tache1Opening.opening_prompt_fr == payload["fr"])
        .first()
    )
    fields = {
        "opening_prompt_fr": payload["fr"],
        "opening_prompt_en": payload["en"],
        "opening_prompt_es": payload["es"],
        "is_active": True,
    }
    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
        return "updated"
    session.add(Tache1Opening(**fields))
    return "inserted"


def main() -> int:
    session = SessionLocal()
    try:
        counts = {"inserted": 0, "updated": 0}
        for payload in OPENINGS:
            counts[_apply_row(session, payload)] += 1
        session.commit()
        print(
            f"Seeded Tâche 1 openings: "
            f"{counts['inserted']} inserted, {counts['updated']} updated."
        )
        return 0
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
