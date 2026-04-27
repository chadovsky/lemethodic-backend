from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
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
from app.models.models import User
from app.services.auth import get_current_user
from app.config import settings

# F-077: schema is now owned by Alembic. Run `alembic upgrade head` on
# fresh checkouts and after pulling migrations. The previous
# `Base.metadata.create_all(bind=engine)` call was removed here so the
# app no longer silently creates tables out-of-band — any schema drift
# now surfaces as an explicit Alembic-level mismatch instead of being
# papered over.

app = FastAPI(title="TCF Oral Practice Tool")

# CORS — allow the v0/Next.js frontend to talk to this backend.
# Add production origins here before launch (F-060).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # Next.js dev server
        "http://127.0.0.1:3000",   # alt localhost form
    ],
    allow_credentials=True,
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

# Serve static files
import os
static_dir = os.path.join(os.path.dirname(__file__), "app", "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# F-052 / F-075b: serve the TTS cache so the <audio> elements in the
# Tâche 1/2 UI can fetch ``/tts_audio/<sha256>.mp3``. Ensure the
# directory exists at startup.
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
# Path traversal guard: reject any filename containing path
# separators or `..`, then double-check via Path.resolve() that the
# resolved file is still inside the cache dir (catches symlink
# escapes too).
_tts_cache_dir = os.path.abspath(settings.TTS_CACHE_DIR)
os.makedirs(_tts_cache_dir, exist_ok=True)


@app.get("/tts_audio/{filename}")
def serve_tts_audio(
    filename: str,
    user: User = Depends(get_current_user),
):
    # First-pass filename guard. Reject anything with path
    # separators, parent-dir traversal, or null bytes. The cache
    # writer only ever produces ``<sha256>.mp3`` filenames so this
    # is the canonical shape; anything else is suspect.
    if (
        "/" in filename
        or "\\" in filename
        or ".." in filename
        or "\x00" in filename
        or filename.startswith(".")
    ):
        raise HTTPException(status_code=400, detail="Invalid filename")

    from pathlib import Path
    cache_root = Path(_tts_cache_dir).resolve()
    target = (cache_root / filename).resolve()

    # Second-pass: even after the string-level filter, confirm the
    # resolved path actually lives inside the cache dir. Catches
    # symlink-based escapes and any future filename quirk the
    # string filter doesn't anticipate.
    try:
        target.relative_to(cache_root)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not target.is_file():
        raise HTTPException(status_code=404, detail="Audio not found")

    # The TTS pipeline only emits .mp3, but infer defensively in case
    # a future provider adds wav/ogg cache entries.
    ext = target.suffix.lower()
    media_type = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".ogg": "audio/ogg",
        ".m4a": "audio/mp4",
        ".webm": "audio/webm",
    }.get(ext, "application/octet-stream")

    return FileResponse(target, media_type=media_type)


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