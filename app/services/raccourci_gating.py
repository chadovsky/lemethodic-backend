"""F-053 — Le Raccourci gating.

Thin read-side service for any code that needs to check curriculum
progress. The canonical source is the ``user_raccourci_progress`` table,
populated on first read via ``ensure_progress_rows``.

Public API:
- ``ensure_progress_rows(user, db)`` — creates 16 progress rows for a
  user on demand. Idempotent; cheap after first call because the
  ``is_populated`` shortcut avoids re-issuing a bulk upsert.
- ``is_above_a2(user, db)`` — True once all 16 lessons are completed.
- ``lessons_completed(user, db)`` — integer count.
- ``next_lesson(user, db)`` — the next unlocked-but-not-completed
  ``RaccourciLesson`` row, or the last lesson once everything's done.
- ``lesson_unlocked(user, lesson_id, db)`` — True when the user can
  access this lesson (status != locked).
- ``record_quiz_attempt(user, lesson, db, score_pct)`` — updates
  progress + unlocks next lesson when score ≥ 80. Returns
  ``(passed, progress_row)``.

All helpers expect a live SQLAlchemy ``Session`` so they behave
predictably inside FastAPI request scopes.
"""
from __future__ import annotations

import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.models import (
    RaccourciLesson,
    User,
    UserRaccourciProgress,
)

QUIZ_PASS_THRESHOLD: int = 80  # percent


# ═══════════════════════════════════════════════════════════════
# Progress bootstrap
# ═══════════════════════════════════════════════════════════════

def ensure_progress_rows(user: User, db: Session) -> list[UserRaccourciProgress]:
    """Create the per-user ``UserRaccourciProgress`` rows if missing.

    Lesson 1 starts ``unlocked`` with an ``unlocked_at`` stamp; lessons
    2-16 start ``locked``. Idempotent: existing rows are left alone
    (so we never stomp progress an already-logged-in user has built up).

    Returns the full list of progress rows for ``user`` ordered by
    ``lesson_number`` — handy for endpoints that want to render the
    whole curriculum in one query.
    """
    lessons = (
        db.query(RaccourciLesson)
        .filter(RaccourciLesson.is_active == True)  # noqa: E712
        .order_by(RaccourciLesson.lesson_number)
        .all()
    )
    if not lessons:
        # Raccourci hasn't been seeded yet — nothing to bootstrap.
        return []

    existing = {
        row.lesson_id: row
        for row in db.query(UserRaccourciProgress)
        .filter(UserRaccourciProgress.user_id == user.id)
        .all()
    }

    created_any = False
    now = datetime.datetime.utcnow()
    for lesson in lessons:
        if lesson.id in existing:
            continue
        initial_status = "unlocked" if lesson.lesson_number == 1 else "locked"
        row = UserRaccourciProgress(
            user_id=user.id,
            lesson_id=lesson.id,
            status=initial_status,
            quiz_attempts=0,
            quiz_best_score=0,
            unlocked_at=now if initial_status == "unlocked" else None,
            updated_at=now,
        )
        db.add(row)
        existing[lesson.id] = row
        created_any = True

    if created_any:
        db.commit()
    # Sorted by lesson_number for caller convenience.
    return sorted(
        existing.values(),
        key=lambda r: next(
            (l.lesson_number for l in lessons if l.id == r.lesson_id),
            9999,
        ),
    )


# ═══════════════════════════════════════════════════════════════
# Reads
# ═══════════════════════════════════════════════════════════════

def lessons_completed(user: User, db: Session) -> int:
    """Number of ``completed`` progress rows for this user. Doesn't
    call ``ensure_progress_rows`` — a user with no progress returns 0
    the same way a user with 16 lock rows does."""
    return (
        db.query(UserRaccourciProgress)
        .filter(
            UserRaccourciProgress.user_id == user.id,
            UserRaccourciProgress.status == "completed",
        )
        .count()
    )


def is_above_a2(user: User, db: Session) -> bool:
    """True iff the user has finished all 16 Le Raccourci lessons.

    F-049 Tâche 2 scenarios above A2_B1 and F-051 Tâche 3 topics above
    A2_B1 both depend on this check.
    """
    return lessons_completed(user, db) >= 16


