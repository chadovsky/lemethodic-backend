"""F-053 — seed the 16 Le Raccourci lessons with PLACEHOLDER content.

Every short description + detailed content field below is generic copy
that keeps the shape of the product working end-to-end. Chadi replaces
each with his real tutoring material before launch. The locked
sequence (lesson_number + prerequisite) is the only thing that's
authoritative here.

Placeholder markers (grep these):
    # CHADI: replace with your real lesson description before Day 7
    # CHADI: replace with your tutoring materials
    # CHADI: replace with your real adapted content
    # CHADI: future work — Spanish detailed content low priority

Idempotent: matches by ``code``. Re-running preserves non-empty fields
that Chadi has already hand-edited (best_short + detailed paths) —
nothing stomps on manual work.

Usage from project root:
    python -m scripts.seed_raccourci_lessons
"""
from __future__ import annotations

import sys

from app.database import SessionLocal
from app.models.models import RaccourciLesson


# ─── lesson payloads ─────────────────────────────────────────────
# CHADI: the titles below are the names from your curriculum doc.
# The short_description + detailed_content fields are placeholders.


def _fr_desc(title: str) -> str:
    # CHADI: replace with your real lesson description before Day 7
    return (
        f"Leçon dédiée à {title.lower()}. Le point de friction principal pour "
        f"les anglophones est expliqué pas à pas, avec des exemples avant/après "
        f"qui mettent en lumière les erreurs fréquentes. Un quiz de 5 questions "
        f"valide la compréhension."
    )


def _en_desc(title_en: str) -> str:
    # CHADI: replace with your real lesson description before Day 7
    return (
        f"Lesson on {title_en.lower()}. Walks through the main sticking point "
        f"for English speakers with before/after examples that highlight the "
        f"habitual mistakes. Five-question quiz confirms you've got it."
    )


def _es_desc(title_es: str) -> str:
    # CHADI: replace with your real lesson description before Day 7
    return (
        f"Lección sobre {title_es.lower()}. Repasa el punto conflictivo para "
        f"quienes vienen del inglés con ejemplos antes/después. Cuestionario de "
        f"5 preguntas para confirmar."
    )


def _fr_detail(title: str) -> str:
    # CHADI: replace with your tutoring materials. The placeholder is
    # generic; your real content is the moat.
    return (
        f"## {title}\n\n"
        f"Cette leçon aborde {title.lower()} dans le contexte de la production "
        f"orale TCF. On y présente d'abord la règle principale, puis on détaille "
        f"les cas limites que vos étudiants anglophones confondent systématiquement. "
        f"Les exemples sont tirés de situations d'examen réelles.\n\n"
        f"**À retenir :** la version courte que l'étudiant doit pouvoir se "
        f"réciter avant de passer au quiz.\n\n"
        f"**Exemples commentés :**\n"
        f"- Exemple correct n°1 (placeholder).\n"
        f"- Exemple incorrect n°1 (placeholder) — pourquoi ça ne passe pas.\n"
        f"- Exemple correct n°2 (placeholder).\n"
    )


def _en_detail(title_en: str) -> str:
    # CHADI: replace with your real adapted content. The English-facing
    # detailed content is NOT a straight translation — it specifically
    # addresses what English speakers get wrong and why.
    return (
        f"## {title_en}\n\n"
        f"This lesson walks you through {title_en.lower()} with the English-"
        f"speaker pitfalls called out explicitly. If you find yourself mapping "
        f"the English rule straight onto French, stop — the whole point of "
        f"this lesson is that the mapping breaks in a specific way.\n\n"
        f"**Short version:** the rule as Chadi summarises it in tutoring.\n\n"
        f"**What you'll want to catch yourself on:**\n"
        f"- The English habit you bring in by default (placeholder).\n"
        f"- The French form you should land on instead (placeholder).\n"
        f"- Why the two aren't symmetric (placeholder).\n"
    )


# CHADI: future work — Spanish detailed content low priority
_ES_DETAIL = None


