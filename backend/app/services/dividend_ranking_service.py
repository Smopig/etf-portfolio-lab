"""全 ETF 配息排行榜 (dividend ranking) read service (CLAUDE.md §7).

Yield is ALWAYS computed from a trailing-twelve-month (TTM) sum of actually
paid distributions divided by the latest close. It is NEVER inflated by
multiplying a single distribution by the payout frequency. Upcoming /
unpaid distributions are excluded from the TTM sum. Every row surfaces its
source name and the relevant data dates so the disclosure rules in §7 hold.
"""

from __future__ import annotations

import datetime as dt
import statistics

from sqlalchemy.orm import Session

from app.models import EtfDividend, EtfDividendFrequencyOverride, EtfMaster
from app.services.price_service import get_latest_prices

VALID_FREQUENCIES = ("月配", "季配", "半年配", "年配")

_PERIOD_PREFIX_TO_FREQ = {
    "M": "月配",
    "Q": "季配",
    "H": "半年配",
    "Y": "年配",
}


def _frequency_from_spacing(ex_dates: list[dt.date]) -> str | None:
    """Infer frequency from the median spacing of recent ex-dividend dates."""
    dates = sorted({d for d in ex_dates if isinstance(d, dt.date)})
    if len(dates) < 2:
        return None
    gaps = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
    gaps = [g for g in gaps if g > 0]
    if not gaps:
        return None
    median_gap = statistics.median(gaps)
    if median_gap <= 45:
        return "月配"
    if median_gap <= 135:
        return "季配"
    if median_gap <= 270:
        return "半年配"
    return "年配"


def classify_frequency(records: list) -> str:
    """Classify 配息週期 from a list of dividend records (dicts or ORM rows).

    Uses the ``period`` token prefix of the most recent ~3 rows; falls back to
    median ex-date spacing when periods are blank/missing. Returns "年配" as a
    last resort when nothing can be inferred (still a real default, not data).
    """

    def _get(rec, attr):
        if isinstance(rec, dict):
            return rec.get(attr)
        return getattr(rec, attr, None)

    dated = [
        (
            _get(r, "ex_dividend_date"),
            _get(r, "period"),
        )
        for r in records
        if _get(r, "ex_dividend_date") is not None
    ]
    dated.sort(key=lambda x: x[0], reverse=True)

    recent_periods = [p for (_d, p) in dated[:3] if p]
    for period in recent_periods:
        prefix = str(period).strip()[:1].upper()
        freq = _PERIOD_PREFIX_TO_FREQ.get(prefix)
        if freq:
            return freq

    spacing_freq = _frequency_from_spacing([d for (d, _p) in dated])
    if spacing_freq:
        return spacing_freq

    return "年配"


def classify_frequency_for_symbol(session: Session, etf_symbol: str) -> str | None:
    """Classify frequency from an ETF's stored dividend history, or None."""
    rows = (
        session.query(EtfDividend)
        .filter(EtfDividend.etf_symbol == etf_symbol)
        .all()
    )
    if not rows:
        return None
    return classify_frequency(rows)


def get_dividend_ranking(
    session: Session,
    *,
    order: str = "desc",
    frequency: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Return the dividend ranking across all ETFs that have dividend rows.

    Each row:
      etf_symbol, name, ttm_dividend, latest_close, ttm_yield_pct (TTM only),
      latest_dividend, latest_ex_date, frequency, payout_per_100k,
      source_name, price_date.

    Sorting is by ``ttm_yield_pct`` (rows without a yield sort last). ``limit``
    is applied only when given (default = ALL — no Top-10 cap).
    """
    today = dt.date.today()
    window_start = today - dt.timedelta(days=365)

    div_rows = session.query(EtfDividend).all()
    by_symbol: dict[str, list[EtfDividend]] = {}
    for r in div_rows:
        by_symbol.setdefault(r.etf_symbol, []).append(r)

    if not by_symbol:
        return []

    symbols = list(by_symbol.keys())
    latest_prices = get_latest_prices(session, symbols=symbols)

    names = {
        s: n
        for (s, n) in session.query(EtfMaster.symbol, EtfMaster.name)
        .filter(EtfMaster.symbol.in_(symbols))
        .all()
    }
    masters_freq = {
        s: f
        for (s, f) in session.query(EtfMaster.symbol, EtfMaster.dividend_frequency)
        .filter(EtfMaster.symbol.in_(symbols))
        .all()
    }
    overrides = {
        o.etf_symbol: o.frequency
        for o in session.query(EtfDividendFrequencyOverride)
        .filter(EtfDividendFrequencyOverride.etf_symbol.in_(symbols))
        .all()
    }

    results: list[dict] = []
    for symbol, rows in by_symbol.items():
        # The DB has no `is_upcoming` column; the refresh phase never persists
        # upcoming distributions. Defensively we also exclude any row whose
        # ex-date is in the future or whose payment_date hasn't arrived yet.
        ttm_dividend = 0.0
        for r in rows:
            amount = float(r.dividend_amount) if r.dividend_amount is not None else 0.0
            ex_date = r.ex_dividend_date
            if ex_date is None or ex_date < window_start or ex_date > today:
                continue
            if r.payment_date is not None and r.payment_date > today:
                continue  # not yet paid
            ttm_dividend += amount

        price_entry = latest_prices.get(symbol, {})
        latest_close = price_entry.get("close")
        price_date = price_entry.get("date")

        ttm_yield_pct = None
        payout_per_100k = None
        if latest_close is not None and latest_close > 0:
            ttm_yield_pct = ttm_dividend / latest_close * 100
            payout_per_100k = round(ttm_yield_pct / 100 * 100000)

        # Latest paid distribution (most recent ex-date not in the future).
        paid_rows = [
            r
            for r in rows
            if r.ex_dividend_date is not None and r.ex_dividend_date <= today
            and (r.payment_date is None or r.payment_date <= today)
        ]
        paid_rows.sort(key=lambda r: r.ex_dividend_date, reverse=True)
        latest_dividend = None
        latest_ex_date = None
        if paid_rows:
            latest = paid_rows[0]
            latest_dividend = (
                float(latest.dividend_amount)
                if latest.dividend_amount is not None
                else None
            )
            latest_ex_date = latest.ex_dividend_date

        # Frequency resolution: override > master > classify-from-history.
        freq = overrides.get(symbol) or masters_freq.get(symbol)
        if not freq:
            freq = classify_frequency(rows)

        source_name = next(
            (r.source_name for r in rows if r.source_name), None
        )

        results.append(
            {
                "etf_symbol": symbol,
                "name": names.get(symbol),
                "ttm_dividend": round(ttm_dividend, 4),
                "latest_close": latest_close,
                "ttm_yield_pct": ttm_yield_pct,
                "latest_dividend": latest_dividend,
                "latest_ex_date": latest_ex_date,
                "frequency": freq,
                "payout_per_100k": payout_per_100k,
                "source_name": source_name,
                "price_date": price_date,
            }
        )

    if frequency is not None:
        results = [r for r in results if r["frequency"] == frequency]

    reverse = order != "asc"
    # Rows without a yield always sort to the bottom regardless of order.
    results.sort(
        key=lambda r: (
            r["ttm_yield_pct"] is None,
            -(r["ttm_yield_pct"] or 0.0) if reverse else (r["ttm_yield_pct"] or 0.0),
        )
    )

    if limit is not None:
        results = results[:limit]

    return results
