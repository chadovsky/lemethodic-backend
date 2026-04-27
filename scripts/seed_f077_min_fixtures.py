"""F-077 minimum fixture seeder for verification harnesses.

The F-075a and F-075b harnesses both call ``db.query(User).first()``
to mint a JWT for their TestClient calls and ``SystemExit`` if no
User row exists. Pre-F-077 (SQLite era) the dev DB always carried
real registered users from manual testing; under F-077 the local
PostgreSQL starts empty after ``alembic upgrade head``, so the
harnesses need a guaranteed seed before they can run.

What this script creates (idempotent — safe to re-run):

  * One test ``User`` (email ``f077-test@local``, admin=False).
  * One ``Tache1Opening`` row (so the F-075a Pass 2 conversation-
    start sub-check exercises the /turn route instead of skipping).

Run from project root on a fresh DB:

    docker-compose up -d
    alembic upgrade head
    python -m scripts.seed_f077_min_fixtures
    python -m scripts.verify_f075a_size_cap   # now has data to mint tokens against

Idempotency: every insert is gated by an existence check — re-running
the script is a no-op once the fixtures exist. Does NOT touch any
other table; production data and feature seeders (École,
Tâche 2 scenarios, Tâche 3 prompts, etc.) are independent.
"""
from __future__ import annotations

from app.database import SessionLocal
from app.models.models import Tache1Opening, User
from app.services.auth import hash_password


TEST_USER_EMAIL = "f077-test@local"
TEST_USER_PASSWORD = "f077-test-password"  # local dev only; never deployed
TEST_USER_FULL_NAME = "F-077 Test User"

# Innocuous Tâche 1 opening line. Picked to be neutrally worded so the
# F-075a /conversations/start path has SOMETHING to pick from random.
SEED_T1_OPENING_FR = "Bonjour, présentez-vous brièvement s'il vous plaît."
SEED_T1_OPENING_EN = "Hello, please introduce yourself briefly."


def seed_user(db) -> User:
    user = db.query(User).filter(User.email == TEST_USER_EMAIL).first()
    if user is not None:
        print(f"[seed_f077] user already present id={user.id} email={user.email}")
        return user
    user = User(
        email=TEST_USER_EMAIL,
        hashed_password=hash_password(TEST_USER_PASSWORD),
        full_name=TEST_USER_FULL_NAME,
        ui_language="en",
        is_admin=False,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    print(f"[seed_f077] created user id={user.id} email={user.email}")
    return user


def seed_tache1_opening(db) -> Tache1Opening:
    existing = (
        db.query(Tache1Opening)
        .filter(Tache1Opening.opening_prompt_fr == SEED_T1_OPENING_FR)
        .first()
    )
    if existing is not None:
        print(f"[seed_f077] tache1_opening already present id={existing.id}")
        return existing
    opening = Tache1Opening(
        opening_prompt_fr=SEED_T1_OPENING_FR,
        opening_prompt_en=SEED_T1_OPENING_EN,
        is_active=True,
    )
    db.add(opening)
    db.commit()
    db.refresh(opening)
    print(f"[seed_f077] created tache1_opening id={opening.id}")
    return opening


def main() -> int:
    db = SessionLocal()
    try:
        seed_user(db)
        seed_tache1_opening(db)
    finally:
        db.close()
    print("[seed_f077] done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