def next_lesson(user: User, db: Session) -> Optional[RaccourciLesson]:
    """Return the first lesson whose progress row is ``unlocked`` or
    ``in_progress`` for this user. Falls back to the last lesson once
    everything's completed (nicer than None for the home-card UI)."""
    ensure_progress_rows(user, db)
    rows = (
        db.query(UserRaccourciProgress, RaccourciLesson)
        .join(RaccourciLesson, UserRaccourciProgress.lesson_id == RaccourciLesson.id)
        .filter(UserRaccourciProgress.user_id == user.id)
        .order_by(RaccourciLesson.lesson_number)
        .all()
    )
    if not rows:
        return None
    for progress, lesson in rows:
        if progress.status in ("unlocked", "in_progress"):
            return lesson
    # All completed — surface lesson 16 so the card still has something
    # to link to.
    return rows[-1][1]


def lesson_unlocked(user: User, lesson_id: int, db: Session) -> bool:
    row = (
        db.query(UserRaccourciProgress)
        .filter(
            UserRaccourciProgress.user_id == user.id,
            UserRaccourciProgress.lesson_id == lesson_id,
        )
        .first()
    )
    return bool(row and row.status != "locked")


# ═══════════════════════════════════════════════════════════════
# Writes
# ═══════════════════════════════════════════════════════════════

def record_quiz_attempt(
    user: User,
    lesson: RaccourciLesson,
    db: Session,
    score_pct: int,
) -> tuple[bool, UserRaccourciProgress]:
    """Update the user's progress for ``lesson`` with a fresh quiz
    attempt. Returns ``(passed, progress_row)`` where ``passed`` is
    ``True`` iff ``score_pct >= QUIZ_PASS_THRESHOLD``.

    Side effects on pass:
    - Progress row flipped to ``completed`` (if not already).
    - ``completed_at`` stamped.
    - The next lesson's row (by ``lesson_number + 1``) is flipped from
      ``locked`` to ``unlocked`` if it was locked. Idempotent — a user
      who re-passes a lesson doesn't double-unlock anything further
      down.
    """
    progress = (
        db.query(UserRaccourciProgress)
        .filter(
            UserRaccourciProgress.user_id == user.id,
            UserRaccourciProgress.lesson_id == lesson.id,
        )
        .first()
    )
    if progress is None:
        # Lazy-create if we somehow don't have the row yet (e.g. the
        # raccourci tables were populated after this user signed up).
        ensure_progress_rows(user, db)
        progress = (
            db.query(UserRaccourciProgress)
            .filter(
                UserRaccourciProgress.user_id == user.id,
                UserRaccourciProgress.lesson_id == lesson.id,
            )
            .first()
        )
    if progress is None:
        raise RuntimeError(f"progress row missing for user={user.id} lesson={lesson.id}")

    now = datetime.datetime.utcnow()
    score_pct = max(0, min(100, int(score_pct)))
    progress.quiz_attempts = (progress.quiz_attempts or 0) + 1
    progress.quiz_best_score = max(progress.quiz_best_score or 0, score_pct)
    progress.updated_at = now

    passed = score_pct >= QUIZ_PASS_THRESHOLD
    if passed:
        # Only mark completed once — preserves the original completion
        # timestamp across retries.
        if progress.status != "completed":
            progress.status = "completed"
            progress.completed_at = now

        # Unlock the next lesson (if any).
        next_row = (
            db.query(UserRaccourciProgress)
            .join(
                RaccourciLesson,
                UserRaccourciProgress.lesson_id == RaccourciLesson.id,
            )
            .filter(
                UserRaccourciProgress.user_id == user.id,
                RaccourciLesson.lesson_number == (lesson.lesson_number or 0) + 1,
            )
            .first()
        )
        if next_row and next_row.status == "locked":
            next_row.status = "unlocked"
            next_row.unlocked_at = now
    else:
        # Touch the status to in_progress if still at "unlocked" so the
        # next_lesson() heuristic can prefer it over a blank slot.
        if progress.status == "unlocked":
            progress.status = "in_progress"

    db.commit()
    db.refresh(progress)
    return passed, progress
