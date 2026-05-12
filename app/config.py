import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    APP_NAME: str = "TCF Oral Practice Tool"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production-please")
    ALGORITHM: str = "HS256"
    # F-310 Phase B (2026-05-12): dropped from 1440 (24h) to 15 minutes
    # alongside the refresh-token flow. Access tokens are short-lived;
    # the FE refreshes silently on 401 via /api/auth/refresh, which mints
    # a fresh 15-min access + rotates the 7-day refresh.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))

    # F-077: PostgreSQL is now the dev + prod database. Default points
    # at the local docker-compose Postgres (matching docker-compose.yml).
    # The conditional `connect_args` in app/database.py still handles
    # SQLite if anyone overrides DATABASE_URL to a sqlite path for a
    # one-off script, but the live app expects Postgres.
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://fluentpath:fluentpath_local_dev@localhost:5432/fluentpath",
    )

    # AssemblyAI
    ASSEMBLYAI_API_KEY: str = os.getenv("ASSEMBLYAI_API_KEY", "")

    # Claude API
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    # ── F-078 storage layout ──────────────────────────────────
    # All persistent file storage lives under STORAGE_LOCAL_ROOT in
    # local dev. Production (DO Spaces) ignores this — see
    # app/services/storage.py for backend selection.
    #
    # Subdirectories under STORAGE_LOCAL_ROOT:
    #   uploads/        user audio recordings (storage keys: uploads/<uuid>.<ext>)
    #   tts_cache/      OpenAI TTS mp3 cache  (storage keys: tts_cache/<sha256>.mp3)
    #
    # UPLOAD_DIR / TTS_CACHE_DIR are derived from STORAGE_LOCAL_ROOT
    # for any code that still references them directly (verification
    # harnesses, route-level os.makedirs no-ops). New write/read sites
    # MUST go through app.services.storage instead so the Spaces
    # backend takes over transparently in production.
    STORAGE_LOCAL_ROOT: str = os.getenv("STORAGE_LOCAL_ROOT", "./storage")
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", os.path.join(STORAGE_LOCAL_ROOT, "uploads"))
    MAX_AUDIO_SECONDS: int = 900  # 15 min max for TCF Task 3
    # F-075a — server-side cap on incoming audio uploads. Enforced at
    # two layers:
    #   (A) main.py middleware on any POST with Content-Type:
    #       multipart/form-data — rejects via Content-Length before
    #       FastAPI buffers the body into memory.
    #   (B) per-route defensive check after `await audio.read()` —
    #       guards against spoofed / chunked transfer encoding.
    # 10 MB gives ~6x headroom over the largest legitimate file in the
    # current corpus (1.68 MB). Raise to 15 MB only if real-world
    # recordings start approaching the cap; do not exceed 20 MB
    # without a real reason. Override via env if needed for testing.
    MAX_AUDIO_UPLOAD_BYTES: int = int(os.getenv("MAX_AUDIO_UPLOAD_BYTES", str(10 * 1024 * 1024)))

    # ── F-052 Text-to-Speech (AI examiner voice) ─────────────
    # Provider abstraction: only "openai" is implemented today. If Chadi
    # later swaps to ElevenLabs, add a second backend in tts.py and
    # switch on this value.
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    TTS_PROVIDER: str = os.getenv("TTS_PROVIDER", "openai")
    # OpenAI voice choices for each Tâche:
    #   Tâche 1 (self-presentation + follow-ups) — "nova":
    #     Warmer, more encouraging feminine voice. Matches the "teacher
    #     who wants you to succeed" tone of the F-048 persona.
    #   Tâche 2 (role-play, various characters) — "echo":
    #     Slightly more neutral masculine voice. Less
    #     counter-productive for characters that aren't grandmotherly
    #     (travel agent, real estate agent, Québécois colleague).
    # Both are OpenAI built-in voices on tts-1-hd.
    TTS_VOICE_TACHE_1: str = os.getenv("TTS_VOICE_TACHE_1", "nova")
    TTS_VOICE_TACHE_2: str = os.getenv("TTS_VOICE_TACHE_2", "echo")
    # Cache + cost-log locations. Cache hashes (text, voice, model) →
    # an mp3 on disk; cost log is a plain append-only JSONL.
    # F-078: cache dir derives from STORAGE_LOCAL_ROOT for the local
    # fallback backend. Cost log stays where it was — small append-only
    # JSONL kept on local disk only; ephemeral on App Platform is fine
    # for the soft-beta unit-economics dashboard.
    TTS_CACHE_DIR: str = os.getenv("TTS_CACHE_DIR", os.path.join(STORAGE_LOCAL_ROOT, "tts_cache"))
    TTS_COST_LOG: str = os.getenv("TTS_COST_LOG", "data/tts_cost.log")

    # ── F-310 auth hardening (Phase A) ───────────────────────
    # ENV gates production-only behaviors (secure cookie flag, etc.).
    # Set to "production" on the DO App Platform deploy.
    ENV: str = os.getenv("ENV", "development")

    # Redis: rate-limit counters + refresh-token revocation set + (F-311)
    # per-tier diagnostic counters. Defaults to docker-compose local.
    # Production override via env-injection.
    #
    # Production host choice (locked 2026-05-12 per Chadi):
    #   DigitalOcean Managed Redis. BE already runs on DO App Platform;
    #   same-region pairing = sub-ms latency, integrated billing, no
    #   extra account. Upstash is the alternative if serverless-friendly
    #   pricing matters later; DO managed is the right call for soft beta.
    #   Provisioning happens before Phase E smoke; DATABASE-shaped env
    #   inject (REDIS_URL) at deploy time.
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # hCaptcha: SECRET stays server-side; SITEKEY exposed to FE via a
    # /api/config/public endpoint Phase C ships (or hardcoded in FE
    # build, FE's call). Fail-closed when SECRET unset.
    HCAPTCHA_SECRET: str = os.getenv("HCAPTCHA_SECRET", "")
    HCAPTCHA_SITEKEY: str = os.getenv("HCAPTCHA_SITEKEY", "")

    # Stripe webhook secret. Payload handler is P-106; Phase A/D wire
    # the verification + a bare endpoint shell.
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    # Transactional email. Provider pluggable; only "resend" is
    # implemented in Phase A (Chadi sign-off 2026-05-12).
    EMAIL_PROVIDER: str = os.getenv("EMAIL_PROVIDER", "resend")
    EMAIL_FROM_ADDRESS: str = os.getenv("EMAIL_FROM_ADDRESS", "noreply@lemethodic.com")
    EMAIL_FROM_NAME: str = os.getenv("EMAIL_FROM_NAME", "Le Méthodic")
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")

    # Refresh-token lifetime. Phase B wires the actual mint/verify flow;
    # default visible now so the JWT helpers in Phase B import from one
    # source of truth. Access-token lifetime stays at the legacy 1440
    # until Phase B drops it to 15 alongside the refresh flow.
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # F-310 Phase C — FE base URL used in email links (verify-email +
    # password-reset). Distinct from FRONTEND_ORIGIN (which is the CORS
    # allowlist consumed inline in main.py and can be comma-separated).
    # Defaults to the production canonical domain so a missing env var
    # in dev sends links to prod — annoying but not dangerous.
    FRONTEND_PUBLIC_URL: str = os.getenv("FRONTEND_PUBLIC_URL", "https://lemethodic.com")

settings = Settings()
