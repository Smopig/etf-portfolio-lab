"""Price history for a single ETF."""

from __future__ import annotations

import datetime as dt
from collections import Counter

from sqlalchemy import func
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

    # Take the MOST RECENT ``limit`` rows (order desc + limit), then present
    # them ascending. Ordering asc before limit would truncate the recent end
    # and silently drop the latest data when a symbol has more rows than limit.
    rows = query.order_by(EtfPrice.trade_date.desc()).limit(limit).all()
    rows.reverse()

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


def get_price_ranges(session: Session, symbols: list[str]) -> dict:
    """Return per-symbol min/max trade_date and the common overlapping window.

    {
      "per_symbol": {sym: {"start": iso|null, "end": iso|null}},
      "common_start": iso|null,
      "common_end": iso|null,
    }

    common_start = max of per-symbol starts (latest start), common_end = min
    of per-symbol ends (earliest end), considering only symbols that have
    data. If no symbol has data, both are null.
    """
    rows = (
        session.query(
            EtfPrice.etf_symbol,
            func.min(EtfPrice.trade_date),
            func.max(EtfPrice.trade_date),
        )
        .filter(EtfPrice.etf_symbol.in_(symbols))
        .group_by(EtfPrice.etf_symbol)
        .all()
    )

    ranges_by_symbol = {sym: (start, end) for sym, start, end in rows}

    per_symbol: dict[str, dict] = {}
    starts: list[dt.date] = []
    ends: list[dt.date] = []
    for sym in symbols:
        rng = ranges_by_symbol.get(sym)
        if rng is None:
            per_symbol[sym] = {"start": None, "end": None}
            continue
        start, end = rng
        per_symbol[sym] = {
            "start": start.isoformat() if start is not None else None,
            "end": end.isoformat() if end is not None else None,
        }
        if start is not None:
            starts.append(start)
        if end is not None:
            ends.append(end)

    common_start = max(starts).isoformat() if starts else None
    common_end = min(ends).isoformat() if ends else None

    return {
        "per_symbol": per_symbol,
        "common_start": common_start,
        "common_end": common_end,
    }


def get_latest_prices(session: Session, symbols: list[str] | None = None) -> dict[str, dict]:
    """Return the latest close and previous close per ETF symbol in one query.

    {
      symbol: {"date", "close", "prev_close", "change", "change_pct"}
    }

    change_pct = (close - prev_close) / prev_close * 100, or None if there is
    no previous close.
    """
    row_number = (
        func.row_number()
        .over(
            partition_by=EtfPrice.etf_symbol,
            order_by=EtfPrice.trade_date.desc(),
        )
        .label("rn")
    )

    subq = session.query(
        EtfPrice.etf_symbol.label("etf_symbol"),
        EtfPrice.trade_date.label("trade_date"),
        EtfPrice.close.label("close"),
        row_number,
    )
    if symbols is not None:
        subq = subq.filter(EtfPrice.etf_symbol.in_(symbols))
    subq = subq.subquery()

    rows = (
        session.query(
            subq.c.etf_symbol,
            subq.c.trade_date,
            subq.c.close,
            subq.c.rn,
        )
        .filter(subq.c.rn.in_((1, 2)))
        .all()
    )

    by_symbol: dict[str, dict] = {}
    for r in rows:
        entry = by_symbol.setdefault(
            r.etf_symbol, {"date": None, "close": None, "prev_close": None}
        )
        if r.rn == 1:
            entry["date"] = r.trade_date.isoformat() if r.trade_date is not None else None
            entry["close"] = float(r.close) if r.close is not None else None
        else:
            entry["prev_close"] = float(r.close) if r.close is not None else None

    result: dict[str, dict] = {}
    for symbol, entry in by_symbol.items():
        close = entry["close"]
        prev_close = entry["prev_close"]
        change = None
        change_pct = None
        if close is not None and prev_close is not None and prev_close != 0:
            change = close - prev_close
            change_pct = change / prev_close * 100
        result[symbol] = {
            "date": entry["date"],
            "close": close,
            "prev_close": prev_close,
            "change": change,
            "change_pct": change_pct,
        }

    return result
