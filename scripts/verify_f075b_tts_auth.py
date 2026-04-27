"""F-075b verification harness.

Exercises the F-075b TTS auth wrap. Drops a synthetic mp3 stub into
the TTS cache directory, runs through the gates, and cleans up the
stub via try/finally per F-080d.z rule #1.

Note: the canonical user-audio serving route the F-075b ticket
originally specced doesn't exist in this codebase (audit found no
serving route at all for user recordings — the diagnostic page
doesn't yet expose playback, and the only audio served today is
the shared TTS cache). Gates 4 + 5 (cross-user 404 / own-user 200
on user audio) therefore don't apply to this scope. F-075b.x in
BACKLOG carries the canonical pattern for whoever wires playback
first.

Run from project root:
    python -m scripts.verify_f075b_tts_auth
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from app.config import settings
from app.database import SessionLocal
from app.models.models import User
from app.services.auth import create_access_token


# Synthetic mp3 file dropped into the TTS cache dir for testing.
# Filename uses the same SHA-256 shape the real cache writer
# produces. Cleaned up via try/finally regardless of test outcome.
_TEST_FILENAME = "f075b_test_" + "0" * 56 + ".mp3"
# Minimal-but-valid: an ID3 tag header + a couple of zero bytes.
# Enough that mp3-aware clients see it as something parseable;
# we're not testing playback, just the route's serve path.
_TEST_BYTES = b"ID3\x03\x00\x00\x00\x00\x00\x00" + b"\x00" * 64


def _drop_stub() -> Path:
    cache_dir = Path(settings.TTS_CACHE_DIR).resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    stub = cache_dir / _TEST_FILENAME
    stub.write_bytes(_TEST_BYTES)
    return stub


def _remove_stub(stub: Path) -> None:
    try:
        stub.unlink(missing_ok=True)
    except Exception as exc:
        print(f"[cleanup] could not remove {stub}: {exc}")


def _auth_token() -> str:
    db = SessionLocal()
    try:
        user = db.query(User).first()
        if user is None:
            raise SystemExit("[F-075b] no users in DB")
        return create_access_token({"sub": user.email})
    finally:
        db.close()


def gate_unauthenticated_returns_401(client: TestClient) -> int:
    """Gate 1: /tts_audio/<file>.mp3 unauthenticated returns 401."""
    print("\n[Gate 1] /tts_audio/<file>.mp3 unauthenticated -> 401")
    r = client.get(f"/tts_audio/{_TEST_FILENAME}")
    ok = r.status_code == 401
    print(f"  {'OK ' if ok else 'FAIL'}  status={r.status_code} body={r.text[:120]}")
    return 0 if ok else 1


def gate_bearer_returns_200(client: TestClient, token: str) -> int:
    """Gate 2a: /tts_audio/<file>.mp3 with Authorization Bearer -> 200."""
    print("\n[Gate 2a] /tts_audio/<file>.mp3 with Bearer header -> 200")
    r = client.get(
        f"/tts_audio/{_TEST_FILENAME}",
        headers={"Authorization": f"Bearer {token}"},
    )
    ok = (
        r.status_code == 200
        and r.content == _TEST_BYTES
        and r.headers.get("content-type", "").startswith("audio/mpeg")
    )
    print(
        f"  {'OK ' if ok else 'FAIL'}  status={r.status_code} "
        f"content_match={r.content == _TEST_BYTES} "
        f"content_type={r.headers.get('content-type')!r}"
    )
    return 0 if ok else 1


def gate_cookie_returns_200(client: TestClient, token: str) -> int:
    """Gate 2b: /tts_audio/<file>.mp3 with access_token cookie -> 200.

    This is the path that <audio src="..."> uses in the browser —
    cookies are auto-attached to media element requests but the
    Authorization header is NOT, so cookie-auth is what keeps T1/T2
    examiner playback working without frontend changes."""
    print("\n[Gate 2b] /tts_audio/<file>.mp3 with cookie -> 200 (the <audio> path)")
    r = client.get(
        f"/tts_audio/{_TEST_FILENAME}",
        cookies={"access_token": token},
    )
    ok = (
        r.status_code == 200
        and r.content == _TEST_BYTES
        and r.headers.get("content-type", "").startswith("audio/mpeg")
    )
    print(
        f"  {'OK ' if ok else 'FAIL'}  status={r.status_code} "
        f"content_match={r.content == _TEST_BYTES}"
    )
    return 0 if ok else 1


def gate_path_traversal_blocked(client: TestClient, token: str) -> int:
    """Gate 3: path traversal attempts return 400/404, not 200.

    Two layers of defense, both fine:
    - Slash-bearing inputs ("../etc/passwd", "subdir/file.mp3") get
      404 from the router because /tts_audio/{filename} only matches
      one path segment — the route never fires.
    - Backslash / leading-dot / explicit-traversal inputs get 400
      from the handler's filename guard.
    - Null bytes are rejected by httpx's URL parser before the
      request even leaves the client; treated as defense-in-depth.
    """
    print("\n[Gate 3] Path traversal -> 400 or 404 (never 200)")
    failures = 0
    headers = {"Authorization": f"Bearer {token}"}
    attempts = [
        "../etc/passwd",
        "..\\windows\\system32",
        ".hidden",
        "subdir/file.mp3",
        "subdir\\file.mp3",
    ]
    for traversal in attempts:
        r = client.get(f"/tts_audio/{traversal}", headers=headers)
        ok = r.status_code in (400, 404)
        if not ok:
            failures += 1
        print(f"  {'OK ' if ok else 'FAIL'}  '{traversal}' -> {r.status_code}")

    # Null byte: httpx refuses to construct the URL. Treat the
    # exception as a blocked-at-client-layer success (never reached
    # the server, which is even better than a 400 reject).
    try:
        r = client.get("/tts_audio/with\x00null.mp3", headers=headers)
        # If httpx ever stops rejecting, the route should still 400.
        ok = r.status_code == 400
        if not ok:
            failures += 1
        print(f"  {'OK ' if ok else 'FAIL'}  'with\\x00null.mp3' -> {r.status_code}")
    except Exception as exc:
        # InvalidURL or similar — never reached the server. That's a pass.
        print(f"  OK   'with\\x00null.mp3' -> rejected at httpx layer ({type(exc).__name__})")
    return failures


def gate_nonexistent_file_404(client: TestClient, token: str) -> int:
    """Sanity: a well-formed but missing filename returns 404."""
    print("\n[Sanity] Well-formed missing filename -> 404")
    r = client.get(
        "/tts_audio/" + "f" * 64 + ".mp3",
        headers={"Authorization": f"Bearer {token}"},
    )
    ok = r.status_code == 404
    print(f"  {'OK ' if ok else 'FAIL'}  status={r.status_code}")
    return 0 if ok else 1


def main() -> int:
    print(f"[F-075b] cache dir: {settings.TTS_CACHE_DIR}")
    stub = _drop_stub()
    print(f"[setup] dropped stub: {stub}")
    failures = 0
    try:
        client = TestClient(app)
        token = _auth_token()

        failures += gate_unauthenticated_returns_401(client)
        failures += gate_bearer_returns_200(client, token)
        failures += gate_cookie_returns_200(client, token)
        failures += gate_path_traversal_blocked(client, token)
        failures += gate_nonexistent_file_404(client, token)
    finally:
        _remove_stub(stub)
        print(f"\n[cleanup] removed stub: {stub.name}")

    print(f"\n[F-075b] failures: {failures}")
    return failures


if __name__ == "__main__":
    rc = main()
    raise SystemExit(0 if rc == 0 else 1)
