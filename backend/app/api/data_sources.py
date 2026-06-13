"""Data source registry & data quality check endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.responses import ok
from app.core.database import get_db
from app.models import DataQualityCheck, DataSourceRegistry, FetchLog

router = APIRouter(tags=["data-sources"])


@router.get("/data-sources")
def list_data_sources(db: Session = Depends(get_db)) -> dict:
    rows = db.query(DataSourceRegistry).order_by(DataSourceRegistry.id).all()
    data = [
        {
            "id": r.id,
            "source_name": r.source_name,
            "source_type": r.source_type,
            "base_url": r.base_url,
            "description": r.description,
            "update_frequency": r.update_frequency,
            "reliability_level": r.reliability_level,
            "license_note": r.license_note,
            "enabled": r.enabled,
        }
        for r in rows
    ]
    return ok(data)


@router.get("/data-quality")
def list_data_quality(
    dataset_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> dict:
    query = db.query(DataQualityCheck)
    if dataset_type is not None:
        query = query.filter(DataQualityCheck.dataset_type == dataset_type)
    if status is not None:
        query = query.filter(DataQualityCheck.status == status)
    rows = query.order_by(DataQualityCheck.id.desc()).limit(limit).all()
    data = [
        {
            "id": r.id,
            "dataset_type": r.dataset_type,
            "dataset_key": r.dataset_key,
            "check_name": r.check_name,
            "status": r.status,
            "severity": r.severity,
            "message": r.message,
            "checked_at": r.checked_at,
        }
        for r in rows
    ]
    return ok(data)


@router.get("/data-sources/fetch-logs")
def list_fetch_logs(
    dataset_type: str | None = Query(default=None),
    provider_name: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> dict:
    query = db.query(FetchLog)
    if dataset_type is not None:
        query = query.filter(FetchLog.dataset_type == dataset_type)
    if provider_name is not None:
        query = query.filter(FetchLog.provider_name == provider_name)
    rows = query.order_by(FetchLog.id.desc()).limit(limit).all()
    data = [
        {
            "id": r.id,
            "provider_name": r.provider_name,
            "dataset_type": r.dataset_type,
            "status": r.status,
            "rows_fetched": r.rows_fetched,
            "rows_inserted": r.rows_inserted,
            "source_url": r.source_url,
            "data_date": r.data_date,
            "message": r.message,
            "started_at": r.started_at,
            "finished_at": r.finished_at,
        }
        for r in rows
    ]
    return ok(data)
