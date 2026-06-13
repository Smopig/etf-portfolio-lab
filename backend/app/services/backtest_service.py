"""Backtesting engine (Phase 7).

Architecture:

- The engine core (``run_backtest``) is PURE Python/pandas/numpy: it takes
  in-memory price series, dividend events, target weights and a config, and
  returns a result. It performs NO database access and does NOT touch
  ``BacktestRun`` / JSONB, so it is fully unit-testable on synthetic data
  with no Postgres dependency.
- ``load_prices_from_db`` / ``load_dividends_from_db`` are a thin DB-loading
  layer that queries ``EtfPrice`` / ``EtfDividend``.
- ``run_backtest_from_db`` wires the two together and, when ``persist=True``,
  writes a ``BacktestRun`` row (including ``result_json``, which is JSONB —
  only this persistence layer touches it).

Modeling simplifications (documented per CLAUDE.md §7 and the task spec):

1. Date alignment: multiple ETFs are aligned via an INNER JOIN on common
   trading dates (the intersection of all symbols' date indices). Dates
   where any symbol is missing a price are dropped entirely. This avoids
   forward-filling stale prices across exchange holidays that differ by
   market, at the cost of potentially shortening the effective date range
   for the metrics.
2. Price field: ``adjusted_close`` is used when present (non-null), else
   ``close``, on a per-row basis.
3. Dividend reinvestment date: dividends are reinvested on ``payment_date``
   if present, else fall back to ``ex_dividend_date``. This is an MVP
   simplification — in reality cash is typically received some days after
   the ex-dividend date, and ``payment_date`` is the closer proxy. If
   neither date falls on/after a trading day in the aligned index, the
   dividend is applied on the next available trading day on/after that
   date; dividends whose date is after the last trading day are ignored.
4. Reinvestment mechanics: on the dividend date, cash = sum over assets of
   (dividend_amount_per_share * shares_held_in_that_asset). This cash is
   then used to buy back ALL assets according to the *target* weights
   (not the asset that paid the dividend) — i.e. dividends contribute to
   the overall portfolio cash pool and are redeployed per target
   allocation. This is a simplifying MVP choice; a more granular model
   would reinvest into the paying asset only.
5. Monthly contributions: a fixed ``monthly_contribution`` amount is added
   as cash on the first trading day on/after each calendar month boundary
   following the start date (the start date itself does not get an extra
   contribution — the ``initial_amount`` covers month 0). The added cash is
   immediately invested per target weights (if rebalancing is due on the
   same day, contribution cash is added first, then the rebalance/buy logic
   runs against the combined cash pool).
6. Rebalancing: on the first trading day of each rebalance period (per
   ``rebalance_frequency``), the FULL portfolio value (holdings + cash) is
   redistributed to match target weights exactly. The notional traded
   (sum of absolute value changes per asset) is subject to
   ``transaction_cost_rate``, which is deducted from the portfolio's cash
   /total value at that point. ``rebalance_frequency="none"`` means the
   portfolio is bought once at the start (and whenever new cash arrives via
   contributions/dividends, which is invested per target weights — this is
   NOT considered a "rebalance" of existing holdings, just deployment of new
   cash) and never rebalanced thereafter.
7. Fractional shares are assumed (no rounding to whole shares). This is
   standard for ETF backtesting MVPs and avoids large discretization error
   for small contribution amounts.
8. CAGR vs IRR: ``cagr`` is computed using the simple formula
   ``(final_value / total_contribution) ** (1/years) - 1``. For DCA
   (monthly_contribution > 0) this formula treats all contributions as if
   made at time 0, which is misleading — it will understate returns for a
   growing portfolio. For DCA we therefore ALSO compute ``irr`` (annualized,
   money-weighted, via ``xirr`` on the contribution cashflows + final
   value), which is the more meaningful metric. Both are returned; callers
   should prefer ``irr`` when ``monthly_contribution > 0``.
9. Volatility / Sharpe are computed from the DAILY portfolio value series
   (including cashflow days), per the spec formulas. Cash inflows
   (contributions/dividends) cause artificial positive "returns" on those
   days; this is a known limitation of value-based (vs. return-based)
   volatility for DCA portfolios, consistent with the spec's stated
   formulas (section 9-10).
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field

import pandas as pd

from app.utils.finance_math import (
    annualized_volatility as _annualized_volatility,
)
from app.utils.finance_math import cagr as _cagr
from app.utils.finance_math import max_drawdown as _max_drawdown
from app.utils.finance_math import normalize_weights_to_fraction
from app.utils.finance_math import sharpe_ratio as _sharpe_ratio
from app.utils.finance_math import xirr as _xirr

DISCLAIMER = "回測結果不代表未來績效，僅供研究分析。"

VALID_REBALANCE_FREQUENCIES = {
    "none",
    "monthly",
    "quarterly",
    "semiannual",
    "annual",
}


@dataclass
class BacktestConfig:
    """Inputs for ``run_backtest``. Weights may be fractions or percentages;
    they are normalized via ``normalize_weights_to_fraction``."""

    start_date: _dt.date
    end_date: _dt.date
    weights: dict[str, float]
    initial_amount: float
    monthly_contribution: float = 0.0
    dividend_reinvest: bool = True
    rebalance_frequency: str = "none"
    transaction_cost_rate: float = 0.0
    risk_free_rate: float = 0.0

    def __post_init__(self) -> None:
        if self.rebalance_frequency not in VALID_REBALANCE_FREQUENCIES:
            raise ValueError(
                f"Invalid rebalance_frequency: {self.rebalance_frequency!r}. "
                f"Must be one of {sorted(VALID_REBALANCE_FREQUENCIES)}."
            )
        if not self.weights:
            raise ValueError("weights must not be empty")

        symbols = list(self.weights.keys())
        fractions = normalize_weights_to_fraction(list(self.weights.values()))
        self.weights = dict(zip(symbols, fractions))


@dataclass
class BacktestResult:
    final_value: float
    total_contribution: float
    total_profit: float
    cagr: float
    irr: float | None
    max_drawdown: float
    annualized_volatility: float
    sharpe_ratio: float
    annual_returns: dict[str, float]
    portfolio_value_series: list[tuple[_dt.date, float]]
    drawdown_series: list[tuple[_dt.date, float]]
    disclaimer: str = DISCLAIMER

    def to_dict(self) -> dict:
        return {
            "final_value": self.final_value,
            "total_contribution": self.total_contribution,
            "total_profit": self.total_profit,
            "cagr": self.cagr,
            "irr": self.irr,
            "max_drawdown": self.max_drawdown,
            "annualized_volatility": self.annualized_volatility,
            "sharpe_ratio": self.sharpe_ratio,
            "annual_returns": self.annual_returns,
            "portfolio_value_series": [
                {"date": d.isoformat(), "value": v}
                for d, v in self.portfolio_value_series
            ],
            "drawdown_series": [
                {"date": d.isoformat(), "drawdown": v}
                for d, v in self.drawdown_series
            ],
            "disclaimer": self.disclaimer,
        }


# ---------------------------------------------------------------------------
# Rebalance period helpers
# ---------------------------------------------------------------------------


def _period_key(d: _dt.date, frequency: str) -> tuple | None:
    """Return a key identifying the rebalance "period" containing ``d``.

    Two dates with the same key are in the same rebalance period. Returns
    ``None`` for frequency == "none" (no periodic rebalancing).
    """
    if frequency == "none":
        return None
    if frequency == "monthly":
        return (d.year, d.month)
    if frequency == "quarterly":
        return (d.year, (d.month - 1) // 3)
    if frequency == "semiannual":
        return (d.year, (d.month - 1) // 6)
    if frequency == "annual":
        return (d.year,)
    raise ValueError(f"Unknown frequency: {frequency}")


def _month_key(d: _dt.date) -> tuple:
    return (d.year, d.month)


# ---------------------------------------------------------------------------
# Pure engine
# ---------------------------------------------------------------------------


def run_backtest(
    prices: dict[str, pd.Series],
    dividends: dict[str, list[tuple[_dt.date, float]]],
    config: BacktestConfig,
) -> BacktestResult:
    """Run a portfolio backtest on in-memory price/dividend data.

    Parameters
    ----------
    prices:
        Mapping of symbol -> pandas Series indexed by ``date`` (or
        ``Timestamp``), values = adjusted close (or close) prices. Each
        series should already be limited to dates within
        ``[config.start_date, config.end_date]`` (extra dates are ignored
        via re-filtering, but it's cleaner for the caller to pre-trim).
    dividends:
        Mapping of symbol -> list of ``(date, dividend_amount_per_share)``
        tuples. ``date`` should be the reinvestment date (payment_date with
        ex_dividend_date fallback — see module docstring).
    config:
        Backtest configuration (weights, contributions, rebalancing, etc).

    Returns
    -------
    BacktestResult
    """
    symbols = list(config.weights.keys())
    if not symbols:
        raise ValueError("config.weights must not be empty")

    missing = [s for s in symbols if s not in prices or prices[s].empty]
    if missing:
        raise ValueError(f"No price data for symbols: {missing}")

    # --- Align on common dates (inner join), within [start, end] ----------
    normalized: dict[str, pd.Series] = {}
    for sym in symbols:
        s = prices[sym].copy()
        s.index = pd.to_datetime(s.index).normalize()
        s = s.sort_index()
        s = s[
            (s.index >= pd.Timestamp(config.start_date))
            & (s.index <= pd.Timestamp(config.end_date))
        ]
        normalized[sym] = s

    common_index = normalized[symbols[0]].index
    for sym in symbols[1:]:
        common_index = common_index.intersection(normalized[sym].index)
    common_index = common_index.sort_values()

    if len(common_index) == 0:
        raise ValueError(
            "No common trading dates across symbols in the requested range"
        )

    price_df = pd.DataFrame(
        {sym: normalized[sym].reindex(common_index) for sym in symbols}
    )
    dates: list[_dt.date] = [ts.date() for ts in common_index]

    # --- Prepare dividend lookup: date -> {symbol: amount_per_share} ------
    div_by_date: dict[_dt.date, dict[str, float]] = {}
    for sym in symbols:
        for ev_date, amount in dividends.get(sym, []):
            if amount is None or amount == 0:
                continue
            ev_ts = pd.Timestamp(ev_date).normalize()
            # snap to next available trading day on/after ev_date
            candidates = common_index[common_index >= ev_ts]
            if len(candidates) == 0:
                continue  # dividend date is after the last trading day
            target_date = candidates[0].date()
            div_by_date.setdefault(target_date, {})
            div_by_date[target_date][sym] = (
                div_by_date[target_date].get(sym, 0.0) + float(amount)
            )

    # --- Simulation state ---------------------------------------------------
    shares: dict[str, float] = {sym: 0.0 for sym in symbols}
    cash: float = 0.0
    total_contribution: float = float(config.initial_amount)
    contribution_cashflows: list[tuple[_dt.date, float]] = [
        (dates[0], -float(config.initial_amount))
    ]

    transaction_cost_total: float = 0.0

    def portfolio_value(idx: int) -> float:
        row = price_df.iloc[idx]
        return cash + sum(shares[sym] * float(row[sym]) for sym in symbols)

    def invest_cash_per_target(idx: int) -> None:
        """Deploy all available cash into target weights at date idx's prices."""
        nonlocal cash
        if cash <= 0:
            return
        row = price_df.iloc[idx]
        for sym in symbols:
            alloc = cash * config.weights[sym]
            price = float(row[sym])
            if price > 0:
                shares[sym] += alloc / price
        cash = 0.0

    def rebalance_to_target(idx: int) -> None:
        """Rebalance full portfolio value to target weights, charging cost."""
        nonlocal cash, transaction_cost_total
        row = price_df.iloc[idx]
        current_values = {sym: shares[sym] * float(row[sym]) for sym in symbols}
        total_value = cash + sum(current_values.values())
        if total_value <= 0:
            return

        target_values = {sym: total_value * config.weights[sym] for sym in symbols}
        traded_notional = sum(
            abs(target_values[sym] - current_values[sym]) for sym in symbols
        )
        cost = traded_notional * config.transaction_cost_rate
        transaction_cost_total += cost
        total_value -= cost

        target_values = {sym: total_value * config.weights[sym] for sym in symbols}
        for sym in symbols:
            price = float(row[sym])
            shares[sym] = target_values[sym] / price if price > 0 else 0.0
        cash = 0.0

    # --- Day 0: invest initial amount ---------------------------------------
    cash = float(config.initial_amount)
    invest_cash_per_target(0)

    last_contribution_month: tuple | None = _month_key(dates[0])
    last_rebalance_period = _period_key(dates[0], config.rebalance_frequency)

    value_series: list[float] = [portfolio_value(0)]

    for idx in range(1, len(dates)):
        d = dates[idx]

        # 1. Monthly contribution: first trading day on/after each new month.
        if config.monthly_contribution and config.monthly_contribution > 0:
            mk = _month_key(d)
            if mk != last_contribution_month:
                cash += float(config.monthly_contribution)
                total_contribution += float(config.monthly_contribution)
                contribution_cashflows.append(
                    (d, -float(config.monthly_contribution))
                )
                last_contribution_month = mk

        # 2. Dividend reinvestment.
        if config.dividend_reinvest and d in div_by_date:
            div_cash = 0.0
            for sym, amount_per_share in div_by_date[d].items():
                div_cash += shares[sym] * amount_per_share
            cash += div_cash

        # 3. Rebalancing (periodic) — takes precedence: redistributes
        #    cash + holdings to target weights.
        period_key = _period_key(d, config.rebalance_frequency)
        if period_key is not None and period_key != last_rebalance_period:
            rebalance_to_target(idx)
            last_rebalance_period = period_key
        else:
            # No rebalance today: just deploy any new cash per target weights.
            invest_cash_per_target(idx)

        value_series.append(portfolio_value(idx))

    # --- Final value & cashflow for IRR -------------------------------------
    final_value = value_series[-1]
    total_profit = final_value - total_contribution

    years = (dates[-1] - dates[0]).days / 365.25
    cagr_value = _cagr(final_value, total_contribution, years)

    irr_value: float | None = None
    if config.monthly_contribution and config.monthly_contribution > 0:
        irr_cashflows = list(contribution_cashflows)
        irr_cashflows.append((dates[-1], final_value))
        irr_value = _xirr(irr_cashflows)

    mdd = _max_drawdown(value_series)
    vol = _annualized_volatility(value_series)
    sharpe = _sharpe_ratio(cagr_value, vol, config.risk_free_rate)

    # --- Annual returns (value at last trading day of each year) -----------
    value_by_date = pd.Series(value_series, index=pd.to_datetime(dates))
    yearly_last = value_by_date.groupby(value_by_date.index.year).last()
    yearly_first = value_by_date.groupby(value_by_date.index.year).first()
    annual_returns: dict[str, float] = {}
    years_sorted = sorted(yearly_last.index)
    for i, yr in enumerate(years_sorted):
        if i == 0:
            start_val = value_series[0]
        else:
            start_val = yearly_last.loc[years_sorted[i - 1]]
        end_val = yearly_last.loc[yr]
        if start_val > 0:
            annual_returns[str(yr)] = float(end_val / start_val - 1.0)
        else:
            annual_returns[str(yr)] = 0.0

    # --- Drawdown series ------------------------------------------------------
    series_s = pd.Series(value_series, dtype="float64")
    running_max = series_s.cummax()
    drawdown_s = (series_s / running_max - 1.0).tolist()

    return BacktestResult(
        final_value=float(final_value),
        total_contribution=float(total_contribution),
        total_profit=float(total_profit),
        cagr=float(cagr_value),
        irr=irr_value,
        max_drawdown=float(mdd),
        annualized_volatility=float(vol),
        sharpe_ratio=float(sharpe),
        annual_returns=annual_returns,
        portfolio_value_series=list(zip(dates, [float(v) for v in value_series])),
        drawdown_series=list(zip(dates, [float(v) for v in drawdown_s])),
    )


# ---------------------------------------------------------------------------
# DB loading layer (thin, separate from the pure engine)
# ---------------------------------------------------------------------------


def load_prices_from_db(
    session, symbols: list[str], start: _dt.date, end: _dt.date
) -> dict[str, pd.Series]:
    """Load price series (adjusted_close, falling back to close) for each
    symbol from ``EtfPrice``, returning ``{symbol: pd.Series indexed by date}``.
    """
    from app.models import EtfPrice

    result: dict[str, pd.Series] = {}
    for sym in symbols:
        rows = (
            session.query(EtfPrice)
            .filter(
                EtfPrice.etf_symbol == sym,
                EtfPrice.trade_date >= start,
                EtfPrice.trade_date <= end,
            )
            .order_by(EtfPrice.trade_date.asc())
            .all()
        )
        idx = []
        vals = []
        for r in rows:
            price = r.adjusted_close if r.adjusted_close is not None else r.close
            if price is None:
                continue
            idx.append(r.trade_date)
            vals.append(float(price))
        result[sym] = pd.Series(vals, index=pd.to_datetime(idx))
    return result


def load_dividends_from_db(
    session, symbols: list[str], start: _dt.date, end: _dt.date
) -> dict[str, list[tuple[_dt.date, float]]]:
    """Load dividend events for each symbol from ``EtfDividend``, returning
    ``{symbol: [(reinvest_date, amount_per_share), ...]}`` where
    ``reinvest_date`` = ``payment_date`` if present else ``ex_dividend_date``.
    """
    from app.models import EtfDividend

    result: dict[str, list[tuple[_dt.date, float]]] = {}
    for sym in symbols:
        rows = (
            session.query(EtfDividend)
            .filter(
                EtfDividend.etf_symbol == sym,
                EtfDividend.ex_dividend_date >= start,
                EtfDividend.ex_dividend_date <= end,
            )
            .order_by(EtfDividend.ex_dividend_date.asc())
            .all()
        )
        events = []
        for r in rows:
            if r.dividend_amount is None:
                continue
            reinvest_date = r.payment_date if r.payment_date is not None else r.ex_dividend_date
            events.append((reinvest_date, float(r.dividend_amount)))
        result[sym] = events
    return result


def run_backtest_from_db(
    session,
    config: BacktestConfig,
    portfolio_id: int | None = None,
    name: str | None = None,
    persist: bool = False,
) -> dict:
    """Load data from DB, run the pure engine, optionally persist a
    ``BacktestRun`` row, and return the result as a dict.

    ``persist=True`` writes ``result_json`` (JSONB) — only used against a
    real Postgres session; SQLite test sessions should call with
    ``persist=False`` (the default).
    """
    symbols = list(config.weights.keys())
    prices = load_prices_from_db(session, symbols, config.start_date, config.end_date)
    dividends = load_dividends_from_db(
        session, symbols, config.start_date, config.end_date
    )

    result = run_backtest(prices, dividends, config)
    result_dict = result.to_dict()

    if persist:
        from app.models import BacktestRun

        run = BacktestRun(
            portfolio_id=portfolio_id,
            name=name,
            start_date=config.start_date,
            end_date=config.end_date,
            initial_amount=config.initial_amount,
            monthly_contribution=config.monthly_contribution,
            rebalance_frequency=config.rebalance_frequency,
            dividend_reinvest=config.dividend_reinvest,
            transaction_cost_rate=config.transaction_cost_rate,
            final_value=result.final_value,
            total_contribution=result.total_contribution,
            total_profit=result.total_profit,
            cagr=result.cagr,
            max_drawdown=result.max_drawdown,
            annualized_volatility=result.annualized_volatility,
            sharpe_ratio=result.sharpe_ratio,
            result_json=result_dict,
        )
        session.add(run)
        session.commit()
        result_dict["backtest_run_id"] = run.id

    return result_dict
