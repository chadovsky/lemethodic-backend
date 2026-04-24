"""
TÂCHE 2 EXAMINER PERSONA BUILDER — F-049

Builds the system prompt for the Tâche 2 examiner from a Tache2Scenario
row. The persona is per-scenario (different for travel agent vs Quebec
colleague), but BEHAVIOR_RULES below are global to every Tâche 2
examiner.

[CHADI: review BEHAVIOR_RULES on Day 7. The placeholder is generic.
Specific tweaks you may want:
- examiner reaction to clearly-uninformed questions
- whether examiner can ever ask the candidate a question back (default: rarely)
- handling of off-topic candidate detours]
"""
from __future__ import annotations

import json
from typing import Iterable

BEHAVIOR_RULES = """
You are playing a character in a TCF (Test de Connaissance du Français) Tâche 2 role-play.

GLOBAL RULES (apply to every scenario):

1. Stay in character at all times. You are NOT an examiner explaining things — you ARE the character (friend / travel agent / librarian / etc.).
2. Speak ONLY in French.
3. Match the register specified in the scenario (formel = vous; informel = tu; semi_formel = vous unless candidate uses tu first).
4. Give SHORT factual answers — one or two sentences maximum per turn. Never give a paragraph.
5. NEVER volunteer information the candidate didn't ask for. If they ask "C'est combien ?" answer the price only. Don't add "and by the way we also have a discount on..."
6. If the candidate asks a vague question, give a vague-but-plausible answer that forces them to ask a follow-up.
7. If the candidate asks something off-topic for the scenario, redirect gently in character ("Je ne suis pas sûr(e), mais pour [scenario topic]...").
8. If the candidate's question is grammatically broken but understandable, answer it — don't correct.
9. If the candidate's question is incomprehensible, in character: "Pardon ? Pouvez-vous reformuler ?"
10. NEVER end the conversation yourself. The candidate decides when they're done. If the candidate says "Merci, c'est tout" or similar, give a brief sign-off in character ("De rien, bonne journée !" or "À plus !").

OUTPUT FORMAT: respond with ONLY the next character turn as plain French text. No commentary, no JSON, no English. Just what the character would say.
""".strip()


# UI-side guide: after this many candidate turns the turn response
# includes wrap_up_hint=true so the frontend can surface a subtle
# "do you want to wrap up?" banner. Not a hard limit.
MAX_CANDIDATE_TURNS_HINT: int = 8

# Hard cap — the turn endpoint force-closes the conversation at this
# count. Matches the Yarden guidance that a well-targeted exchange
# shouldn't need more than a dozen turns to hit its marks.
MAX_CANDIDATE_TURNS_HARD: int = 12


def _data_targets_to_str(raw) -> str:
    """Tache2Scenario.data_targets is stored as JSON text. Tolerate a
    list (already decoded), a JSON string, or anything weird — fall back
    to 'plausible info about the scenario' so the prompt always makes
    sense to the model."""
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, str):
        try:
            decoded = json.loads(raw)
            items = decoded if isinstance(decoded, list) else []
        except json.JSONDecodeError:
            items = []
    else:
        items = []
    if not items:
        return "(aucune cible spécifique — improvise)"
    return ", ".join(str(i) for i in items)


def build_persona(scenario) -> str:
    """Combine BEHAVIOR_RULES with the scenario-specific persona block
    and the data-targets hint. Returns the full system prompt string
    ready to hand to Claude."""
    persona = getattr(scenario, "examiner_persona", "") or ""
    data_targets_raw = getattr(scenario, "data_targets", None) or []
    data_targets = _data_targets_to_str(data_targets_raw)
    register = getattr(scenario, "register", "formel") or "formel"

    return (
        f"{BEHAVIOR_RULES}\n\n"
        f"--- THIS SCENARIO'S REGISTER ---\n\n"
        f"{register}\n\n"
        f"--- THIS SCENARIO'S CHARACTER ---\n\n"
        f"{persona}\n\n"
        f"--- WHAT YOU KNOW (improvise plausible facts as needed) ---\n\n"
        f"The candidate is trying to gather these pieces of information from you: "
        f"{data_targets}. You can improvise realistic details for each. Stay "
        f"consistent within this conversation.\n"
    )
