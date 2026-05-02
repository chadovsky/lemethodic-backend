from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from app.routers import auth, recordings, admin
from app.routers import analytics
from app.routers import writing
from app.routers import oral
from app.routers import patterns
from app.routers import conversations
from app.routers import audio
from app.routers import ecole
from app.routers import users
from app.routers import modules
from app.routers import onboarding
from app.routers import diagnostic
from app.routers import today
from app.models.models import User
from app.services.auth import get_current_user
from app.services import storage
from app.config import settings

# F-077: schema is now owned by Alembic. Run `alembic upgrade head` on
# fresh checkouts and after pulling migrations. The previous
# `Base.metadata.create_all(bind=engine)` call was removed here so the
# app no longer silently creates tables out-of-band — any schema drift
# now surfaces as an explicit Alembic-level mismatch instead of being
# papered over.

app = FastAPI(title="TCF Oral Practice Tool")


# F-078: dumb 200 health endpoint for App Platform's polling probe.
# Deliberately does NOT touch the database — a slow query mustn't fail
# the health check and trigger an unnecessary container restart. Real
# DB / dependency monitoring goes in a separate `/ready` endpoint
# post-launch if needed.
@app.get("/health")
async def health():
    return {"status": "ok"}


# CORS — Next.js dev origins always allowed; production frontend
# origin is injected via FRONTEND_ORIGIN env var (set by F-079 once
# the Vercel URL exists). Multiple production origins can be passed
# as a comma-separated list — useful for staging + prod side by side.
import os as _os

_default_dev_origins = [
    "http://localhost:3000",   # Next.js dev server
    "http://127.0.0.1:3000",   # alt localhost form
    "http://localhost:3001",   # alt port for parallel dev runs
]
_extra_origins = [
    o.strip() for o in (_os.getenv("FRONTEND_ORIGIN") or "").split(",") if o.strip()
]
_allowed_origins = _default_dev_origins + _extra_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,  # cookie auth (F-075b)
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════
# F-075a — server-side audio upload size cap (Layer A: middleware)
# ═══════════════════════════════════════════════════════════════
#
# Reject oversized multipart uploads BEFORE FastAPI buffers the body
# into worker memory. The cap is keyed on Content-Type rather than a
# path allowlist so any future audio-receiving route is guarded by
# default — no multipart endpoint in this codebase carries anything
# other than audio today, and the same DoS class applies if a future
# multipart endpoint is added without explicit protection.
#
# Layer B (per-route `await audio.read(); if len(...) > cap: 413`)
# runs alongside this in the four upload handlers — that catches
# spoofed / missing Content-Length and chunked-transfer cases the
# header check can't see. See app/routers/recordings.py + audio.py +
# conversations.py for the per-route checks.
@app.middleware("http")
async def enforce_multipart_upload_cap(request: Request, call_next):
    if request.method == "POST":
        content_type = request.headers.get("content-type", "").lower()
        if content_type.startswith("multipart/form-data"):
            content_length = request.headers.get("content-length")
            if content_length:
                try:
                    if int(content_length) > settings.MAX_AUDIO_UPLOAD_BYTES:
                        cap_mb = settings.MAX_AUDIO_UPLOAD_BYTES // (1024 * 1024)
                        return JSONResponse(
                            status_code=413,
                            content={
                                "detail": f"Audio file exceeds maximum allowed size of {cap_mb} MB"
                            },
                        )
                except ValueError:
                    # Malformed Content-Length — let it fall through to
                    # Layer B (route-level read-time check) rather than
                    # 400 here; the route's own size check is the
                    # authoritative gate.
                    pass
    return await call_next(request)

# Routers
app.include_router(auth.router)
app.include_router(recordings.router)
app.include_router(admin.router)
app.include_router(analytics.router)
app.include_router(writing.router)
app.include_router(oral.router)
app.include_router(patterns.router)
app.include_router(conversations.router)
app.include_router(audio.router)
app.include_router(ecole.router)
app.include_router(users.router)
app.include_router(modules.router)
app.include_router(onboarding.router)
app.include_router(diagnostic.router)
app.include_router(today.router)

# Serve static files
import os
static_dir = os.path.join(os.path.dirname(__file__), "app", "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# F-052 / F-075b: serve the TTS cache so the <audio> elements in the
# Tâche 1/2 UI can fetch ``/tts_audio/<sha256>.mp3``.
#
# F-075b — replaced the unauthenticated `app.mount("/tts_audio", ...)`
# with an authenticated route handler. TTS files are SHARED across
# users (cached by SHA-256 of (text, voice, model)) so there's no
# ownership check — any logged-in user can fetch any cached file —
# but they MUST be authenticated. `get_current_user` accepts both
# the access_token cookie and the Authorization Bearer header; the
# cookie path is what makes `<audio src="/tts_audio/...">` work
# without frontend changes (browsers don't attach Authorization
# headers to media element requests, but they do send cookies).
#
# F-078 — file body now comes from `app.services.storage` (Spaces in
# prod, local-disk fallback otherwise). Filename guards still apply:
# they prevent malicious filenames from becoming arbitrary storage
# keys (e.g. an attacker can't request `tts_cache/../../etc/passwd`
# because the slash check rejects it before we build the key).


@app.get("/tts_audio/{filename}")
def serve_tts_audio(
    filename: str,
    user: User = Depends(get_current_user),
):
    # Filename guard. Reject anything with path separators,
    # parent-dir traversal, null bytes, or leading-dot. The TTS
    # cache writer only emits ``<sha256>.mp3`` filenames so this is
    # the canonical shape; anything else is suspect. Combined with
    # the prefix-pinned storage key below, this is sufficient to
    # contain the requested file inside tts_cache/ even if the
    # storage backend is permissive about object keys.
    if (
        "/" in filename
        or "\\" in filename
        or ".." in filename
        or "\x00" in filename
        or filename.startswith(".")
    ):
        raise HTTPException(status_code=400, detail="Invalid filename")

    storage_key = f"tts_cache/{filename}"
    if not storage.exists(storage_key):
        raise HTTPException(status_code=404, detail="Audio not found")

    # The TTS pipeline only emits .mp3, but infer defensively in case
    # a future provider adds wav/ogg cache entries.
    ext = os.path.splitext(filename)[1].lower()
    media_type = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".ogg": "audio/ogg",
        ".m4a": "audio/mp4",
        ".webm": "audio/webm",
    }.get(ext, "application/octet-stream")

    return storage.stream_response(storage_key, content_type=media_type)


@app.get("/", response_class=HTMLResponse)
async def root():
    template_path = os.path.join(os.path.dirname(__file__), "app", "templates", "index.html")
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()


@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    template_path = os.path.join(os.path.dirname(__file__), "app", "templates", "admin.html")
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()


@app.get("/writing", response_class=HTMLResponse)
async def writing_page():
    template_path = os.path.join(os.path.dirname(__file__), "app", "templates", "writing.html")
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()