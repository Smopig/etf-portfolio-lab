"""填息天數 (days-to-recover after each dividend) — CLAUDE.md §7.

For each paid (past) dividend ex-date, computes how many trading days it took
for the close price to first return to >= the pre-ex close (the close on the
trading day immediately BEFORE the ex-date). Uses only stored EtfPrice +
EtfDividend rows — never fabricates. Dividends not yet recovered as of the
latest available price are reported with ``recovered=False`` / ``days=None``.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from app.models import EtfDividend, EtfPrice

_DEFAULT_LIMIT = 12


def get_dividend_recovery(
    db: Session,
    etf_symbol: str,
    limit: int = _DEFAULT_LIMIT,
) -> list[dict]:
    """Return 填息 rows for the most recent ~``limit`` paid dividends.

    Each row::

        {
          "ex_date": date,
          "dividend_amount": float | None,
          "pre_ex_close": float | None,
          "recovered": bool,
          "days_to_recover": int | None,   # trading days, None if not recovered
          "recovered_date": date | None,
        }

    "填息天數" = number of trading days from the ex-date (exclusive of the
    pre-ex day) until the first close >= pre_ex_close. A dividend with no
    pre-ex close (no price before the ex-date) is reported recovered=False.
    """
    today = dt.date.today()

    # Paid, past dividends only, newest first; cap to the requested window.
    dividends = (
        db.query(EtfDividend)
        .filter(EtfDividend.etf_symbol == etf_symbol)
        .filter(EtfDividend.ex_dividend_date <= today)
        .order_by(EtfDividend.ex_dividend_date.desc())
        .limit(limit)
        .all()
    )
    if not dividends:
        return []

    # Load the full ascending price series once (close per trade_date).
    price_rows = (
        db.query(EtfPrice.trade_date, EtfPrice.close)
        .filter(EtfPrice.etf_symbol == etf_symbol)
        .filter(EtfPrice.close.isnot(None))
        .order_by(EtfPrice.trade_date.asc())
        .all()
    )
    series = [(r.trade_date, float(r.close)) for r in price_rows]

    rows: list[dict] = []
    for div in dividends:
        rows.append(_recovery_for_dividend(div, series))
    return rows


def _recovery_for_dividend(div: EtfDividend, series: list[tuple[dt.date, float]]) -> dict:
    ex_date = div.ex_dividend_date
    amount = float(div.dividend_amount) if div.dividend_amount is not None else None

    # pre_ex_close = close on the last trading day strictly before ex_date.
    pre_ex_close: float | None = None
    for trade_date, close in series:
        if trade_date < ex_date:
            pre_ex_close = close
        else:
            break

    base = {
        "ex_date": ex_date,
        "dividend_amount": amount,
        "pre_ex_close": pre_ex_close,
        "recovered": False,
        "days_to_recover": None,
        "recovered_date": None,
    }
    if pre_ex_close is None:
        return base

    # Walk trading days on/after the ex-date; count them (ex-date = day 1).
    trading_day = 0
    for trade_date, close in series:
        if trade_date < ex_date:
            continue
        trading_day += 1
        if close >= pre_ex_close:
            base["recovered"] = True
            base["days_to_recover"] = trading_day
            base["recovered_date"] = trade_date
            break
    return base
