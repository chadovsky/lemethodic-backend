"""Fluency analysis — F-038.

Computes a per-recording fluency assessment from AssemblyAI word-level
timing + text. Fluency is NOT a couche in La Méthode en Couches; it's a
separate measurable dimension that complements the 4 couches. Couches
measure *what* the student says; fluency measures *how smoothly*.

No external API calls, no LLM. Metrics → score bands → templated
bilingual verdict. Fast and deterministic.

The reference bands are calibrated for B1–B2 anglophone French oral
production. They are first-pass defaults — Chadi will calibrate against
real student recordings (tracked as a follow-up).

AssemblyAI returns word timestamps in MILLISECONDS; we convert to
seconds up front so the thresholds in this module read naturally.
"""
from __future__ import annotations

import re
from typing import Iterable

# ── Thresholds (seconds) ────────────────────────────────────────
PAUSE_THRESHOLD_SEC = 0.5      # gap above this counts as a pause
LONG_PAUSE_THRESHOLD_SEC = 1.5  # gap above this counts as a "long" pause

# Hesitation markers — French filler words that signal uncertainty.
# Matched word-boundary, case-insensitive.
_HESITATION_MARKERS = ("euh", "ben", "hmm", "uhh", "hum")
_HESITATION_RE = re.compile(
    r"\b(" + "|".join(re.escape(m) for m in _HESITATION_MARKERS) + r")\b",
    re.IGNORECASE,
)

# ── Metric → sub-score bands ────────────────────────────────────
# Each band returns 1–5. See CLAUDE.md / F-038 ticket for the table.
# These are reference values; calibrate later against real recordings.

def _score_wpm(wpm: float) -> int:
    if 130 <= wpm <= 160:
        return 5
    if (110 <= wpm < 130) or (160 < wpm <= 180):
        return 4
    if 90 <= wpm < 110:
        return 3
    if 70 <= wpm < 90:
        return 2
    # <70 or >180
    return 1


def _score_long_pauses_per_min(rate: float) -> int:
    if rate <= 1:
        return 5
    if rate <= 2:
        return 4
    if rate <= 4:
        return 3
    if rate <= 6:
        return 2
    return 1


def _score_hesitations_per_min(rate: float) -> int:
    if rate <= 1:
        return 5
    if rate <= 3:
        return 4
    if rate <= 5:
        return 3
    if rate <= 8:
        return 2
    return 1


def _score_repetitions_per_min(rate: float) -> int:
    if rate == 0:
        return 5
    if rate <= 1:
        return 4
    if rate <= 2:
        return 3
    if rate <= 4:
        return 2
    return 1


# ── Templated verdicts ─────────────────────────────────────────
# Bucketed by overall /20. Each band has FR / EN / ES strings.
# Rule-based so the verdict stays fast, free, and consistent.
_VERDICT_TEMPLATES: list[tuple[int, dict[str, str]]] = [
    (17, {
        "fr": "Débit régulier et naturel, presque sans hésitation. Très bonne fluidité.",
        "en": "Steady, natural pace with almost no hesitation. Excellent fluency.",
        "es": "Ritmo regular y natural, casi sin vacilaciones. Excelente fluidez.",
    }),
    (14, {
        "fr": "Débit régulier avec quelques pauses naturelles. Très peu d'hésitations.",
        "en": "Steady pace with some natural pauses. Very few hesitations.",
        "es": "Ritmo regular con algunas pausas naturales. Muy pocas vacilaciones.",
    }),
    (11, {
        "fr": "Débit acceptable, mais les pauses et hésitations se remarquent. À fluidifier.",
        "en": "Acceptable pace, but pauses and hesitations are noticeable. Work on smoothing out.",
        "es": "Ritmo aceptable, pero las pausas y vacilaciones se notan. Hay que fluidificar.",
    }),
    (8, {
        "fr": "Débit haché, pauses fréquentes et hésitations marquées. Priorité à la fluidité.",
        "en": "Choppy pace with frequent pauses and marked hesitations. Prioritise fluency work.",
        "es": "Ritmo entrecortado, pausas frecuentes y vacilaciones marcadas. Prioridad: la fluidez.",
    }),
    (0, {
        "fr": "Débit très interrompu. La fluidité doit être travaillée avant tout autre aspect.",
        "en": "Very broken pace. Fluency needs work before anything else.",
        "es": "Ritmo muy entrecortado. Hay que trabajar la fluidez antes que cualquier otro aspecto.",
    }),
]


def _verdict_for_score(score: int) -> dict[str, str]:
    for threshold, verdicts in _VERDICT_TEMPLATES:
        if score >= threshold:
            return verdicts
    return _VERDICT_TEMPLATES[-1][1]


# ── Normalisation helpers ──────────────────────────────────────

