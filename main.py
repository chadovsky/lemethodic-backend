from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from app.database import engine, Base
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
from app.models import writing as writing_models  # ensure tables are created
from app.config import settings

# Create tables
Base.metadata.create_all(bind=engine)

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

# F-052: serve the TTS cache so the <audio> elements in the Tâche 1/2
# UI can fetch ``/tts_audio/<sha256>.mp3``. Ensure the directory exists
# at startup so StaticFiles doesn't bail out.
from app.config import settings as _settings  # noqa: E402
_tts_cache_dir = os.path.abspath(_settings.TTS_CACHE_DIR)
os.makedirs(_tts_cache_dir, exist_ok=True)
app.mount("/tts_audio", StaticFiles(directory=_tts_cache_dir), name="tts_audio")


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