import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    APP_NAME: str = "TCF Oral Practice Tool"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production-please")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24h

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

    # Audio storage
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
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
    TTS_CACHE_DIR: str = os.getenv("TTS_CACHE_DIR", "data/tts_cache")
    TTS_COST_LOG: str = os.getenv("TTS_COST_LOG", "data/tts_cost.log")

settings = Settings()
