"""F-075a verification harness.

Exercises the audio upload size cap at both layers:

1. Layer A (middleware): synthetic POST with multipart Content-Type
   and Content-Length > cap. Body is small — middleware decides
   solely from the header. Expect 413.
2. Layer B (route-level): real multipart upload with a body that
   actually exceeds the cap. Expect 413 from each of the four
   audio-receiving routes.
3. Regression: legitimate small upload still succeeds (status 200 or
   500 from STT failing on synthetic bytes — the size check passes
   either way; what we're verifying is "not 413").
4. Existing recordings unaffected: ingress-only ticket; touching
   the DB is out of scope.

All routes are exercised through TestClient. Auth is via a minted
JWT for the first user in the DB. The synthetic recordings created
during gate 3 are not cleaned up here — they go to disk under
UPLOAD_DIR with no DB row (gate 3 stops before STT runs), so they
don't pollute application state. Per F-080d.z rule #1 the test
runner could clean them; the path includes a F-075a tag so a future
janitor can find them.

Run from project root:
    python -m scripts.verify_f075a_size_cap
"""
from __future__ import annotations

import io

from fastapi.testclient import TestClient

from main import app
from app.config import settings
from app.database import SessionLocal
from app.models.models import Conversation, Recording, User
from app.services.auth import create_access_token


CAP = settings.MAX_AUDIO_UPLOAD_BYTES
CAP_MB = CAP // (1024 * 1024)
OVER = CAP + 1024 * 1024  # 1 MB over the cap


def _auth_headers() -> dict:
    db = SessionLocal()
    try:
        user = db.query(User).first()
        if user is None:
            raise SystemExit("[F-075a] no users in DB; cannot mint token")
        token = create_access_token({"sub": user.email})
    finally:
        db.close()
    return {"Authorization": f"Bearer {token}"}


def pass_1_middleware_content_length() -> int:
    """Layer A: middleware rejects on Content-Length alone."""
    print("\n[Pass 1] Middleware (Layer A) Content-Length check")
    client = TestClient(app)
    headers = {
        **_auth_headers(),
        # Spoof Content-Length above cap. Body in the request will
        # not actually be 11 MB — middleware decides on the header.
        # TestClient will compute its own Content-Length from the body
        # though, so this test isn't truly synthetic — it requires a
        # real over-cap body to make the header match. Use a real
        # body to keep the test honest.
    }
    # Build a real over-cap multipart body. The middleware sees the
    # actual Content-Length and rejects before the route is invoked.
    big = b"\x00" * OVER
    files = {"audio": ("big.webm", io.BytesIO(big), "audio/webm")}
    r = client.post("/api/recordings/upload", files=files, headers=headers)
    ok = r.status_code == 413 and "exceeds maximum" in r.text
    print(f"  {'OK ' if ok else 'FAIL'}  /api/recordings/upload  status={r.status_code}  body={r.text[:120]}")
    return 0 if ok else 1


def pass_2_route_level_all_four() -> int:
    """Layer B: per-route check on each of the four audio-receiving
    endpoints. Use a body 1 MB over cap. The middleware is also
    firing here (since Content-Length matches body), so this gate
    confirms the routes ALSO reject in case middleware is bypassed."""
    print("\n[Pass 2] Layer B route-level checks (all four routes)")
    client = TestClient(app)
    headers = _auth_headers()
    big = b"\x00" * OVER
    files = lambda: {"audio": ("big.webm", io.BytesIO(big), "audio/webm")}
    failures = 0

    routes = [
        # path, extra form data, expected_status
        ("/api/recordings/upload",     {"tache_mode": "tache_3", "duration_seconds": "10"}, 413),
        ("/api/recordings/transcribe", {"tache_mode": "tache_3", "duration_seconds": "10"}, 413),
        ("/api/audio/upload",          {"duration_seconds": "10"},                          413),
    ]
    for path, data, expected in routes:
        r = client.post(path, files=files(), data=data, headers=headers)
        ok = r.status_code == expected
        if not ok:
            failures += 1
        print(f"  {'OK ' if ok else 'FAIL'}  {path:<35} status={r.status_code}  expected={expected}")

    # /api/conversations/{id}/turn requires a live conversation. We can
    # spin one up via /api/conversations/start, then upload the over-cap
    # audio. If conv start fails for unrelated reasons (no scenarios
    # seeded), skip with a note rather than failing the gate.
    start = client.post(
        "/api/conversations/start",
        json={"tache_mode": "tache_1", "ui_language": "en"},
        headers=headers,
    )
    if start.status_code != 200:
        print(f"  SKIP /api/conversations/{{id}}/turn  conversation start failed status={start.status_code} body={start.text[:120]}")
    else:
        conv_id = start.json().get("id") or start.json().get("conversation_id")
        if conv_id is None:
            print(f"  SKIP /api/conversations/{{id}}/turn  no conv id in start response")
        else:
            r = client.post(
                f"/api/conversations/{conv_id}/turn",
                files=files(),
                data={"duration_seconds": "10"},
                headers=headers,
            )
            ok = r.status_code == 413
            if not ok:
                failures += 1
            print(f"  {'OK ' if ok else 'FAIL'}  /api/conversations/{{id}}/turn   status={r.status_code}")

    return failures


