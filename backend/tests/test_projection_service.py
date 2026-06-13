"""Tests for the pure financial projection engine (Phase 8)."""

import pytest

from app.services.projection_service import (
    ProjectionConfig,
    project_future_value,
    project_scenarios,
    required_annual_return,
    required_monthly_contribution,
    required_years,
)


def test_zero_rate_simple_addition():
    config = ProjectionConfig(
        initial_amount=100_000,
        monthly_contribution=1_000,
        annual_return_rate=0.0,
        years=10,
    )
    result = project_future_value(config)

    months = 10 * 12
    expected_final = 100_000 + 1_000 * months

    assert result["final_value"] == pytest.approx(expected_final)
    assert result["total_contribution"] == pytest.approx(expected_final)
    assert result["total_profit"] == pytest.approx(0.0, abs=1e-9)


def test_known_compounding_one_year_six_percent():
    config = ProjectionConfig(
        initial_amount=1_000_000,
        monthly_contribution=0.0,
        annual_return_rate=0.06,
        years=1,
    )
    result = project_future_value(config)

    assert result["final_value"] == pytest.approx(1_060_000, rel=1e-6)
    assert result["total_contribution"] == pytest.approx(1_000_000)
    assert result["total_profit"] == pytest.approx(60_000, rel=1e-6)


def test_yearly_series_length_and_shape():
    config = ProjectionConfig(
        initial_amount=10_000,
        monthly_contribution=500,
        annual_return_rate=0.05,
        years=3,
    )
    result = project_future_value(config)

    assert len(result["yearly_series"]) == 3
    for i, entry in enumerate(result["yearly_series"], start=1):
        assert entry["year"] == i
        assert "value" in entry
        assert "contributed" in entry
        assert "profit" in entry

    # last yearly snapshot matches final result
    assert result["yearly_series"][-1]["value"] == pytest.approx(result["final_value"])
    assert result["yearly_series"][-1]["contributed"] == pytest.approx(
        result["total_contribution"]
    )


def test_target_achieved_flag():
    config_hit = ProjectionConfig(
        initial_amount=1_000_000,
        monthly_contribution=0.0,
        annual_return_rate=0.06,
        years=1,
        target_amount=1_000_000,
    )
    result_hit = project_future_value(config_hit)
    assert result_hit["target_achieved"] is True

    config_miss = ProjectionConfig(
        initial_amount=1_000_000,
        monthly_contribution=0.0,
        annual_return_rate=0.06,
        years=1,
        target_amount=2_000_000,
    )
    result_miss = project_future_value(config_miss)
    assert result_miss["target_achieved"] is False

    config_none = ProjectionConfig(
        initial_amount=1_000_000,
        monthly_contribution=0.0,
        annual_return_rate=0.06,
        years=1,
    )
    result_none = project_future_value(config_none)
    assert result_none["target_achieved"] is None


def test_scenarios_ordering():
    scenarios = project_scenarios(
        initial_amount=100_000,
        monthly_contribution=2_000,
        years=20,
    )

    optimistic = scenarios["scenarios"]["樂觀"]["final_value"]
    neutral = scenarios["scenarios"]["中性"]["final_value"]
    conservative = scenarios["scenarios"]["保守"]["final_value"]

    assert optimistic > neutral > conservative
    assert scenarios["rates_used"]["樂觀"] == 0.08
    assert scenarios["rates_used"]["中性"] == 0.06
    assert scenarios["rates_used"]["保守"] == 0.04


def test_scenarios_custom_rates():
    custom = {"low": 0.01, "high": 0.10}
    scenarios = project_scenarios(
        initial_amount=50_000,
        monthly_contribution=1_000,
        years=5,
        scenarios=custom,
    )

    assert set(scenarios["scenarios"].keys()) == {"low", "high"}
    assert scenarios["scenarios"]["high"]["final_value"] > scenarios["scenarios"]["low"]["final_value"]


