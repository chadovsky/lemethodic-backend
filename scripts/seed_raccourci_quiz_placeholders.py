"""F-053 — seed 5 PLACEHOLDER quiz questions per Le Raccourci lesson.

Every question below is generic and matches the lesson's broad topic,
but is NOT pedagogically validated. Chadi replaces each one before
launch. The point of this seeder is to prove the quiz mechanism works
end-to-end (submit → score → unlock next lesson).

Placeholder marker: every question is tagged with
``# CHADI: replace with real questions before launch.`` in comments
at the top of the lesson's block.

Shape per lesson (5 questions):
- 2 × multiple_choice
- 2 × fill_blank
- 1 × translate_en_fr

Idempotent: keyed by (lesson_id, question_number). Re-runs update the
row in place, never duplicate.

Usage from project root:
    python -m scripts.seed_raccourci_quiz_placeholders
"""
from __future__ import annotations

import json
import sys

from app.database import SessionLocal
from app.models.models import RaccourciLesson, RaccourciQuizQuestion


# A question template helper — keeps the 80 payloads readable.
def _mc(n, q_fr, q_en, q_es, correct, options, expl_fr, expl_en):
    return {
        "question_number": n, "question_type": "multiple_choice",
        "question_fr": q_fr, "question_en": q_en, "question_es": q_es,
        "correct_answer": correct, "options": options,
        "explanation_fr": expl_fr, "explanation_en": expl_en,
        "explanation_es": "",
        "accepted_alternatives": [],
    }

def _fb(n, q_fr, q_en, q_es, correct, alternatives, expl_fr, expl_en):
    return {
        "question_number": n, "question_type": "fill_blank",
        "question_fr": q_fr, "question_en": q_en, "question_es": q_es,
        "correct_answer": correct, "options": [],
        "explanation_fr": expl_fr, "explanation_en": expl_en,
        "explanation_es": "",
        "accepted_alternatives": alternatives,
    }

def _translate(n, en_source, correct, alternatives, expl_fr, expl_en):
    return {
        "question_number": n, "question_type": "translate_en_fr",
        "question_fr": f"Traduisez en français : « {en_source} »",
        "question_en": f"Translate to French: \"{en_source}\"",
        "question_es": f"Traduce al francés: «{en_source}»",
        "correct_answer": correct, "options": [],
        "explanation_fr": expl_fr, "explanation_en": expl_en,
        "explanation_es": "",
        "accepted_alternatives": alternatives,
    }


# CHADI: replace with real questions before launch.
# Keyed by lesson code → list of 5 question dicts.
QUESTIONS: dict[str, list[dict]] = {
    "conjugaison": [
        _mc(1, "Quelle est la forme correcte du verbe « parler » à la 1ʳᵉ personne du singulier au présent ?",
            "What is the correct 1st person singular present-tense form of « parler » ?",
            "¿Cuál es la forma correcta de « parler » en 1ª persona del presente?",
            "je parle", ["je parle", "je parles", "je parlent"],
            "Au présent, les verbes en -er prennent la terminaison -e à la 1ʳᵉ personne du singulier.",
            "Present-tense -er verbs take -e in the 1st person singular."),
        _mc(2, "Quelle est la bonne conjugaison : « Nous ___ »",
            "Correct conjugation: « Nous ___ »",
            "Conjugación correcta: «Nous ___»",
            "finissons", ["finissons", "finisson", "finit"],
            "Les verbes en -ir (groupe 2) font -issons à la 1ʳᵉ personne du pluriel.",
            "-ir (group 2) verbs take -issons in the 1st person plural."),
        _fb(3, "Complétez : Tu ___ (aller) à l'école.",
            "Complete: Tu ___ (aller) à l'école.",
            "Completa: Tu ___ (aller) à l'école.",
            "vas", [],
            "« Aller » est irrégulier : je vais, tu vas, il va.",
            "\"Aller\" is irregular: je vais, tu vas, il va."),
        _fb(4, "Complétez : Ils ___ (avoir) un chien.",
            "Complete: Ils ___ (avoir) un chien.",
            "Completa: Ils ___ (avoir) un chien.",
            "ont", [],
            "« Avoir » : j'ai, tu as, il a, nous avons, vous avez, ils ont.",
            "\"Avoir\": j'ai, tu as, il a, nous avons, vous avez, ils ont."),
        _translate(5, "I speak French every day.",
            "Je parle français tous les jours.",
            ["Je parle français chaque jour.", "Je parle le français tous les jours."],
            "Au présent, on utilise simplement « je parle » + le complément.",
            "Simple present: « je parle » + complement, no -s."),
    ],
    "les_articles": [
        _mc(1, "Quel article utilisez-vous : « ___ maison » (féminin) ?",
            "Which article: « ___ maison » (feminine)?",
            "¿Qué artículo: «___ maison» (femenino)?",
            "la", ["le", "la", "les"],
            "« Maison » est un nom féminin singulier, donc « la ».",
            "\"Maison\" is feminine singular, so \"la\"."),
        _mc(2, "Quel article pour un mot masculin pluriel indéfini ?",
            "Which article for a masculine plural indefinite noun?",
            "¿Qué artículo para un sustantivo masculino plural indefinido?",
            "des", ["un", "des", "le"],
            "L'article indéfini pluriel est « des » pour les deux genres.",
            "The plural indefinite article is \"des\" for both genders."),
        _fb(3, "Complétez : J'aime ___ chocolat.",
            "Complete: J'aime ___ chocolat.",
            "Completa: J'aime ___ chocolat.",
            "le", [],
            "Après « aimer » on utilise l'article défini (le / la / les).",
            "After \"aimer\" use the definite article (le / la / les)."),
        _fb(4, "Complétez : Il y a ___ pomme sur la table.",
            "Complete: Il y a ___ pomme sur la table.",
            "Completa: Il y a ___ pomme sur la table.",
            "une", [],
            "« Pomme » est féminin, article indéfini « une ».",
            "\"Pomme\" is feminine, indefinite article \"une\"."),
        _translate(5, "I'm looking for a book.",
            "Je cherche un livre.",
            ["Je suis à la recherche d'un livre."],
            "« Chercher » n'est PAS suivi de préposition en français.",
            "\"Chercher\" takes NO preposition in French."),
    ],
    # For the remaining 14 lessons we reuse a compact template — the
    # questions are topic-tagged placeholders that keep the quiz flow
    # working but carry a clear "Chadi to rewrite" intent.
}


