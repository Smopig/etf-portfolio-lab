"""Price history for a single ETF."""

from __future__ import annotations

import datetime as dt
from collections import Counter

from sqlalchemy.orm import Session

from app.models import EtfPrice


def get_price_history(
    session: Session,
    etf_symbol: str,
    start: dt.date | None = None,
    end: dt.date | None = None,
    limit: int = 500,
) -> dict:
    """Return price history for ``etf_symbol`` ordered by trade_date ascending.

    {
      symbol, currency, source_name, data_start, data_end,
      points: [{date, open, high, low, close, adjusted_close, volume}, ...]
    }
    """
    query = session.query(EtfPrice).filter(EtfPrice.etf_symbol == etf_symbol)
    if start is not None:
        query = query.filter(EtfPrice.trade_date >= start)
    if end is not None:
        query = query.filter(EtfPrice.trade_date <= end)

    rows = query.order_by(EtfPrice.trade_date.asc()).limit(limit).all()

    if not rows:
        return {
            "symbol": etf_symbol,
            "currency": "TWD",
            "source_name": None,
            "data_start": None,
            "data_end": None,
            "points": [],
        }

    source_counts = Counter(r.source_name for r in rows if r.source_name)
    most_common_source = source_counts.most_common(1)[0][0] if source_counts else None

    points = [
        {
            "date": r.trade_date.isoformat(),
            "open": float(r.open) if r.open is not None else None,
            "high": float(r.high) if r.high is not None else None,
            "low": float(r.low) if r.low is not None else None,
            "close": float(r.close) if r.close is not None else None,
            "adjusted_close": float(r.adjusted_close) if r.adjusted_close is not None else None,
            "volume": float(r.volume) if r.volume is not None else None,
        }
        for r in rows
    ]

    return {
        "symbol": etf_symbol,
        "currency": "TWD",
        "source_name": most_common_source,
        "data_start": rows[0].trade_date.isoformat(),
        "data_end": rows[-1].trade_date.isoformat(),
        "points": points,
    }
