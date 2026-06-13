"""Concentration metrics for a single ETF's holdings."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import EtfHolding
from app.utils.finance_math import (
    effective_holdings,
    hhi,
    normalize_weights_to_fraction,
    top_n_weight,
)


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


def _load_holdings(
    session: Session, etf_symbol: str, holding_date: dt.date
) -> list[EtfHolding]:
    return (
        session.query(EtfHolding)
        .filter(
            EtfHolding.etf_symbol == etf_symbol,
            EtfHolding.holding_date == holding_date,
        )
        .all()
    )


def get_top_holdings(
    session: Session,
    etf_symbol: str,
    holding_date: dt.date | None = None,
    n: int = 10,
) -> list[dict]:
    """Return the top ``n`` holdings of ``etf_symbol`` by weight, descending.

    Each item: {asset_symbol, asset_name, weight_fraction, weight_pct}.
    """
    resolved_date = _resolve_holding_date(session, etf_symbol, holding_date)
    if resolved_date is None:
        return []

    rows = _load_holdings(session, etf_symbol, resolved_date)
    if not rows:
        return []

    raw_weights = [float(r.weight) if r.weight is not None else 0.0 for r in rows]
    fractions = normalize_weights_to_fraction(raw_weights)

    items = [
        {
            "asset_symbol": r.asset_symbol,
            "asset_name": r.asset_name,
            "weight_fraction": frac,
            "weight_pct": frac * 100,
        }
        for r, frac in zip(rows, fractions)
    ]

    items.sort(key=lambda x: x["weight_fraction"], reverse=True)
    return items[:n]


def get_concentration(
    session: Session,
    etf_symbol: str,
    holding_date: dt.date | None = None,
) -> dict:
    """Return concentration summary for ``etf_symbol``.

    {
      holding_date, num_holdings,
      top1, top3, top5, top10 (fraction + pct),
      hhi, effective_holdings,
    }
    """
    resolved_date = _resolve_holding_date(session, etf_symbol, holding_date)
    if resolved_date is None:
        return {
            "etf_symbol": etf_symbol,
            "holding_date": None,
            "num_holdings": 0,
            "top1_fraction": None,
            "top1_pct": None,
            "top3_fraction": None,
            "top3_pct": None,
            "top5_fraction": None,
            "top5_pct": None,
            "top10_fraction": None,
            "top10_pct": None,
            "hhi": None,
            "effective_holdings": None,
        }

    rows = _load_holdings(session, etf_symbol, resolved_date)
    raw_weights = [float(r.weight) if r.weight is not None else 0.0 for r in rows]
    fractions = normalize_weights_to_fraction(raw_weights)
    sorted_fractions = sorted(fractions, reverse=True)

    hhi_value = hhi(sorted_fractions)

    result = {
        "etf_symbol": etf_symbol,
        "holding_date": resolved_date,
        "num_holdings": len(rows),
        "hhi": hhi_value,
        "effective_holdings": effective_holdings(hhi_value),
    }

    for n in (1, 3, 5, 10):
        frac = top_n_weight(sorted_fractions, n)
        result[f"top{n}_fraction"] = frac
        result[f"top{n}_pct"] = frac * 100

    return result
