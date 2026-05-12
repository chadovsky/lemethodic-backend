"""F-311 Phase A — prompt-injection detection.

Pure-function gate called BEFORE the Claude call from endpoint handlers
(recordings/upload, conversations/end, writing/submit). Rejects user
input that contains system-override patterns.

Pattern strategy:
  - Conservative English-pattern list. Le Méthodic's user input is
    French (STT transcripts + writing submissions in French); English
    injection strings won't appear in legitimate content, so we can be
    aggressive on English without false-positive risk for now.
  - Chat-template tokens (<|im_start|> etc.) trigger regardless of
    surrounding language — these are model-shaping characters that no
    legitimate writing should contain.
  - When future surfaces process English content (RAG, vocab), revisit.

Detection returns (bool, pattern_name) for structured logging. Callers
log the pattern name + user_id but NOT the raw input (an attacker
forcing rejections shouldn't see their probes echoed in logs as
content).

Toggle: settings.ENABLE_PROMPT_INJECTION_CHECK. Default True. Set to
False if false-positive rate surfaces in production logs.
"""
from __future__ import annotations

import re
from typing import Tuple


_INJECTION_PATTERNS: list[tuple[re.Pattern, str]] = [
    # Direct override attempts
    (
        re.compile(
            r"\bignore\s+(all\s+)?(previous|prior|above|earlier)\s+"
            r"(instructions?|prompts?|rules?|directives?|messages?)\b",
            re.IGNORECASE,
        ),
        "ignore_previous",
    ),
    (
        re.compile(
            r"\bdisregard\s+(all\s+|the\s+|any\s+)?"
            r"(previous|prior|above|earlier)\s+"
            r"(instructions?|prompts?|rules?)\b",
            re.IGNORECASE,
        ),
        "disregard_previous",
    ),
    (
        re.compile(
            r"\bforget\s+(everything\s+)?(above|before|prior|previous)\b",
            re.IGNORECASE,
        ),
        "forget_previous",
    ),
    # Persona reassignment
    (
        re.compile(r"\byou\s+are\s+now\s+\w+", re.IGNORECASE),
        "you_are_now",
    ),
    (
        # "act as a/an/the/if X" — standard persona-reassignment phrasing.
        # Tighter alternatives like requiring (different|new|the) miss the
        # common "act as a pirate / helpful assistant" form.
        re.compile(
            r"\bact\s+as\s+(a|an|the|if)\s+\w+",
            re.IGNORECASE,
        ),
        "act_as",
    ),
    (
        re.compile(
            r"\bpretend\s+(you\s+are|to\s+be)\b",
            re.IGNORECASE,
        ),
        "pretend_to_be",
    ),
    # Chat-template injection
    (re.compile(r"<\|im_start\|>"), "chat_template_im_start"),
    (re.compile(r"<\|im_end\|>"), "chat_template_im_end"),
    (re.compile(r"<\|system\|>"), "chat_template_system"),
    (re.compile(r"<\|assistant\|>"), "chat_template_assistant"),
    (re.compile(r"<\|user\|>"), "chat_template_user"),
    # Output redirection
    (
        re.compile(
            r"\binstead\s+of\s+(the\s+)?(above|previous|prior)\s+"
            r"(instructions?|prompts?|rules?)\b",
            re.IGNORECASE,
        ),
        "instead_of_above",
    ),
]


def contains_injection_signal(text: str | None) -> Tuple[bool, str | None]:
    """Check for prompt-injection signals.

    Returns (detected, pattern_name). On detection, caller should:
      - Reject with HTTP 400 (or equivalent).
      - Log WARNING with pattern_name + user_id + ip — NOT the raw input.

    On empty/None input → (False, None). The endpoint handler validates
    presence; this function is content-only.
    """
    if not text:
        return False, None
    for pattern, name in _INJECTION_PATTERNS:
        if pattern.search(text):
            return True, name
    return False, None
