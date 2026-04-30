"""F-078 — Storage abstraction over local disk + DigitalOcean Spaces.

Single module for every persistent file write/read in the app. Backend
selected automatically:

  * If ``DO_SPACES_BUCKET`` env var is set → boto3 against Spaces.
  * Otherwise → local filesystem rooted at ``settings.STORAGE_LOCAL_ROOT``.

This means production (App Platform with Spaces creds injected) goes
through Spaces; local dev (no creds) falls through to disk transparently.
The fallback is also the soft-beta safety net — if Spaces creds are
misconfigured in production, the app stays functional (container
restart loses files, but uploads/sessions in-flight don't fail).

**Storage keys** are forward-slash relative paths like
``uploads/<uuid>.<ext>`` or ``tts_cache/<sha256>.mp3``. The local
backend writes them under ``STORAGE_LOCAL_ROOT/<key>``; Spaces writes
them as the literal object key. Callers MUST use forward slashes —
backslashes would land in S3 as part of the key name on Spaces and
create cross-platform breakage on disk.

**Async note:** boto3 is synchronous. Calling ``write_bytes`` from an
async route handler blocks the event loop during the upload (~50–200 ms
per call on Spaces). This is acceptable for soft-beta scale (5–10 users).
F-078.x in BACKLOG covers the migration to ``aioboto3`` post-launch.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from app.config import settings

if TYPE_CHECKING:  # avoid importing fastapi at module import time
    from fastapi.responses import Response

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────
# Backend selection
# ──────────────────────────────────────────────────────────────────


def _spaces_enabled() -> bool:
    """True when DO_SPACES_BUCKET is set — selects the Spaces backend.

    Read at every call (cheap) so test suites can flip between modes
    by mutating os.environ without re-importing this module.
    """
    return bool(os.getenv("DO_SPACES_BUCKET"))


def _spaces_client():
    """Boto3 S3 client configured for DO Spaces.

    Region defaults to ``fra1`` (Frankfurt — closest to Morocco). The
    ``signature_version="s3v4"`` is required for Spaces; default sigv2
    fails with ``InvalidArgument`` on PutObject.
    """
    import boto3
    from botocore.client import Config

    region = os.getenv("DO_SPACES_REGION", "fra1")
    return boto3.client(
        "s3",
        region_name=region,
        endpoint_url=f"https://{region}.digitaloceanspaces.com",
        aws_access_key_id=os.getenv("DO_SPACES_KEY"),
        aws_secret_access_key=os.getenv("DO_SPACES_SECRET"),
        config=Config(signature_version="s3v4"),
    )


def _local_path(key: str) -> Path:
    """Resolve a storage key to its local-disk path under STORAGE_LOCAL_ROOT."""
    return Path(settings.STORAGE_LOCAL_ROOT) / key


# ──────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────


def write_bytes(key: str, content: bytes, content_type: str = "application/octet-stream") -> None:
    """Persist ``content`` under ``key``. Creates parent dirs in the
    local fallback; Spaces requires no setup."""
    if _spaces_enabled():
        client = _spaces_client()
        # DO Spaces rejects Content-Type values that include media-type
        # parameters (e.g. ``audio/webm;codecs=opus`` from MediaRecorder)
        # with InvalidArgument on PutObject. Strip everything after ``;``.
        clean_content_type = (
            content_type.split(";")[0].strip()
            if content_type
            else "application/octet-stream"
        )
        # DEBUG: trace entry into Spaces write path. Throwaway, remove once
        # the prod 500 is diagnosed.
        print(
            f"DEBUG storage.write_bytes called key={key!r} "
            f"bucket={os.getenv('DO_SPACES_BUCKET')!r} "
            f"region={os.getenv('DO_SPACES_REGION', 'fra1')!r} "
            f"content_len={len(content)} content_type={content_type!r} "
            f"clean_content_type={clean_content_type!r}",
            flush=True,
        )
        # DEBUG: surface the actual endpoint boto3 is using and the
        # exact type/prefix of the body, in case content is a wrapper
        # (BytesIO, memoryview) or the endpoint is being mangled.
        print(
            f"DEBUG endpoint_url={client.meta.endpoint_url} "
            f"type(content)={type(content).__name__} "
            f"content_first16={content[:16]!r}",
            flush=True,
        )
        try:
            client.put_object(
                Bucket=os.getenv("DO_SPACES_BUCKET"),
                Key=key,
                Body=content,
                ContentType=clean_content_type,
            )
            # DEBUG: confirm put_object returned without raising. If we
            # see BEFORE but not this and not the error log, the exception
            # is escaping our except clause (class mismatch / BaseException).
            print(f"DEBUG put_object succeeded key={key!r}", flush=True)
        except Exception as exc:
            # DEBUG: surface full Spaces error envelope (ArgumentName /
            # ArgumentValue point at the offending field on InvalidArgument).
            # Uses print() to stdout because app.services.storage ERROR logs
            # are dropped by the prod log sink (no handler on root logger).
            # Remove once the prod 500 is diagnosed.
            err = getattr(exc, "response", {}).get("Error", {})
            print(
                f"Spaces PutObject failed key={key!r} "
                f"bucket={os.getenv('DO_SPACES_BUCKET')!r} "
                f"region={os.getenv('DO_SPACES_REGION', 'fra1')!r} "
                f"error={err!r}",
                flush=True,
            )
            logger.error(
                "Spaces PutObject failed key=%r bucket=%r region=%r error=%r",
                key,
                os.getenv("DO_SPACES_BUCKET"),
                os.getenv("DO_SPACES_REGION", "fra1"),
                err,
            )
            raise
        return

    target = _local_path(key)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Direct write — no atomic-rename safety. Acceptable: a corrupt
    # write only occurs on hard crash mid-flush, and the worst case
    # (a half-written TTS mp3 served once before being re-cached) is
    # benign. The previous tts.py atomic-rename pattern is gone with
    # Spaces (PUT is atomic by definition).
    with open(target, "wb") as f:
        f.write(content)


def read_bytes(key: str) -> bytes:
    """Fetch ``key`` from storage. Raises FileNotFoundError if missing
    so callers can convert to 404 without leaking backend internals."""
    if _spaces_enabled():
        client = _spaces_client()
        try:
            response = client.get_object(Bucket=os.getenv("DO_SPACES_BUCKET"), Key=key)
            return response["Body"].read()
        except client.exceptions.NoSuchKey:
            raise FileNotFoundError(f"Spaces key not found: {key}")
        except Exception as exc:
            error_code = getattr(exc, "response", {}).get("Error", {}).get("Code", "")
            if error_code in ("NoSuchKey", "404", "NotFound"):
                raise FileNotFoundError(f"Spaces key not found: {key}")
            raise

    target = _local_path(key)
    if not target.is_file():
        raise FileNotFoundError(f"Local storage key not found: {key}")
    return target.read_bytes()


def exists(key: str) -> bool:
    """Cheap presence check. False on not-found; raises on infra errors
    so a bad bucket / network outage doesn't masquerade as cache miss."""
    if _spaces_enabled():
        client = _spaces_client()
        try:
            client.head_object(Bucket=os.getenv("DO_SPACES_BUCKET"), Key=key)
            return True
        except Exception as exc:
            # Spaces returns 404 / NoSuchKey for missing objects. Any
            # other error code (403, 500, network) re-raises so the
            # caller can decide — silently returning False would mask
            # auth failures as cache misses and cause re-synthesis loops.
            error_code = getattr(exc, "response", {}).get("Error", {}).get("Code", "")
            if error_code in ("404", "NoSuchKey", "NotFound"):
                return False
            raise

    return _local_path(key).is_file()


def stream_response(key: str, content_type: str = "application/octet-stream") -> "Response":
    """Build a FastAPI response that returns the bytes at ``key``.

    Used by audio-serving handlers (currently F-075b ``/tts_audio/...``).
    The whole body is read into memory before responding — fine for
    audio clips well under the 10 MB upload cap; revisit if larger
    files start being served. Raises FileNotFoundError on miss; the
    handler is expected to convert that to a 404.
    """
    from fastapi.responses import Response

    content = read_bytes(key)
    return Response(content=content, media_type=content_type)
