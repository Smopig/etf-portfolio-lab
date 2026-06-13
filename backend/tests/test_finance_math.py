import datetime as dt

import pytest

from app.utils.finance_math import (
    annualized_volatility,
    cagr,
    effective_holdings,
    hhi,
    max_drawdown,
    normalize_weights_to_fraction,
    sharpe_ratio,
    top_n_weight,
    xirr,
)


def test_normalize_weights_to_fraction_percent_scale():
    weights = [40.0, 30.0, 20.0, 10.0]
    result = normalize_weights_to_fraction(weights)
    assert result == [0.4, 0.3, 0.2, 0.1]


def test_normalize_weights_to_fraction_fraction_scale():
    weights = [0.4, 0.3, 0.2, 0.1]
    result = normalize_weights_to_fraction(weights)
    assert result == [0.4, 0.3, 0.2, 0.1]


def test_normalize_weights_to_fraction_empty():
    assert normalize_weights_to_fraction([]) == []


def test_normalize_weights_to_fraction_none_values():
    weights = [50.0, None, 50.0]
    result = normalize_weights_to_fraction(weights)
    assert result == [0.5, 0.0, 0.5]


def test_hhi_basic():
    # 4 equal holdings of 25% each -> HHI = 4 * 0.25^2 = 0.25
    weights = [0.25, 0.25, 0.25, 0.25]
    assert hhi(weights) == 0.25


def test_hhi_empty():
    assert hhi([]) == 0.0


def test_effective_holdings():
    assert effective_holdings(0.25) == 4.0


def test_effective_holdings_zero():
    assert effective_holdings(0.0) is None


def test_top_n_weight():
    sorted_weights = [0.4, 0.3, 0.2, 0.1]
    assert top_n_weight(sorted_weights, 1) == 0.4
    assert top_n_weight(sorted_weights, 3) == 0.9
    assert top_n_weight(sorted_weights, 10) == 1.0


def test_top_n_weight_empty():
    assert top_n_weight([], 5) == 0.0
    assert top_n_weight([0.5], 0) == 0.0


# ---------------------------------------------------------------------------
# Backtest metric helpers (Phase 7)
# ---------------------------------------------------------------------------


def test_cagr_one_year_doubling():
    assert cagr(200.0, 100.0, 1.0) == pytest.approx(1.0)


def test_cagr_two_year_doubling():
    assert cagr(200.0, 100.0, 2.0) == pytest.approx(0.41421356, rel=1e-6)


def test_cagr_degenerate():
    assert cagr(200.0, 0.0, 1.0) == 0.0
    assert cagr(200.0, 100.0, 0.0) == 0.0


def test_max_drawdown_basic():
    assert max_drawdown([100, 120, 90, 150]) == pytest.approx(-0.25)


def test_max_drawdown_empty():
    assert max_drawdown([]) == 0.0


def test_annualized_volatility_constant_series():
    assert annualized_volatility([100, 100, 100, 100]) == 0.0


def test_annualized_volatility_basic_positive():
    values = [100, 102, 99, 105, 103, 108]
    vol = annualized_volatility(values)
    assert vol > 0


def test_sharpe_ratio_basic():
    assert sharpe_ratio(0.1, 0.2, 0.02) == pytest.approx(0.4)


def test_sharpe_ratio_zero_volatility():
    assert sharpe_ratio(0.1, 0.0, 0.02) == 0.0


def test_xirr_simple_two_flow():
    import datetime as _dt

    cashflows = [(_dt.date(2025, 1, 1), -100.0), (_dt.date(2026, 1, 1), 110.0)]
    result = xirr(cashflows)
    assert result == pytest.approx(0.10, abs=1e-3)