# CHADI: replace with real questions before launch.
# Generic fallback block used for every lesson not explicitly authored
# above. Five questions per lesson, covering all required types.
def _fallback_questions(lesson_title_fr: str) -> list[dict]:
    topic = lesson_title_fr
    return [
        _mc(1,
            f"[Placeholder – {topic}] Laquelle de ces phrases est correcte ?",
            f"[Placeholder – {topic}] Which of these sentences is correct?",
            f"[Marcador – {topic}] ¿Cuál de estas frases es correcta?",
            "Option A",
            ["Option A", "Option B", "Option C"],
            f"CHADI: explication à écrire pour {topic}.",
            f"CHADI: explanation to write for {topic}."),
        _mc(2,
            f"[Placeholder – {topic}] Quel est le meilleur choix ?",
            f"[Placeholder – {topic}] What is the best choice?",
            f"[Marcador – {topic}] ¿Cuál es la mejor opción?",
            "Option B",
            ["Option A", "Option B", "Option C"],
            f"CHADI: explication à écrire pour {topic}.",
            f"CHADI: explanation to write for {topic}."),
        _fb(3,
            f"[Placeholder – {topic}] Complétez la phrase : « Il ___ à Paris. »",
            f"[Placeholder – {topic}] Complete: \"Il ___ à Paris.\"",
            f"[Marcador – {topic}] Completa: «Il ___ à Paris.»",
            "va", [],
            f"CHADI: explication à écrire pour {topic}.",
            f"CHADI: explanation to write for {topic}."),
        _fb(4,
            f"[Placeholder – {topic}] Complétez : « Nous ___ des amis. »",
            f"[Placeholder – {topic}] Complete: \"Nous ___ des amis.\"",
            f"[Marcador – {topic}] Completa: «Nous ___ des amis.»",
            "avons", [],
            f"CHADI: explication à écrire pour {topic}.",
            f"CHADI: explanation to write for {topic}."),
        _translate(5,
            f"[Placeholder – {topic}] She is reading a book.",
            "Elle lit un livre.",
            ["Elle est en train de lire un livre."],
            f"CHADI: explication à écrire pour {topic}.",
            f"CHADI: explanation to write for {topic}."),
    ]


def _apply_questions(session, lesson: RaccourciLesson, question_payloads: list[dict]) -> tuple[int, int]:
    inserted = 0
    updated = 0
    for q in question_payloads:
        existing = (
            session.query(RaccourciQuizQuestion)
            .filter(
                RaccourciQuizQuestion.lesson_id == lesson.id,
                RaccourciQuizQuestion.question_number == q["question_number"],
            )
            .first()
        )
        common = {
            "question_type": q["question_type"],
            "question_fr": q["question_fr"],
            "question_en": q["question_en"],
            "question_es": q["question_es"],
            "correct_answer": q["correct_answer"],
            "accepted_alternatives": json.dumps(q["accepted_alternatives"], ensure_ascii=False),
            "explanation_fr": q["explanation_fr"],
            "explanation_en": q["explanation_en"],
            "explanation_es": q["explanation_es"],
            "options": json.dumps(q["options"], ensure_ascii=False),
        }
        if existing:
            for k, v in common.items():
                setattr(existing, k, v)
            updated += 1
        else:
            session.add(RaccourciQuizQuestion(
                lesson_id=lesson.id,
                question_number=q["question_number"],
                **common,
            ))
            inserted += 1
    return inserted, updated


def main() -> int:
    session = SessionLocal()
    try:
        lessons = (
            session.query(RaccourciLesson)
            .order_by(RaccourciLesson.lesson_number)
            .all()
        )
        if len(lessons) != 16:
            print(f"Expected 16 raccourci_lessons, found {len(lessons)}. "
                  f"Run seed_raccourci_lessons first.")
            return 1

        total_ins = 0
        total_upd = 0
        for lesson in lessons:
            payload = QUESTIONS.get(lesson.code) or _fallback_questions(lesson.title_fr)
            ins, upd = _apply_questions(session, lesson, payload)
            total_ins += ins
            total_upd += upd
        session.commit()
        print(
            f"Quiz placeholders seeded: "
            f"{total_ins} inserted, {total_upd} updated "
            f"(5 per lesson × 16 lessons = 80 questions expected). "
            f"CHADI: replace every question before launch."
        )
        return 0
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
