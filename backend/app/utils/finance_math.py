"""Pure numeric helpers for concentration/exposure math.

No DB access here — keep these functions easy to unit-test in isolation.
"""

from __future__ import annotations

import pandas as pd


def normalize_weights_to_fraction(weights: list[float]) -> list[float]:
    """Normalize a list of weights to fractions (0-1).

    Mirrors the scale-detection logic in
    ``app.utils.data_quality.check_holding_weight_sum``: if the sum of the
    provided weights is <= 1.5, they are assumed to already be fractions
    (e.g. 0.195 == 19.5%). Otherwise they are assumed to be percentages
    (e.g. 19.5 == 19.5%) and are divided by 100.

    Empty input returns an empty list. ``None`` values are treated as 0.
    """
    if not weights:
        return []

    cleaned = [float(w) if w is not None else 0.0 for w in weights]
    total = sum(cleaned)

    if total <= 1.5:
        return cleaned

    return [w / 100.0 for w in cleaned]


def hhi(weights_fraction: list[float]) -> float:
    """Herfindahl-Hirschman Index = sum(w^2), weights as fractions (0-1)."""
    if not weights_fraction:
        return 0.0
    return sum(w * w for w in weights_fraction)


def effective_holdings(hhi_value: float) -> float | None:
    """Effective number of holdings = 1 / HHI.

    Returns ``None`` if ``hhi_value`` is 0 (undefined / no holdings).
    """
    if not hhi_value:
        return None
    return 1.0 / hhi_value


def top_n_weight(sorted_weights: list[float], n: int) -> float:
    """Sum of the top ``n`` weights from a list already sorted descending.

    If ``n`` exceeds the length of the list, sums all available weights.
    """
    if not sorted_weights or n <= 0:
        return 0.0
    return round(sum(sorted_weights[:n]), 12)


# ---------------------------------------------------------------------------
# Backtest metric helpers (Phase 7)
# ---------------------------------------------------------------------------


def cagr(final_value: float, basis: float, years: float) -> float:
    """Compound annual growth rate.

    ``CAGR = (final_value / basis) ^ (1 / years) - 1``

    Returns 0.0 if ``basis`` <= 0 or ``years`` <= 0 (undefined / degenerate).
    Negative ``final_value`` (not normally possible for a portfolio) is
    clamped to 0 before the power operation to avoid complex results.
    """
    if basis is None or basis <= 0 or years is None or years <= 0:
        return 0.0
    ratio = max(final_value, 0.0) / basis
    return ratio ** (1.0 / years) - 1.0


def max_drawdown(values: list[float]) -> float:
    """Maximum drawdown of a value series.

    ``running_max = cumulative_max(values)``
    ``drawdown = values / running_max - 1``
    ``max_drawdown = min(drawdown)`` (a value <= 0).

    Returns 0.0 for empty input.
    """
    if values is None or len(values) == 0:
        return 0.0

    series = pd.Series(values, dtype="float64")
    running_max = series.cummax()
    drawdown = series / running_max - 1.0
    return float(drawdown.min())


def annualized_volatility(values: list[float]) -> float:
    """Annualized volatility from a value series.

    ``daily_returns = pct_change(values)``
    ``annualized_volatility = std(daily_returns, ddof=1) * sqrt(252)``

    Returns 0.0 if fewer than 2 returns are available (e.g. <= 2 values),
    or if the standard deviation is NaN (e.g. all returns identical and
    only one observation).
    """
    if values is None or len(values) < 2:
        return 0.0

    series = pd.Series(values, dtype="float64")
    daily_returns = series.pct_change().dropna()
    if len(daily_returns) < 2:
        return 0.0

    std = daily_returns.std(ddof=1)
    if pd.isna(std):
        return 0.0
    return float(std * (252 ** 0.5))


def sharpe_ratio(
    annualized_return: float, volatility: float, risk_free_rate: float = 0.0
) -> float:
    """Sharpe ratio = (annualized_return - risk_free_rate) / volatility.

    Returns 0.0 if ``volatility`` is 0 (undefined / no variability).
    """
    if volatility is None or volatility == 0:
        return 0.0
    return (annualized_return - risk_free_rate) / volatility


def xirr(cashflows: list[tuple], guess: float = 0.1) -> float:
    """Annualized internal rate of return for irregularly-dated cashflows.

    ``cashflows`` is a list of ``(date, amount)`` tuples. ``date`` must be a
    ``datetime.date`` (or ``datetime``) and ``amount`` a float (negative =
    outflow / contribution, positive = inflow / value received).

    Uses Newton's method with a bisection fallback for robustness. Returns
    0.0 if the input is degenerate (fewer than 2 cashflows, or all amounts
    have the same sign — no sign change means no finite IRR exists).
    """
    if not cashflows or len(cashflows) < 2:
        return 0.0

    sorted_flows = sorted(cashflows, key=lambda cf: cf[0])
    t0 = sorted_flows[0][0]

    amounts = [amt for _, amt in sorted_flows]
    if not (min(amounts) < 0 < max(amounts)):
        # No sign change -> IRR undefined.
        return 0.0

    def years_from_t0(d) -> float:
        return (d - t0).days / 365.25

    times = [years_from_t0(d) for d, _ in sorted_flows]

    def npv(rate: float) -> float:
        if rate <= -1.0:
            rate = -1.0 + 1e-9
        return sum(amt / (1.0 + rate) ** t for t, amt in zip(times, amounts))

    def dnpv(rate: float) -> float:
        if rate <= -1.0:
            rate = -1.0 + 1e-9
        return sum(
            -t * amt / (1.0 + rate) ** (t + 1) for t, amt in zip(times, amounts)
        )

    rate = guess
    for _ in range(100):
        f = npv(rate)
        df = dnpv(rate)
        if df == 0:
            break
        new_rate = rate - f / df
        if new_rate <= -1.0:
            new_rate = (rate + -0.999999999) / 2
        if abs(new_rate - rate) < 1e-9:
            rate = new_rate
            break
        rate = new_rate
    else:
        rate = None

    if rate is not None and abs(npv(rate)) < 1e-6 and rate > -1.0:
        return float(rate)

    # Bisection fallback over a wide range.
    lo, hi = -0.999999, 10.0
    f_lo, f_hi = npv(lo), npv(hi)
    if f_lo * f_hi > 0:
        # Expand hi until sign change or give up.
        while hi < 1e6 and f_lo * f_hi > 0:
            hi *= 10
            f_hi = npv(hi)
        if f_lo * f_hi > 0:
            return 0.0

    for _ in range(200):
        mid = (lo + hi) / 2
        f_mid = npv(mid)
        if abs(f_mid) < 1e-8:
            return float(mid)
        if f_lo * f_mid < 0:
            hi = mid
            f_hi = f_mid
        else:
            lo = mid
            f_lo = f_mid

    return float((lo + hi) / 2)
