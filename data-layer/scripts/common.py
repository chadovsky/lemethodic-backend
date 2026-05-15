"""
Le Méthodic data-layer common utilities.

Shared by every script. Provides:
- Config loading
- DB session factory
- Idempotent upsert helper
- Surface form normalization
- Logging setup
- License registry
"""

from __future__ import annotations

import logging
import os
import re
import unicodedata
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional

import yaml
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_CONFIG_CACHE: Optional[dict] = None


def load_config(path: str = "config.yml") -> dict:
    """Load and cache the config.yml file."""
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE
    cfg_path = Path(path)
    if not cfg_path.exists():
        raise FileNotFoundError(
            f"Config not found at {cfg_path.absolute()}. "
            "Did you copy config.example.yml to config.yml and edit it?"
        )
    with open(cfg_path, "r", encoding="utf-8") as f:
        _CONFIG_CACHE = yaml.safe_load(f)
    return _CONFIG_CACHE


def save_config(cfg: dict, path: str = "config.yml") -> None:
    """Persist config (used by decide.py)."""
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logger(name: str, log_dir: str = "logs") -> logging.Logger:
    """Per-stage logger; writes to logs/<name>_<timestamp>.log AND stdout."""
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    # Reset handlers in case of re-entry
    logger.handlers = []

    file_handler = logging.FileHandler(f"{log_dir}/{name}_{timestamp}.log", encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )
    logger.addHandler(file_handler)

    err_handler = logging.FileHandler(f"{log_dir}/errors.log", encoding="utf-8")
    err_handler.setLevel(logging.ERROR)
    err_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(name)s] %(message)s")
    )
    logger.addHandler(err_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(
        logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S")
    )
    logger.addHandler(stream_handler)

    return logger


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

_ENGINE: Optional[Engine] = None
_SESSION_FACTORY: Optional[sessionmaker] = None


def get_engine() -> Engine:
    global _ENGINE
    if _ENGINE is None:
        cfg = load_config()
        _ENGINE = create_engine(
            cfg["db"]["connection_string"],
            pool_pre_ping=True,
            future=True,
        )
    return _ENGINE


def get_session_factory() -> sessionmaker:
    global _SESSION_FACTORY
    if _SESSION_FACTORY is None:
        _SESSION_FACTORY = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _SESSION_FACTORY


@contextmanager
def db_session():
    """Context-managed session. Auto-commits on success, rolls back on error."""
    session: Session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def apply_sql(sql_path: str) -> None:
    """Execute a .sql file. Used by `make schema` and `make merge`."""
    log = setup_logger("apply_sql")
    log.info(f"Applying {sql_path}")
    sql = Path(sql_path).read_text(encoding="utf-8")
    with get_engine().begin() as conn:
        # Split on semicolons that end a line, preserve functions / triggers
        statements = _split_sql_statements(sql)
        for stmt in statements:
            stmt = stmt.strip()
            if stmt:
                conn.execute(text(stmt))
    log.info(f"Applied {sql_path} ({len(statements)} statements).")


def _split_sql_statements(sql: str) -> list[str]:
    """Naive splitter that respects $$ blocks (for trigger functions)."""
    parts: list[str] = []
    buf: list[str] = []
    in_dollar = False
    for line in sql.splitlines():
        if "$$" in line:
            # toggle once or twice per line
            n = line.count("$$")
            for _ in range(n):
                in_dollar = not in_dollar
        buf.append(line)
        if (not in_dollar) and line.rstrip().endswith(";"):
            parts.append("\n".join(buf))
            buf = []
    if buf:
        parts.append("\n".join(buf))
    return parts


def nuke_data() -> None:
    """DESTRUCTIVE: drop all chunk data. Used by `make nuke`."""
    log = setup_logger("nuke")
    log.warning("Nuking all chunk data.")
    with get_engine().begin() as conn:
        conn.execute(text("TRUNCATE chunks RESTART IDENTITY CASCADE"))
        conn.execute(text("TRUNCATE enrichment_log RESTART IDENTITY"))
    log.warning("All chunk data dropped.")


# ---------------------------------------------------------------------------
# Surface form normalization
# ---------------------------------------------------------------------------

_SMART_QUOTES = {
    "\u2018": "'", "\u2019": "'", "\u201A": "'", "\u201B": "'",
    "\u201C": '"', "\u201D": '"', "\u201E": '"', "\u201F": '"',
    "\u2032": "'", "\u2033": '"',
}
_WHITESPACE = re.compile(r"\s+")


def normalize_surface(surface: str) -> str:
    """
    Canonicalize a surface form for deduplication:
    - lowercase
    - strip whitespace
    - collapse internal whitespace
    - normalize smart quotes to ASCII
    - NFC unicode normalization
    Preserves accents (é, è, ç remain as themselves).
    """
    if surface is None:
        return ""
    s = unicodedata.normalize("NFC", surface).strip().lower()
    for k, v in _SMART_QUOTES.items():
        s = s.replace(k, v)
    s = _WHITESPACE.sub(" ", s)
    return s


# ---------------------------------------------------------------------------
# Idempotent upsert
# ---------------------------------------------------------------------------

_UPSERT_SQL = text("""
    INSERT INTO chunks (
        surface_fr, normalized_surface, lemma_fr, surface_en, language,
        chunk_type, pos_pattern, register, cefr_level,
        frequency_subtitles, frequency_books, frequency_web,
        is_quebec_specific, quebec_variant
    )
    VALUES (
        :surface_fr, :normalized_surface, :lemma_fr, :surface_en, :language,
        :chunk_type, :pos_pattern, :register, :cefr_level,
        :frequency_subtitles, :frequency_books, :frequency_web,
        :is_quebec_specific, :quebec_variant
    )
    ON CONFLICT (normalized_surface) DO UPDATE SET
        lemma_fr           = COALESCE(EXCLUDED.lemma_fr,           chunks.lemma_fr),
        surface_en         = COALESCE(EXCLUDED.surface_en,         chunks.surface_en),
        chunk_type         = COALESCE(EXCLUDED.chunk_type,         chunks.chunk_type),
        pos_pattern        = COALESCE(EXCLUDED.pos_pattern,        chunks.pos_pattern),
        register           = COALESCE(EXCLUDED.register,           chunks.register),
        cefr_level         = COALESCE(EXCLUDED.cefr_level,         chunks.cefr_level),
        frequency_subtitles= COALESCE(EXCLUDED.frequency_subtitles,chunks.frequency_subtitles),
        frequency_books    = COALESCE(EXCLUDED.frequency_books,    chunks.frequency_books),
        frequency_web      = COALESCE(EXCLUDED.frequency_web,      chunks.frequency_web),
        is_quebec_specific = chunks.is_quebec_specific OR EXCLUDED.is_quebec_specific,
        quebec_variant     = COALESCE(EXCLUDED.quebec_variant,     chunks.quebec_variant)
    RETURNING id
""")

_SOURCE_INSERT = text("""
    INSERT INTO chunk_sources (chunk_id, source_name, source_version, source_license, contributed_fields)
    VALUES (:chunk_id, :source_name, :source_version, :source_license, :contributed_fields)
    ON CONFLICT (chunk_id, source_name) DO UPDATE SET
        ingested_at = NOW(),
        contributed_fields = EXCLUDED.contributed_fields
""")


def upsert_chunk(
    session: Session,
    surface_fr: str,
    source_name: str,
    source_version: Optional[str] = None,
    source_license: Optional[str] = None,
    contributed_fields: Optional[list[str]] = None,
    **fields,
) -> int:
    """
    Insert or update a chunk. Idempotent — re-runs produce no duplicates.
    Tracks per-source provenance in chunk_sources.

    Returns the chunk's id.
    """
    normalized = normalize_surface(surface_fr)
    if not normalized:
        raise ValueError(f"Surface normalizes to empty: '{surface_fr}'")

    params: dict[str, Any] = {
        "surface_fr": surface_fr.strip(),
        "normalized_surface": normalized,
        "lemma_fr": fields.get("lemma_fr"),
        "surface_en": fields.get("surface_en"),
        "language": fields.get("language", "fr"),
        "chunk_type": fields.get("chunk_type"),
        "pos_pattern": fields.get("pos_pattern"),
        "register": fields.get("register"),
        "cefr_level": fields.get("cefr_level"),
        "frequency_subtitles": fields.get("frequency_subtitles"),
        "frequency_books": fields.get("frequency_books"),
        "frequency_web": fields.get("frequency_web"),
        "is_quebec_specific": fields.get("is_quebec_specific", False),
        "quebec_variant": fields.get("quebec_variant"),
    }

    result = session.execute(_UPSERT_SQL, params)
    chunk_id = result.scalar_one()

    session.execute(_SOURCE_INSERT, {
        "chunk_id": chunk_id,
        "source_name": source_name,
        "source_version": source_version,
        "source_license": source_license,
        "contributed_fields": contributed_fields or [],
    })

    return chunk_id


def insert_example(
    session: Session,
    chunk_id: int,
    example_fr: str,
    source_name: str,
    example_en: Optional[str] = None,
    cefr_level: Optional[str] = None,
) -> None:
    """Insert an example sentence. Deduplicates on (chunk_id, normalized example)."""
    if not example_fr or not example_fr.strip():
        return
    session.execute(text("""
        INSERT INTO chunk_examples (chunk_id, example_fr, example_en, cefr_level, source_name)
        SELECT :chunk_id, :example_fr, :example_en, :cefr_level, :source_name
        WHERE NOT EXISTS (
            SELECT 1 FROM chunk_examples
            WHERE chunk_id = :chunk_id
            AND lower(trim(example_fr)) = lower(trim(:example_fr))
        )
    """), {
        "chunk_id": chunk_id,
        "example_fr": example_fr.strip(),
        "example_en": (example_en or "").strip() or None,
        "cefr_level": cefr_level,
        "source_name": source_name,
    })


def batch_commit(session: Session, batch_size: int, counter: int) -> bool:
    """Commit every N rows. Returns True if a commit occurred."""
    if counter > 0 and counter % batch_size == 0:
        session.commit()
        return True
    return False


# ---------------------------------------------------------------------------
# License registry
# ---------------------------------------------------------------------------

LICENSE_REGISTRY = {
    "UniversalCEFR": {
        "license": "Mixed (per-dataset)",
        "attribution": "Texts from UniversalCEFR project on Hugging Face.",
        "url": "https://huggingface.co/UniversalCEFR",
        "commercial_use": "Conditional — per-source verification required.",
    },
    "Lexique3": {
        "license": "CC-BY-SA-4.0",
        "attribution": "New B. & Pallier C. (2001). Lexique 3.",
        "url": "http://www.lexique.org",
        "commercial_use": "Yes, with attribution.",
    },
    "PARSEME": {
        "license": "CC-BY-4.0 (varies by language)",
        "attribution": "PARSEME multilingual corpus of verbal MWEs.",
        "url": "https://gitlab.com/parseme",
        "commercial_use": "Yes, with attribution.",
    },
    "CollFrEn": {
        "license": "Open (research)",
        "attribution": "Fisas et al. CollFrEn (2020).",
        "url": "https://github.com/TalnUPF/CollFrEn",
        "commercial_use": "Verify per current repo terms.",
    },
    "DBnary": {
        "license": "CC-BY-SA-3.0 (inherited from Wiktionary)",
        "attribution": "DBnary project, derived from Wiktionary contributors.",
        "url": "http://kaiko.getalp.org/about-dbnary/",
        "commercial_use": "Yes, with share-alike obligations.",
    },
    "AnkiWeb": {
        "license": "Per-deck (varies)",
        "attribution": "Community-contributed Anki decks (per-deck attribution).",
        "url": "https://ankiweb.net",
        "commercial_use": "Per-deck verification required.",
    },
    "Tatoeba": {
        "license": "CC-BY-2.0-FR",
        "attribution": "Sentences from Tatoeba.",
        "url": "https://tatoeba.org",
        "commercial_use": "Yes, with attribution.",
    },
    "WikipediaFR": {
        "license": "CC-BY-SA",
        "attribution": "French Wikipedia article titles + lead extracts (Wikipedia contributors).",
        "url": "https://fr.wikipedia.org",
        "commercial_use": "Yes, with attribution + share-alike.",
    },
}


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------

def ensure_dirs() -> None:
    cfg = load_config()
    for key in ("raw_dir", "processed_dir", "logs_dir"):
        Path(cfg["data"][key]).mkdir(parents=True, exist_ok=True)