def test_required_monthly_contribution_round_trip():
    initial = 100_000
    annual_rate = 0.06
    years = 10
    target = 2_000_000

    solved = required_monthly_contribution(
        initial_amount=initial,
        annual_return_rate=annual_rate,
        years=years,
        target_amount=target,
    )

    contribution = solved["monthly_contribution"]
    assert contribution > 0
    assert solved["achievable_with_zero"] is False

    result = project_future_value(
        ProjectionConfig(
            initial_amount=initial,
            monthly_contribution=contribution,
            annual_return_rate=annual_rate,
            years=years,
        )
    )

    assert result["final_value"] == pytest.approx(target, rel=1e-6)


def test_required_monthly_contribution_zero_rate():
    initial = 0
    years = 10
    target = 120_000

    solved = required_monthly_contribution(
        initial_amount=initial,
        annual_return_rate=0.0,
        years=years,
        target_amount=target,
    )

    months = years * 12
    assert solved["monthly_contribution"] == pytest.approx(target / months)


def test_required_monthly_contribution_already_met():
    solved = required_monthly_contribution(
        initial_amount=5_000_000,
        annual_return_rate=0.06,
        years=10,
        target_amount=1_000_000,
    )
    assert solved["monthly_contribution"] == 0.0
    assert solved["achievable_with_zero"] is True


def test_required_annual_return_round_trip():
    initial = 100_000
    monthly = 5_000
    years = 10
    target = 1_500_000

    solved = required_annual_return(
        initial_amount=initial,
        monthly_contribution=monthly,
        years=years,
        target_amount=target,
    )

    assert solved["achievable"] is True
    rate = solved["annual_return_rate"]

    result = project_future_value(
        ProjectionConfig(
            initial_amount=initial,
            monthly_contribution=monthly,
            annual_return_rate=rate,
            years=years,
        )
    )

    assert result["final_value"] == pytest.approx(target, rel=1e-4)


def test_required_annual_return_unreachable():
    # Absurdly high target, even at 200% annual return won't reach it.
    solved = required_annual_return(
        initial_amount=100,
        monthly_contribution=0,
        years=1,
        target_amount=1e18,
    )
    assert solved["achievable"] is False
    assert solved["annual_return_rate"] is None


def test_required_years_known_horizon():
    # initial=1,000,000, rate=0, monthly=0 -> never reaches a higher target
    # so use a reachable scenario with contributions.
    initial = 0
    monthly = 10_000
    annual_rate = 0.0
    # After exactly 10 years (120 months) of 10,000/month with 0% growth,
    # value == 1,200,000.
    target = 1_200_000

    result = required_years(
        initial_amount=initial,
        monthly_contribution=monthly,
        annual_return_rate=annual_rate,
        target_amount=target,
        max_years=50,
    )

    assert result["achievable"] is True
    assert result["years"] == 10
    assert result["months"] == 120


def test_required_years_unreachable():
    result = required_years(
        initial_amount=0,
        monthly_contribution=0,
        annual_return_rate=0.0,
        target_amount=1_000_000_000,
        max_years=5,
    )

    assert result["achievable"] is False
    assert result["years"] is None
    assert result["months"] is None


def test_required_years_already_met():
    result = required_years(
        initial_amount=2_000_000,
        monthly_contribution=0,
        annual_return_rate=0.0,
        target_amount=1_000_000,
        max_years=10,
    )

    assert result["achievable"] is True
    assert result["years"] == 0
    assert result["months"] == 0


def test_disclaimer_present_everywhere():
    config = ProjectionConfig(initial_amount=1000, monthly_contribution=0, annual_return_rate=0.05, years=1)
    result = project_future_value(config)
    assert "僅供研究分析" in result["disclaimer"]

    scenarios = project_scenarios(1000, 100, 5)
    assert "僅供研究分析" in scenarios["disclaimer"]

    solved = required_monthly_contribution(1000, 0.05, 5, 100000)
    assert "僅供研究分析" in solved["disclaimer"]
