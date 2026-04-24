"""Pattern catalog API — static reference data, no auth required.

Frontend fetches once on page load and caches in window.PATTERN_LABELS.
"""
from fastapi import APIRouter

from app.services.pattern_catalog import PATTERN_LABELS

router = APIRouter(prefix="/api/patterns", tags=["patterns"])


@router.get("/labels")
def get_pattern_labels() -> dict[str, str]:
    """Return the full {key: label} map for client-side rendering."""
    return PATTERN_LABELS
