"""Data import status endpoint (MVP placeholder).

File-upload based data import is Phase 2 / CLI-driven for now. This endpoint
provides a minimal read-only summary of recent data quality checks so the
frontend can show "last import status" without implementing upload yet.

TODO (future phase): add POST /api/imports endpoints for file-upload-driven
ingestion once the import UI is designed.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.responses import ok
from app.core.database import get_db
from app.models import DataQualityCheck

router = APIRouter(tags=["data-import"])


@router.get("/imports/status")
def import_status(db: Session = Depends(get_db)) -> dict:
    recent = (
        db.query(DataQualityCheck)
        .order_by(DataQualityCheck.id.desc())
        .limit(10)
        .all()
    )
    data = {
        "recent_quality_checks": [
            {
                "dataset_type": r.dataset_type,
                "dataset_key": r.dataset_key,
                "check_name": r.check_name,
                "status": r.status,
                "checked_at": r.checked_at,
            }
            for r in recent
        ],
        "note": (
            "File-upload based data import is not implemented in this phase; "
            "data is currently loaded via CLI importers (Phase 2)."
        ),
    }
    return ok(data)