def _word_time_sec(value) -> float:
    """AssemblyAI word timestamps are in MILLISECONDS. Convert to
    seconds. Be tolerant of anything weird (strings, None, negatives)."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    if v < 0:
        return 0.0
    return v / 1000.0


def _count_repetitions(words: Iterable[dict]) -> int:
    """Count immediate word repetitions (same normalised token twice in a
    row), e.g. 'je je pense'. Punctuation is stripped; match is
    case-insensitive."""
    prev = None
    count = 0
    for w in words:
        token = (w.get("text") or "").strip().lower()
        token = re.sub(r"[^\wàâäéèêëîïôöùûüÿçœæ'-]+", "", token, flags=re.UNICODE)
        if not token:
            prev = None
            continue
        if token == prev:
            count += 1
        prev = token
    return count


# ── Public API ─────────────────────────────────────────────────

def compute_fluency(
    stt_result: dict | None,
    *,
    recording_duration_sec: float | None = None,
) -> dict | None:
    """Compute fluency metrics + score + bilingual verdict from an STT
    result dict (shape produced by ``app.services.stt.transcribe_audio``).

    Returns ``None`` when there isn't enough data to compute fluency
    (e.g., writing submissions, demo mode, or transcripts with <2 words).
    Callers should persist ``None`` / ``null`` and the UI should hide
    the fluency card in that case.

    ``recording_duration_sec`` is the clock duration of the audio file
    (from ``Recording.duration_seconds``). Used to compute the
    speech-to-silence ratio when available; falls back to the
    words-span duration otherwise.
    """
    if not stt_result or not isinstance(stt_result, dict):
        return None

    words = stt_result.get("words") or []
    transcript = stt_result.get("transcript") or ""

    if len(words) < 2:
        return None

    # Timestamps → seconds.
    starts = [_word_time_sec(w.get("start")) for w in words]
    ends = [_word_time_sec(w.get("end")) for w in words]
    first_start = starts[0]
    last_end = ends[-1]
    words_span_sec = max(last_end - first_start, 0.0)
    if words_span_sec <= 0:
        return None

    # Pauses.
    pause_count = 0
    long_pause_count = 0
    long_pause_positions: list[dict] = []
    total_pause_sec = 0.0
    for i in range(len(words) - 1):
        gap = starts[i + 1] - ends[i]
        if gap > PAUSE_THRESHOLD_SEC:
            pause_count += 1
            total_pause_sec += gap
            if gap > LONG_PAUSE_THRESHOLD_SEC:
                long_pause_count += 1
                long_pause_positions.append({
                    "after_word_index": i,
                    "after_word": words[i].get("text", ""),
                    "duration_sec": round(gap, 2),
                })

    # Hesitations — word-boundary match on the transcript text.
    hesitation_count = len(_HESITATION_RE.findall(transcript))

    # Repetitions.
    repetition_count = _count_repetitions(words)

    # Speech-to-silence ratio:
    # If we have the recording's clock duration, use it. Otherwise, fall
    # back to words-span (which will always give 1.0 minus pause ratio).
    total_recording_sec = (
        recording_duration_sec
        if recording_duration_sec and recording_duration_sec > 0
        else words_span_sec
    )
    speaking_sec = max(words_span_sec - total_pause_sec, 0.0)
    speech_to_silence_ratio = (
        speaking_sec / total_recording_sec if total_recording_sec > 0 else 0.0
    )
    pause_ratio = (
        total_pause_sec / total_recording_sec if total_recording_sec > 0 else 0.0
    )

    duration_min = words_span_sec / 60.0
    wpm = round(len(words) / duration_min) if duration_min > 0 else 0

    # Per-minute rates — guard against absurdly short recordings.
    long_pauses_per_min = long_pause_count / duration_min if duration_min > 0 else 0
    hesitations_per_min = hesitation_count / duration_min if duration_min > 0 else 0
    repetitions_per_min = repetition_count / duration_min if duration_min > 0 else 0

    # Sub-scores (1-5) then sum → /20.
    sub_wpm = _score_wpm(wpm)
    sub_long_pauses = _score_long_pauses_per_min(long_pauses_per_min)
    sub_hesitations = _score_hesitations_per_min(hesitations_per_min)
    sub_repetitions = _score_repetitions_per_min(repetitions_per_min)
    score = sub_wpm + sub_long_pauses + sub_hesitations + sub_repetitions

    verdict = _verdict_for_score(score)

    return {
        "score": score,
        "wpm": wpm,
        "pause_count": pause_count,
        "long_pause_count": long_pause_count,
        "pause_ratio": round(pause_ratio, 3),
        "hesitation_count": hesitation_count,
        "repetition_count": repetition_count,
        "speech_to_silence_ratio": round(speech_to_silence_ratio, 3),
        "long_pauses": long_pause_positions,
        "sub_scores": {
            "wpm": sub_wpm,
            "long_pauses": sub_long_pauses,
            "hesitations": sub_hesitations,
            "repetitions": sub_repetitions,
        },
        "verdict_fr": verdict["fr"],
        "verdict_en": verdict["en"],
        "verdict_es": verdict["es"],
    }
