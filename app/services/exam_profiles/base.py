"""
Exam profile contract.

An ExamProfile is a plain-data description of an evaluation framework (TCF
Canada, DELF B2, FIDE, AP French, interview prep, ...). Profiles are
consumed by analysis.py and the router layer; they never import from those
modules, so adding a new profile is additive: drop a new module in this
package, register it in __init__.py, done.

A profile supplies:
  - a criteria list for each skill (oral / writing)
  - a score-to-level mapping (CEFR or any other primary scale)
  - an optional secondary framework (CLB for TCF Canada, none for DELF)
  - a prompt fragment that teaches Claude how examiners weight this framework
  - ui label metadata so the frontend can render it without knowing the profile
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional


DEFAULT_EXAMINER_VOICE_GUIDE = """Voix d'examinateur neutre et formelle.
Registre d'un correcteur officiel : assessment-only, aucun coaching.
Ne cite pas les mots de l'étudiant. Ne propose pas de transformation.
Lexique d'évaluation professionnelle : « niveau atteint / partiellement
atteint / non atteint », « maîtrise », « lacune », « tolérance »,
« registre adapté », « progression claire »."""


DEFAULT_TEACHER_VOICE_GUIDE = """La voix Professeur est universelle : pédagogie
avant tout. Tu N'UTILISES JAMAIS la terminologie technique interne dans
les champs teacher_coaching. Mappe toujours vers le langage étudiant :

  L1 interference        → "English habits"
  sentence architecture  → "how you built the sentence"
  lexical range          → "word choice"
  phonological control   → "pronunciation and fluency"
  coherence              → "how your ideas flow"
  discourse structure    → "how you organized your argument"
  morphosyntax           → "grammar patterns"
  register               → "formality level"
  cohesion               → "how your ideas connect"
  lexicon                → "the words you chose"

Tu dois citer les mots EXACTS de l'étudiant (jamais de paraphrase).
Tu dois terminer sur un champ transformation : UNE action concrète et
unique à appliquer au prochain essai."""


@dataclass(frozen=True)
class Criterion:
    """One scorable criterion in an exam profile (e.g. 'Task response').

    The tutor-facing technical label lives in ``label_fr_technical``; the
    student-facing labels live in ``label_*_student`` and should be plainer.
    """

    key: str
    label_fr_technical: str
    label_fr_student: str
    label_en_student: str
    label_es_student: str
    max_score: int = 20
    prompt_guidance: str = ""


@dataclass(frozen=True)
class ExamProfile:
    id: str
    display_name: str

    # Which pills to render in the Score Overview card. Values from:
    #   "raw20"  — e.g. "13.4 / 20"
    #   "cefr"   — e.g. "B2"
    #   "clb"    — e.g. "CLB 7"
    # Future profiles may introduce other frameworks (e.g. "delf_pass").
    frameworks_shown: tuple[str, ...]

    criteria_oral: tuple[Criterion, ...]
    criteria_writing: tuple[Criterion, ...]

    # Score → primary level (typically CEFR). Must be pure / deterministic so
    # the value can't hallucinate from the LLM.
    score_to_cefr: Callable[[float], str]

    # Primary-level → secondary framework value. None for profiles with no
    # secondary (e.g. DELF shows only CEFR).
    cefr_to_secondary: Optional[Callable[[str], object]] = None
    secondary_framework_label: Optional[str] = None  # e.g. "CLB"

    # Appended to Claude's system prompt to describe this framework's
    # examiner persona and scoring philosophy. Criteria blocks are generated
    # from the criteria list; this preamble is just the intro.
    system_prompt_preamble: str = ""

    # Optional override for the JSON namespace key in the model response.
    # Defaults to "<id>_evaluation".
    response_namespace: str = ""

    # Dual-channel feedback voice guides. Spliced into the Pass 1 system
    # prompt as {examiner_voice_guide} and {teacher_voice_guide}. Profiles
    # typically override examiner_voice_guide with framework-specific
    # register; teacher_voice_guide defaults are universal pedagogy and
    # most profiles inherit them unchanged.
    examiner_voice_guide: str = DEFAULT_EXAMINER_VOICE_GUIDE
    teacher_voice_guide: str = DEFAULT_TEACHER_VOICE_GUIDE

    def criteria_for(self, skill: str) -> tuple[Criterion, ...]:
        if skill == "writing":
            return self.criteria_writing
        return self.criteria_oral

    @property
    def namespace(self) -> str:
        return self.response_namespace or f"{self.id}_evaluation"

    def build_criteria_prompt_block(self, skill: str) -> str:
        """Render the criteria list as a prompt fragment for Claude."""
        lines = []
        for i, c in enumerate(self.criteria_for(skill), start=1):
            lines.append(
                f"  {i}. {c.key} — {c.label_fr_technical}\n"
                f"     {c.prompt_guidance}"
            )
        return "\n\n".join(lines)

    def student_labels(self, skill: str, ui_language: str) -> list[dict]:
        """Shape-ready data for the frontend criteria rows."""
        attr = {
            "en": "label_en_student",
            "fr": "label_fr_student",
            "es": "label_es_student",
        }.get(ui_language, "label_en_student")
        out = []
        for c in self.criteria_for(skill):
            out.append(
                {
                    "key": c.key,
                    "label": getattr(c, attr),
                    "label_fr_technical": c.label_fr_technical,
                    "max_score": c.max_score,
                }
            )
        return out
