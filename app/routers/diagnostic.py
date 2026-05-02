"""P-221 — diagnostic state endpoint.

GET /api/diagnostic/state — read-only state machine for the
3-recording diagnostic flow. Drives the /ecole banner and the one-time
"diagnostic complete" results screen on the FE.

See app/schemas/diagnostic.py and app/services/diagnostic_state.py for
the contract and state-transition rationale.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import User
from app.schemas.diagnostic import DiagnosticStateResponse
from app.services.auth import get_current_user
from app.services.diagnostic_state import get_diagnostic_state


router = APIRouter(prefix="/api/diagnostic", tags=["diagnostic"])


@router.get("/state", response_model=DiagnosticStateResponse)
def diagnostic_state(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DiagnosticStateResponse:
    return DiagnosticStateResponse(**get_diagnostic_state(db, user))
