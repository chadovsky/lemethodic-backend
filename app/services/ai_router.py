"""F-311 Phase A — model routing by task class.

Single source of truth for which Anthropic model ID handles which
workload. Future model bumps (e.g. Sonnet 4.6 → 4.7) are a one-line
config change, not a 6-site search-and-replace.

Tasks (per F-311 Decision 4 + Q2 confirmations 2026-05-12):
  - "diagnostic"            → sonnet (deep evaluation)
  - "writing_diagnostic"    → sonnet (same model, distinct task for routing)
  - "detection"             → sonnet (cluster + module detection)
  - "examiner"              → haiku (conversation turns; rollback to sonnet
                              via MODEL_EXAMINER env if quality drops)
  - "outline_scaffold"      → sonnet (argument_assistant — reasoning-heavy)
  - "transcript_correction" → haiku (low-confidence word fix — lexical)
  - "vocab"                 → haiku (future Le Vocabulaire)
  - "rag_synthesis"         → haiku (future RAG retrieval-augmented synthesis)

Each task has a settings.MODEL_* env-overrideable constant. Defaults match
the strategic-session lock; overrides handle fast rollback during smoke.
"""
from __future__ import annotations

from typing import Literal

from app.config import settings


Task = Literal[
    "diagnostic",
    "writing_diagnostic",
    "detection",
    "examiner",
    "outline_scaffold",
    "transcript_correction",
    "vocab",
    "rag_synthesis",
]


def pick_model(task: Task) -> str:
    """Return the Anthropic model ID for a given task.

    Raises KeyError on an unknown task — caller bug, not a fallback case.
    """
    mapping: dict[str, str] = {
        "diagnostic": settings.MODEL_DIAGNOSTIC,
        "writing_diagnostic": settings.MODEL_DIAGNOSTIC,
        "detection": settings.MODEL_DETECTION,
        "examiner": settings.MODEL_EXAMINER,
        "outline_scaffold": settings.MODEL_OUTLINE_SCAFFOLD,
        "transcript_correction": settings.MODEL_TRANSCRIPT_CORRECTION,
        "vocab": settings.MODEL_VOCAB,
        "rag_synthesis": settings.MODEL_RAG_SYNTHESIS,
    }
    return mapping[task]
