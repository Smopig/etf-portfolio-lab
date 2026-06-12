"""Reverse-lookup: which ETFs hold a given stock / industry."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import EtfHolding, StockIndustry
from app.services.exposure_service import _industry_level_attr
from app.utils.finance_math import normalize_weights_to_fraction


def find_etfs_by_stock(
    session: Session,
    stock_symbol: str,
    holding_date: dt.date | None = None,
) -> list[dict]:
    """Find ETFs holding ``stock_symbol``, with weight, sorted desc.

    If ``holding_date`` is None, uses the latest holding_date available for
    each individual ETF (which may differ across ETFs).
    """
    # All (etf_symbol, holding_date) rows for this stock.
    query = session.query(EtfHolding).filter(EtfHolding.asset_symbol == stock_symbol)
    if holding_date is not None:
        query = query.filter(EtfHolding.holding_date == holding_date)
    rows = query.all()
    if not rows:
        return []

    if holding_date is None:
        # Determine latest holding_date per ETF (across all holdings, not
        # just rows containing this stock), then keep only matching rows.
        latest_by_etf = dict(
            session.query(EtfHolding.etf_symbol, func.max(EtfHolding.holding_date))
            .filter(EtfHolding.etf_symbol.in_({r.etf_symbol for r in rows}))
            .group_by(EtfHolding.etf_symbol)
            .all()
        )
        rows = [r for r in rows if r.holding_date == latest_by_etf.get(r.etf_symbol)]

    if not rows:
        return []

    # Normalize weights per (etf_symbol, holding_date) group.
    groups: dict[tuple[str, dt.date], list[EtfHolding]] = {}
    for r in rows:
        all_rows = (
            session.query(EtfHolding)
            .filter(
                EtfHolding.etf_symbol == r.etf_symbol,
                EtfHolding.holding_date == r.holding_date,
            )
            .all()
        )
        groups[(r.etf_symbol, r.holding_date)] = all_rows

    results: list[dict] = []
    for r in rows:
        group = groups[(r.etf_symbol, r.holding_date)]
        raw_weights = [float(x.weight) if x.weight is not None else 0.0 for x in group]
        fractions = normalize_weights_to_fraction(raw_weights)
        idx = group.index(r)
        frac = fractions[idx]
        results.append(
            {
                "etf_symbol": r.etf_symbol,
                "holding_date": r.holding_date,
                "asset_symbol": r.asset_symbol,
                "asset_name": r.asset_name,
                "weight_fraction": frac,
                "weight_pct": frac * 100,
            }
        )

    results.sort(key=lambda x: x["weight_fraction"], reverse=True)
    return results


def find_etfs_by_industry(
    session: Session,
    industry: str,
    level: int = 1,
    holding_date: dt.date | None = None,
) -> list[dict]:
    """Rank ETFs by their total exposure (fraction of holdings) to ``industry``.

    If ``holding_date`` is None, each ETF is evaluated as of its own latest
    holding_date.
    """
    industry_attr = _industry_level_attr(level)

    # Stocks belonging to this industry at the given level.
    stock_symbols = {
        s
        for (s,) in session.query(StockIndustry.stock_symbol)
        .filter(industry_attr == industry)
        .all()
    }
    if not stock_symbols:
        return []

    # Determine relevant (etf_symbol, holding_date) pairs.
    if holding_date is not None:
        etf_dates = {
            etf_symbol: holding_date
            for (etf_symbol,) in session.query(EtfHolding.etf_symbol)
            .filter(EtfHolding.holding_date == holding_date)
            .distinct()
            .all()
        }
    else:
        etf_dates = dict(
            session.query(EtfHolding.etf_symbol, func.max(EtfHolding.holding_date))
            .group_by(EtfHolding.etf_symbol)
            .all()
        )

    results: list[dict] = []
    for etf_symbol, h_date in etf_dates.items():
        rows = (
            session.query(EtfHolding)
            .filter(
                EtfHolding.etf_symbol == etf_symbol,
                EtfHolding.holding_date == h_date,
            )
            .all()
        )
        if not rows:
            continue
        raw_weights = [float(r.weight) if r.weight is not None else 0.0 for r in rows]
        fractions = normalize_weights_to_fraction(raw_weights)

        exposure = sum(
            frac
            for r, frac in zip(rows, fractions)
            if r.asset_symbol in stock_symbols
        )
        if exposure <= 0:
            continue

        results.append(
            {
                "etf_symbol": etf_symbol,
                "holding_date": h_date,
                "industry": industry,
                "level": level,
                "weight_fraction": exposure,
                "weight_pct": exposure * 100,
            }
        )

    results.sort(key=lambda x: x["weight_fraction"], reverse=True)
    return results
