"""Tests for the pure backtest engine (Phase 7).

These tests use synthetic, hand-constructable price/dividend series and do
not touch any database — ``run_backtest`` is pure pandas/numpy.
"""

from __future__ import annotations

import datetime as dt

import pandas as pd
import pytest

from app.services.backtest_service import BacktestConfig, run_backtest


def _daily_index(start: dt.date, n: int) -> pd.DatetimeIndex:
    return pd.date_range(start=start, periods=n, freq="D")


def test_single_asset_doubling_no_contributions():
    start = dt.date(2024, 1, 1)
    n = 366  # exactly 1 year (2024 is a leap year, but we use 365.25 anyway)
    idx = _daily_index(start, n)

    # Linear price path 100 -> 200, with a dip to create a known drawdown.
    prices = []
    for i in range(n):
        base = 100 + (100 * i / (n - 1))
        prices.append(base)
    # Introduce a dip at index 100: drop to 50% of its value -> -25% type dip
    prices[100] = prices[100] * 0.5

    series = pd.Series(prices, index=idx)

    config = BacktestConfig(
        start_date=start,
        end_date=(idx[-1]).date(),
        weights={"AAA": 1.0},
        initial_amount=100.0,
        monthly_contribution=0.0,
        dividend_reinvest=False,
        rebalance_frequency="none",
        transaction_cost_rate=0.0,
    )

    result = run_backtest({"AAA": series}, {"AAA": []}, config)

    # final value ~ 2x initial (price doubles, fractional shares)
    assert result.final_value == pytest.approx(2 * 100.0, rel=0.05)
    assert result.total_contribution == pytest.approx(100.0)
    assert result.total_profit == pytest.approx(result.final_value - 100.0)
    assert result.cagr == pytest.approx(1.0, rel=0.1)

    # Drawdown should be negative and reasonably large given the dip.
    assert result.max_drawdown < -0.1
    assert result.max_drawdown <= 0

    # Conservation: final_value == shares*price + cash (no cash held here,
    # checked implicitly via final_value already returned by engine).
    assert result.irr is None  # no monthly contributions -> no IRR


def test_dca_increases_total_contribution_and_irr_is_finite():
    start = dt.date(2024, 1, 1)
    n = 400  # > 1 year so multiple month boundaries occur
    idx = _daily_index(start, n)
    prices = pd.Series([100 + 0.05 * i for i in range(n)], index=idx)

    monthly = 50.0
    config = BacktestConfig(
        start_date=start,
        end_date=idx[-1].date(),
        weights={"AAA": 1.0},
        initial_amount=1000.0,
        monthly_contribution=monthly,
        dividend_reinvest=False,
        rebalance_frequency="none",
    )

    result = run_backtest({"AAA": prices}, {"AAA": []}, config)

    # Count distinct month boundaries crossed after the start date.
    months_seen = set()
    for d in [ts.date() for ts in idx]:
        months_seen.add((d.year, d.month))
    n_months = len(months_seen)  # includes the starting month
    expected_contribution = 1000.0 + monthly * (n_months - 1)

    assert result.total_contribution == pytest.approx(expected_contribution)
    assert result.final_value > result.total_contribution * 0  # sanity, positive
    assert result.final_value > 0
    assert result.irr is not None
    assert abs(result.irr) < 100  # finite, sane magnitude
    assert result.total_profit == pytest.approx(
        result.final_value - result.total_contribution
    )


def test_dividend_reinvest_on_vs_off():
    start = dt.date(2024, 1, 1)
    n = 100
    idx = _daily_index(start, n)
    # Flat price so the only growth source is dividend reinvestment.
    prices = pd.Series([100.0] * n, index=idx)

    # A single dividend event halfway through.
    div_date = idx[50].date()
    dividends = {"AAA": [(div_date, 5.0)]}  # $5/share dividend

    base_kwargs = dict(
        start_date=start,
        end_date=idx[-1].date(),
        weights={"AAA": 1.0},
        initial_amount=1000.0,
        monthly_contribution=0.0,
        rebalance_frequency="none",
    )

    config_on = BacktestConfig(dividend_reinvest=True, **base_kwargs)
    config_off = BacktestConfig(dividend_reinvest=False, **base_kwargs)

    result_on = run_backtest({"AAA": prices}, dividends, config_on)
    result_off = run_backtest({"AAA": prices}, dividends, config_off)

    # With reinvestment, the dividend cash buys more shares -> higher final value
    # (flat price means off-case final value == initial_amount exactly).
    assert result_off.final_value == pytest.approx(1000.0)
    assert result_on.final_value > result_off.final_value
    # Reinvested dividend cash = 1000/100 shares * $5 = $50
    assert result_on.final_value == pytest.approx(1050.0)