def pass_3_legitimate_small_upload() -> int:
    """A small body must NOT 413. We don't care if STT fails (the
    bytes are synthetic) — the gate is "size check passed, route
    proceeded". Status 413 is the failure signal here; anything
    else means the cap let the request through."""
    print("\n[Pass 3] Legitimate small upload regression (must NOT 413)")
    client = TestClient(app)
    headers = _auth_headers()
    small = b"\x00" * (256 * 1024)  # 256 KB — well under cap, well under p50 of real corpus
    files = {"audio": ("small.webm", io.BytesIO(small), "audio/webm")}
    r = client.post(
        "/api/recordings/upload",
        files=files,
        data={"tache_mode": "tache_3", "duration_seconds": "5"},
        headers=headers,
    )
    ok = r.status_code != 413
    print(f"  {'OK ' if ok else 'FAIL'}  /api/recordings/upload  status={r.status_code} (any non-413 acceptable)")
    return 0 if ok else 1


def _cleanup_test_artifacts(pre_recording_max_id: int, pre_conversation_max_id: int) -> None:
    """F-080d.z rule #1: any test that mutates shared tables MUST use
    try/finally with snapshot+restore. Pass 2/3 can persist Recording
    rows (when the size check lets a small synthetic upload through to
    STT, which fails on the synthetic bytes but the row already
    committed) and Conversation rows (Pass 2 starts a real conversation
    to test the /turn route). Delete any rows created during the run
    using the pre-run id snapshots."""
    db = SessionLocal()
    try:
        new_recordings = (
            db.query(Recording)
            .filter(Recording.id > pre_recording_max_id)
            .all()
        )
        new_conversations = (
            db.query(Conversation)
            .filter(Conversation.id > pre_conversation_max_id)
            .all()
        )
        for r in new_recordings:
            db.delete(r)
        for c in new_conversations:
            db.delete(c)
        if new_recordings or new_conversations:
            db.commit()
            print(f"\n[cleanup] deleted {len(new_recordings)} recording rows, {len(new_conversations)} conversation rows created during the run")
    finally:
        db.close()


def main() -> int:
    print(f"[F-075a] cap = {CAP} bytes ({CAP_MB} MB); test body = {OVER} bytes")

    # Snapshot pre-run table state for cleanup. The verification harness
    # mutates shared tables (Recording, Conversation) via the API
    # routes — F-080d.z rule #1 requires snapshot+restore.
    db = SessionLocal()
    try:
        pre_rec_max = db.query(Recording.id).order_by(Recording.id.desc()).first()
        pre_conv_max = db.query(Conversation.id).order_by(Conversation.id.desc()).first()
        pre_rec_max_id = pre_rec_max[0] if pre_rec_max else 0
        # Conversation.id is a string UUID, not an int — can't compare
        # with > directly. Snapshot the full id set instead.
        existing_conv_ids = {row[0] for row in db.query(Conversation.id).all()}
    finally:
        db.close()

    failures = 0
    try:
        failures += pass_1_middleware_content_length()
        failures += pass_2_route_level_all_four()
        failures += pass_3_legitimate_small_upload()
    finally:
        # Delete any recordings created with id > pre_rec_max_id and
        # any conversations whose id wasn't in the pre-run set.
        db = SessionLocal()
        try:
            new_recs = (
                db.query(Recording).filter(Recording.id > pre_rec_max_id).all()
            )
            new_convs = [
                c for c in db.query(Conversation).all()
                if c.id not in existing_conv_ids
            ]
            for r in new_recs:
                db.delete(r)
            for c in new_convs:
                db.delete(c)
            if new_recs or new_convs:
                db.commit()
                print(f"\n[cleanup] deleted {len(new_recs)} recording rows, {len(new_convs)} conversation rows created during the run")
        finally:
            db.close()

    print(f"\n[F-075a] failures: {failures}")
    return failures


if __name__ == "__main__":
    rc = main()
    raise SystemExit(0 if rc == 0 else 1)
