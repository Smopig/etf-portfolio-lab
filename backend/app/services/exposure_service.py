"""Industry exposure aggregation for a single ETF's holdings."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import EtfHolding, StockIndustry
from app.utils.finance_math import normalize_weights_to_fraction

UNCLASSIFIED = "Unclassified"


def _latest_holding_date(session: Session, etf_symbol: str) -> dt.date | None:
    return (
        session.query(func.max(EtfHolding.holding_date))
        .filter(EtfHolding.etf_symbol == etf_symbol)
        .scalar()
    )


def _resolve_holding_date(
    session: Session, etf_symbol: str, holding_date: dt.date | None
) -> dt.date | None:
    if holding_date is not None:
        return holding_date
    return _latest_holding_date(session, etf_symbol)


def _industry_level_attr(level: int):
    if level == 2:
        return StockIndustry.industry_level_2
    return StockIndustry.industry_level_1


def get_industry_exposure(
    session: Session,
    etf_symbol: str,
    holding_date: dt.date | None = None,
    level: int = 1,
) -> dict:
    """Aggregate normalized holding weights by industry classification.

    Returns:
        {
          etf_symbol, holding_date, level,
          industries: [{industry, weight_fraction, weight_pct}, ...] (desc),
          max_industry: {...} | None,
          top3_industries: [...],
          unclassified: {industry, weight_fraction, weight_pct},
        }
    """
    resolved_date = _resolve_holding_date(session, etf_symbol, holding_date)
    if resolved_date is None:
        return {
            "etf_symbol": etf_symbol,
            "holding_date": None,
            "level": level,
            "industries": [],
            "max_industry": None,
            "top3_industries": [],
            "unclassified": {
                "industry": UNCLASSIFIED,
                "weight_fraction": 0.0,
                "weight_pct": 0.0,
            },
        }

    holdings = (
        session.query(EtfHolding)
        .filter(
            EtfHolding.etf_symbol == etf_symbol,
            EtfHolding.holding_date == resolved_date,
        )
        .all()
    )

    if not holdings:
        return {
            "etf_symbol": etf_symbol,
            "holding_date": resolved_date,
            "level": level,
            "industries": [],
            "max_industry": None,
            "top3_industries": [],
            "unclassified": {
                "industry": UNCLASSIFIED,
                "weight_fraction": 0.0,
                "weight_pct": 0.0,
            },
        }

    raw_weights = [
        float(h.weight) if h.weight is not None else 0.0 for h in holdings
    ]
    fractions = normalize_weights_to_fraction(raw_weights)

    # Load the full industry map once (avoid N+1).
    asset_symbols = {h.asset_symbol for h in holdings if h.asset_symbol}
    industry_attr = _industry_level_attr(level)
    industry_map: dict[str, str | None] = {}
    if asset_symbols:
        rows = (
            session.query(StockIndustry.stock_symbol, industry_attr)
            .filter(StockIndustry.stock_symbol.in_(asset_symbols))
            .all()
        )
        industry_map = {symbol: industry for symbol, industry in rows}

    totals: dict[str, float] = {}
    for h, frac in zip(holdings, fractions):
        industry = None
        if h.asset_symbol:
            industry = industry_map.get(h.asset_symbol)
        key = industry if industry else UNCLASSIFIED
        totals[key] = totals.get(key, 0.0) + frac

    industries = [
        {"industry": k, "weight_fraction": v, "weight_pct": v * 100}
        for k, v in totals.items()
        if k != UNCLASSIFIED
    ]
    industries.sort(key=lambda x: x["weight_fraction"], reverse=True)

    unclassified_fraction = totals.get(UNCLASSIFIED, 0.0)
    unclassified = {
        "industry": UNCLASSIFIED,
        "weight_fraction": unclassified_fraction,
        "weight_pct": unclassified_fraction * 100,
    }

    return {
        "etf_symbol": etf_symbol,
        "holding_date": resolved_date,
        "level": level,
        "industries": industries,
        "max_industry": industries[0] if industries else None,
        "top3_industries": industries[:3],
        "unclassified": unclassified,
    }
