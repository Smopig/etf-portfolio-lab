"""Reverse-lookup endpoints: industry -> ETF ranking, stock -> ETFs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.responses import ok
from app.core.database import get_db
from app.services.reverse_lookup_service import find_etfs_by_industry, find_etfs_by_stock

router = APIRouter(tags=["industries"])


@router.get("/industries/{industry}/etf-ranking")
def industry_etf_ranking(
    industry: str,
    level: int = Query(default=1, ge=1, le=2),
    db: Session = Depends(get_db),
) -> dict:
    return ok(find_etfs_by_industry(db, industry, level=level))


@router.get("/stocks/{stock_symbol}/etfs")
def stock_etfs(stock_symbol: str, db: Session = Depends(get_db)) -> dict:
    return ok(find_etfs_by_stock(db, stock_symbol))
