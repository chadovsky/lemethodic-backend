"""P-234 — cluster detail view endpoints.

Two read-only endpoints back the FE cluster detail page:

  GET /api/clusters/{slug}              → curriculum content
  GET /api/users/me/clusters/{slug}     → per-user state + history

Both authenticated (Q5 lock-in — any logged-in user; no path-
enrollment scoping). 404 on unknown slugs; graceful defaults when
the user has no UserClusterStatus row (Q3).

See `app/schemas/cluster.py` for the shape contract and
`app/services/cluster_lookup.py` for the data-fetch implementation.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import User
from app.schemas.cluster import (
    ClusterDetailResponse,
    UserClusterStateResponse,
)
from app.services.auth import get_current_user
from app.services.cluster_lookup import (
    get_cluster_detail,
    get_user_cluster_state,
)


router = APIRouter(tags=["clusters"])


@router.get("/api/clusters/{slug}", response_model=ClusterDetailResponse)
def cluster_detail(
    slug: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClusterDetailResponse:
    payload = get_cluster_detail(db, slug)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cluster '{slug}' not found",
        )
    return ClusterDetailResponse(**payload)


@router.get(
    "/api/users/me/clusters/{slug}",
    response_model=UserClusterStateResponse,
)
def user_cluster_state(
    slug: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserClusterStateResponse:
    payload = get_user_cluster_state(db, user, slug)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cluster '{slug}' not found",
        )
    return UserClusterStateResponse(**payload)
