"""ETF endpoints: list, card, holdings, concentration, exposure, compare, overlap."""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.responses import not_found, ok, validation_error
from app.core.database import get_db
from app.models import EtfMaster
from app.services.concentration_service import (
    get_concentration,
    get_holdings_meta,
    get_top_holdings,
)
from app.services.dashboard_service import (
    RANKING_METRICS,
    get_holdings_and_price_symbol_sets,
    rank_etfs,
)
from app.services.etf_card_service import get_etf_card
from app.services.exposure_service import get_industry_exposure
from app.services.overlap_service import (
    get_industry_similarity,
    get_multi_overlap,
    get_pairwise_overlap,
)
from app.services.price_service import get_latest_prices, get_price_history, get_price_ranges

router = APIRouter(prefix="/etfs", tags=["etfs"])


def _split_symbols(symbols: str) -> list[str]:
    parts = [s.strip() for s in symbols.split(",") if s.strip()]
    if not parts:
        raise validation_error("symbols query parameter must contain at least one symbol.")
    return parts


@router.get("")
def list_etfs(
    active: bool | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict:
    query = db.query(EtfMaster)
    if active is not None:
        query = query.filter(EtfMaster.is_active == active)
    rows = query.order_by(EtfMaster.symbol).all()
    holdings_symbols, price_symbols = get_holdings_and_price_symbol_sets(db)
    latest_prices = get_latest_prices(db, symbols=[r.symbol for r in rows])
    data = [
        {
            "symbol": r.symbol,
            "name": r.name,
            "issuer": r.issuer,
            "asset_class": r.asset_class,
            "management_type": r.management_type,
            "is_active": r.is_active,
            "has_holdings": r.symbol in holdings_symbols,
            "has_price_data": r.symbol in price_symbols,
            "latest_close": latest_prices.get(r.symbol, {}).get("close"),
            "latest_date": latest_prices.get(r.symbol, {}).get("date"),
            "change_pct": latest_prices.get(r.symbol, {}).get("change_pct"),
        }
        for r in rows
    ]
    return ok(data)


@router.get("/ranking")
def get_etfs_ranking(
    metric: str = Query(...),
    order: str = Query(default="desc"),
    limit: int = Query(default=10, ge=1, le=100),
    industry: str | None = Query(default=None),
    level: int = Query(default=1, ge=1, le=2),
    db: Session = Depends(get_db),
) -> dict:
    if metric not in RANKING_METRICS:
        raise validation_error(
            f"metric must be one of {', '.join(RANKING_METRICS)}."
        )
    if metric == "industry_exposure" and not industry:
        raise validation_error("industry parameter is required for metric=industry_exposure.")
    if order not in ("asc", "desc"):
        raise validation_error("order must be 'asc' or 'desc'.")
    results = rank_etfs(db, metric=metric, order=order, limit=limit, industry=industry, level=level)
    return ok(results, meta={"metric": metric, "order": order, "limit": limit})


@router.get("/compare")
def compare_etfs(symbols: str = Query(...), db: Session = Depends(get_db)) -> dict:
    syms = _split_symbols(symbols)
    return ok(get_multi_overlap(db, syms))


@router.get("/overlap")
def overlap_etfs(symbols: str = Query(...), db: Session = Depends(get_db)) -> dict:
    syms = _split_symbols(symbols)
    if len(syms) != 2:
        raise validation_error("overlap requires exactly 2 symbols.")
    pairwise = get_pairwise_overlap(db, syms[0], syms[1])
    industry_similarity = get_industry_similarity(db, syms[0], syms[1])
    return ok({"overlap": pairwise, "industry_similarity": industry_similarity})


@router.get("/price-range")
def get_etf_price_range(symbols: str = Query(...), db: Session = Depends(get_db)) -> dict:
    syms = _split_symbols(symbols)
    return ok(get_price_ranges(db, syms))


@router.get("/{symbol}")
def get_etf(symbol: str, db: Session = Depends(get_db)) -> dict:
    card = get_etf_card(db, symbol)
    if card is None:
        raise not_found(f"ETF '{symbol}' not found.")
    return ok(card)


@router.get("/{symbol}/holdings")
def get_holdings(
    symbol: str,
    date: dt.date | None = Query(default=None),
    n: int = Query(default=10, ge=1, le=200),
    db: Session = Depends(get_db),
) -> dict:
    items = get_top_holdings(db, symbol, holding_date=date, n=n)
    meta = get_holdings_meta(db, symbol, holding_date=date)
    return ok(items, meta=meta)


@router.get("/{symbol}/prices")
def get_etf_prices(
    symbol: str,
    start: dt.date | None = Query(default=None),
    end: dt.date | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=5000),
    db: Session = Depends(get_db),
) -> dict:
    return ok(get_price_history(db, symbol, start=start, end=end, limit=limit))


@router.get("/{symbol}/concentration")
def get_etf_concentration(
    symbol: str,
    date: dt.date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict:
    return ok(get_concentration(db, symbol, holding_date=date))


@router.get("/{symbol}/industry-exposure")
def get_etf_industry_exposure(
    symbol: str,
    level: int = Query(default=1, ge=1, le=2),
    date: dt.date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict:
    return ok(get_industry_exposure(db, symbol, holding_date=date, level=level))