def test_rebalance_changes_outcome_vs_none():
    start = dt.date(2024, 1, 1)
    n = 400
    idx = _daily_index(start, n)

    # Asset A rises steadily, asset B stays flat.
    a_prices = pd.Series([100 * (1 + 0.002) ** i for i in range(n)], index=idx)
    b_prices = pd.Series([100.0] * n, index=idx)

    base_kwargs = dict(
        start_date=start,
        end_date=idx[-1].date(),
        weights={"A": 0.5, "B": 0.5},
        initial_amount=1000.0,
        monthly_contribution=0.0,
        dividend_reinvest=False,
        transaction_cost_rate=0.0,
    )

    config_none = BacktestConfig(rebalance_frequency="none", **base_kwargs)
    config_quarterly = BacktestConfig(rebalance_frequency="quarterly", **base_kwargs)

    prices = {"A": a_prices, "B": b_prices}
    divs = {"A": [], "B": []}

    result_none = run_backtest(prices, divs, config_none)
    result_quarterly = run_backtest(prices, divs, config_quarterly)

    # The two strategies should produce different final values.
    assert result_none.final_value != pytest.approx(result_quarterly.final_value)

    # Quarterly rebalancing sells the winner (A) periodically to buy the
    # flat asset (B), which for a steadily-rising A and flat B should
    # produce a LOWER final value than buy-and-hold (since A outperforms).
    assert result_quarterly.final_value < result_none.final_value


def test_transaction_cost_reduces_final_value():
    start = dt.date(2024, 1, 1)
    n = 400
    idx = _daily_index(start, n)

    a_prices = pd.Series([100 * (1 + 0.002) ** i for i in range(n)], index=idx)
    b_prices = pd.Series([100.0] * n, index=idx)

    base_kwargs = dict(
        start_date=start,
        end_date=idx[-1].date(),
        weights={"A": 0.5, "B": 0.5},
        initial_amount=1000.0,
        monthly_contribution=0.0,
        dividend_reinvest=False,
        rebalance_frequency="quarterly",
    )

    config_no_cost = BacktestConfig(transaction_cost_rate=0.0, **base_kwargs)
    config_with_cost = BacktestConfig(transaction_cost_rate=0.01, **base_kwargs)

    prices = {"A": a_prices, "B": b_prices}
    divs = {"A": [], "B": []}

    result_no_cost = run_backtest(prices, divs, config_no_cost)
    result_with_cost = run_backtest(prices, divs, config_with_cost)

    assert result_with_cost.final_value < result_no_cost.final_value


def test_two_asset_alignment_on_common_dates():
    start = dt.date(2024, 1, 1)
    # Asset A has 100 days, asset B has 90 days starting 5 days later and
    # ending 5 days earlier -> common dates should be the overlap.
    idx_a = _daily_index(start, 100)
    idx_b = _daily_index(start + dt.timedelta(days=5), 90)

    a_prices = pd.Series([100.0 + i for i in range(100)], index=idx_a)
    b_prices = pd.Series([200.0 + i for i in range(90)], index=idx_b)

    common_end = min(idx_a[-1], idx_b[-1]).date()
    config = BacktestConfig(
        start_date=start,
        end_date=common_end,
        weights={"A": 0.5, "B": 0.5},
        initial_amount=1000.0,
        dividend_reinvest=False,
        rebalance_frequency="none",
    )

    result = run_backtest(
        {"A": a_prices, "B": b_prices}, {"A": [], "B": []}, config
    )

    # The aligned series should start on idx_b[0] (the later start date).
    first_date = result.portfolio_value_series[0][0]
    assert first_date == idx_b[0].date()

    last_date = result.portfolio_value_series[-1][0]
    assert last_date == min(idx_a[-1], idx_b[-1]).date()

    assert result.final_value > 0
    assert result.total_profit == pytest.approx(result.final_value - 1000.0)