LESSONS = [
    {"lesson_number": 1,  "code": "conjugaison",
     "title_fr": "Conjugaison", "title_en": "Conjugation", "title_es": "Conjugación",
     "duration": 15},
    {"lesson_number": 2,  "code": "les_articles",
     "title_fr": "Les articles", "title_en": "Articles", "title_es": "Los artículos",
     "duration": 15},
    {"lesson_number": 3,  "code": "feminin_masculin",
     "title_fr": "Féminin / masculin", "title_en": "Feminine / masculine", "title_es": "Femenino / masculino",
     "duration": 15},
    {"lesson_number": 4,  "code": "articles_avances",
     "title_fr": "Les articles (suite)", "title_en": "Articles (continued)", "title_es": "Los artículos (continuación)",
     "duration": 15},
    {"lesson_number": 5,  "code": "prepositions",
     "title_fr": "Prépositions", "title_en": "Prepositions", "title_es": "Preposiciones",
     "duration": 15},
    {"lesson_number": 6,  "code": "pronoms_relatifs",
     "title_fr": "Pronoms relatifs", "title_en": "Relative pronouns", "title_es": "Pronombres relativos",
     "duration": 15},
    {"lesson_number": 7,  "code": "what_question",
     "title_fr": "Comment dire « what » — en question",
     "title_en": "How to say 'what' — as a question",
     "title_es": "Cómo decir 'what' — en pregunta",
     "duration": 15},
    {"lesson_number": 8,  "code": "what_non_question",
     "title_fr": "Comment dire « what » — hors question",
     "title_en": "How to say 'what' — non-question",
     "title_es": "Cómo decir 'what' — no-pregunta",
     "duration": 15},
    {"lesson_number": 9,  "code": "discours_indirect_present",
     "title_fr": "Discours indirect au présent",
     "title_en": "Reported speech (present)",
     "title_es": "Discurso indirecto (presente)",
     "duration": 15},
    {"lesson_number": 10, "code": "conditionnel_pqp_revision",
     "title_fr": "Conditionnel + plus-que-parfait (révision)",
     "title_en": "Conditional + pluperfect (review)",
     "title_es": "Condicional + pluscuamperfecto (repaso)",
     "duration": 15},
    {"lesson_number": 11, "code": "discours_indirect_passe",
     "title_fr": "Discours indirect au passé",
     "title_en": "Reported speech (past)",
     "title_es": "Discurso indirecto (pasado)",
     "duration": 15},
    {"lesson_number": 12, "code": "subjonctif_mise_en_relief",
     "title_fr": "Subjonctif + mise en relief",
     "title_en": "Subjunctive + emphasis structures",
     "title_es": "Subjuntivo + estructuras de énfasis",
     "duration": 25},
    {"lesson_number": 13, "code": "voix_passive",
     "title_fr": "Voix passive (4 structures)",
     "title_en": "Passive voice (4 structures)",
     "title_es": "Voz pasiva (4 estructuras)",
     "duration": 25},
    {"lesson_number": 14, "code": "adverbes",
     "title_fr": "Adverbes", "title_en": "Adverbs", "title_es": "Adverbios",
     "duration": 15},
    {"lesson_number": 15, "code": "nominalisation",
     "title_fr": "Nominalisation", "title_en": "Nominalization", "title_es": "Nominalización",
     "duration": 15},
    {"lesson_number": 16, "code": "gerondif",
     "title_fr": "Gérondif", "title_en": "Gerund", "title_es": "Gerundio",
     "duration": 15},
]


def _apply_row(session, payload: dict) -> str:
    code = payload["code"]
    existing = (
        session.query(RaccourciLesson)
        .filter(RaccourciLesson.code == code)
        .first()
    )

    ln = payload["lesson_number"]
    fields_structural = {
        "lesson_number": ln,
        "title_fr": payload["title_fr"],
        "title_en": payload["title_en"],
        "title_es": payload["title_es"],
        "prerequisite_lesson_number": None if ln == 1 else ln - 1,
        "estimated_duration_minutes": payload["duration"],
        "is_active": True,
    }

    # Content fields: never stomp a non-empty value on re-seed —
    # Chadi's hand edits are sacred.
    def _fill_if_empty(obj, attr, new_value):
        current = getattr(obj, attr, None)
        if not (current or "").strip() if isinstance(current, str) else (current is None):
            setattr(obj, attr, new_value)

    if existing:
        for k, v in fields_structural.items():
            setattr(existing, k, v)
        _fill_if_empty(existing, "short_description_fr", _fr_desc(payload["title_fr"]))
        _fill_if_empty(existing, "short_description_en", _en_desc(payload["title_en"]))
        _fill_if_empty(existing, "short_description_es", _es_desc(payload["title_es"]))
        _fill_if_empty(existing, "detailed_content_fr", _fr_detail(payload["title_fr"]))
        _fill_if_empty(existing, "detailed_content_en", _en_detail(payload["title_en"]))
        if existing.detailed_content_es is None:
            existing.detailed_content_es = _ES_DETAIL  # stays None; explicit for clarity
        return "updated"

    session.add(RaccourciLesson(
        code=code,
        short_description_fr=_fr_desc(payload["title_fr"]),
        short_description_en=_en_desc(payload["title_en"]),
        short_description_es=_es_desc(payload["title_es"]),
        detailed_content_fr=_fr_detail(payload["title_fr"]),
        detailed_content_en=_en_detail(payload["title_en"]),
        detailed_content_es=_ES_DETAIL,
        **fields_structural,
    ))
    return "inserted"


def main() -> int:
    session = SessionLocal()
    try:
        counts = {"inserted": 0, "updated": 0}
        for payload in LESSONS:
            counts[_apply_row(session, payload)] += 1
        session.commit()
        print(
            f"Le Raccourci lessons seeded: "
            f"{counts['inserted']} inserted, {counts['updated']} updated. "
            f"(16 total. ES detailed_content intentionally null. "
            f"CHADI: replace placeholder content before launch.)"
        )
        return 0
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
