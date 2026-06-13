"""Future-value projection / financial planning engine (Phase 8).

Architecture mirrors Phase 7 (``backtest_service.py``):

- ``project_future_value`` and the goal-solvers are PURE functions: no
  database access, operate only on numeric inputs, fully unit-testable.
- ``run_projection`` / ``persist_projection`` are a thin persistence layer
  that, when ``persist=True``, writes a ``ProjectionRun`` row (including
  ``result_json``, which is JSONB) — only this layer touches the DB.

Modeling notes (CLAUDE.md §7):

- This is a hypothetical future simulation based on an ASSUMED constant
  annual return rate. It is NOT a forecast/guarantee and is for research
  purposes only — see ``DISCLAIMER``.
- monthly_rate = (1 + annual_rate) ** (1/12) - 1
- Each month: value = value * (1 + monthly_rate) + monthly_contribution
  (contribution applied at the END of the month).
"""

from __future__ import annotations

from dataclasses import dataclass

DISCLAIMER = "未來模擬基於假設報酬率，不代表保證收益，僅供研究分析。"

DEFAULT_SCENARIOS: dict[str, float] = {
    "保守": 0.04,
    "中性": 0.06,
    "樂觀": 0.08,
}


@dataclass
class ProjectionConfig:
    initial_amount: float
    monthly_contribution: float = 0.0
    annual_return_rate: float = 0.0
    years: int = 0
    target_amount: float | None = None


def _monthly_rate(annual_rate: float) -> float:
    return (1.0 + annual_rate) ** (1.0 / 12.0) - 1.0


def project_future_value(config: ProjectionConfig) -> dict:
    """Pure simulation of monthly compounding + monthly contributions.

    Returns a dict with final_value, total_contribution, total_profit,
    target_achieved, yearly_series, monthly_rate, disclaimer.
    """
    months = int(round(config.years * 12))
    m = _monthly_rate(config.annual_return_rate)

    value = float(config.initial_amount)
    contributed = float(config.initial_amount)

    yearly_series: list[dict] = []

    for month_idx in range(1, months + 1):
        value = value * (1.0 + m) + config.monthly_contribution
        contributed += config.monthly_contribution

        if month_idx % 12 == 0:
            year = month_idx // 12
            yearly_series.append(
                {
                    "year": year,
                    "value": value,
                    "contributed": contributed,
                    "profit": value - contributed,
                }
            )

    final_value = value
    total_contribution = contributed
    total_profit = final_value - total_contribution

    target_achieved: bool | None = None
    if config.target_amount is not None:
        target_achieved = final_value >= config.target_amount

    return {
        "final_value": final_value,
        "total_contribution": total_contribution,
        "total_profit": total_profit,
        "target_achieved": target_achieved,
        "yearly_series": yearly_series,
        "monthly_rate": m,
        "disclaimer": DISCLAIMER,
    }


def project_scenarios(
    initial_amount: float,
    monthly_contribution: float,
    years: int,
    scenarios: dict[str, float] | None = None,
    target_amount: float | None = None,
) -> dict:
    """Run ``project_future_value`` under multiple named annual-rate
    scenarios (defaults: 保守 4% / 中性 6% / 樂觀 8%)."""
    scenarios = scenarios if scenarios is not None else DEFAULT_SCENARIOS

    results: dict[str, dict] = {}
    for label, rate in scenarios.items():
        config = ProjectionConfig(
            initial_amount=initial_amount,
            monthly_contribution=monthly_contribution,
            annual_return_rate=rate,
            years=years,
            target_amount=target_amount,
        )
        res = project_future_value(config)
        results[label] = {
            "annual_return_rate": rate,
            "final_value": res["final_value"],
            "total_contribution": res["total_contribution"],
            "total_profit": res["total_profit"],
            "target_achieved": res["target_achieved"],
            "yearly_series": res["yearly_series"],
        }

    return {
        "scenarios": results,
        "rates_used": dict(scenarios),
        "disclaimer": DISCLAIMER,
    }


def required_years(
    initial_amount: float,
    monthly_contribution: float,
    annual_return_rate: float,
    target_amount: float,
    max_years: int = 100,
) -> dict:
    """Smallest whole number of years such that the projected value at the
    end of that year reaches ``target_amount``. Also returns the fractional
    month count within max_years*12 at which the target is first crossed.

    Returns ``{"achievable": False, ...}`` if not reached within
    ``max_years``.
    """
    m = _monthly_rate(annual_return_rate)

    value = float(initial_amount)
    if value >= target_amount:
        return {
            "achievable": True,
            "years": 0,
            "months": 0,
            "disclaimer": DISCLAIMER,
        }

    max_months = int(round(max_years * 12))
    for month_idx in range(1, max_months + 1):
        value = value * (1.0 + m) + monthly_contribution
        if value >= target_amount:
            years_needed = -(-month_idx // 12)  # ceil division
            return {
                "achievable": True,
                "years": years_needed,
                "months": month_idx,
                "disclaimer": DISCLAIMER,
            }

    return {
        "achievable": False,
        "years": None,
        "months": None,
        "disclaimer": DISCLAIMER,
    }


def required_monthly_contribution(
    initial_amount: float,
    annual_return_rate: float,
    years: int,
    target_amount: float,
) -> dict:
    """Solve for the constant monthly contribution C such that:

        FV = initial*(1+m)^N + C * (((1+m)^N - 1) / m)  >= target_amount

    where m = monthly_rate, N = years*12. Closed-form inversion for C.
    """
    m = _monthly_rate(annual_return_rate)
    N = int(round(years * 12))

    if N <= 0:
        # No time to contribute; just compare initial amount.
        return {
            "monthly_contribution": 0.0,
            "achievable_with_zero": initial_amount >= target_amount,
            "disclaimer": DISCLAIMER,
        }

    growth = (1.0 + m) ** N
    fv_initial = initial_amount * growth

    if fv_initial >= target_amount:
        return {
            "monthly_contribution": 0.0,
            "achievable_with_zero": True,
            "disclaimer": DISCLAIMER,
        }

    remaining = target_amount - fv_initial

    if m == 0:
        contribution = remaining / N
    else:
        annuity_factor = (growth - 1.0) / m
        contribution = remaining / annuity_factor

    return {
        "monthly_contribution": max(contribution, 0.0),
        "achievable_with_zero": False,
        "disclaimer": DISCLAIMER,
    }


def required_annual_return(
    initial_amount: float,
    monthly_contribution: float,
    years: int,
    target_amount: float,
    rate_low: float = -0.99,
    rate_high: float = 2.0,
    tolerance: float = 1e-6,
    max_iterations: int = 200,
) -> dict:
    """Solve for the constant annual return rate that makes the projected
    final value equal ``target_amount``, via bisection (final value is
    monotonically increasing in the rate)."""

    def final_value(rate: float) -> float:
        return project_future_value(
            ProjectionConfig(
                initial_amount=initial_amount,
                monthly_contribution=monthly_contribution,
                annual_return_rate=rate,
                years=years,
            )
        )["final_value"]

    fv_low = final_value(rate_low)
    fv_high = final_value(rate_high)

    if fv_low >= target_amount:
        # Even the worst case reaches target; minimal rate works.
        return {"achievable": True, "annual_return_rate": rate_low, "disclaimer": DISCLAIMER}

    if fv_high < target_amount:
        return {"achievable": False, "annual_return_rate": None, "disclaimer": DISCLAIMER}

    lo, hi = rate_low, rate_high
    for _ in range(max_iterations):
        mid = (lo + hi) / 2.0
        fv_mid = final_value(mid)
        if abs(fv_mid - target_amount) <= tolerance * max(1.0, abs(target_amount)):
            break
        if fv_mid < target_amount:
            lo = mid
        else:
            hi = mid
    else:
        mid = (lo + hi) / 2.0

    return {"achievable": True, "annual_return_rate": mid, "disclaimer": DISCLAIMER}


def run_projection(
    session,
    config: ProjectionConfig,
    persist: bool = False,
    name: str | None = None,
) -> dict:
    """Run the pure engine and, when ``persist=True``, write a
    ``ProjectionRun`` row (``result_json`` is JSONB — only used against a
    real Postgres session; SQLite test sessions should use
    ``persist=False``, the default)."""

    result = project_future_value(config)

    if persist:
        from app.models import ProjectionRun

        run = ProjectionRun(
            name=name,
            initial_amount=config.initial_amount,
            monthly_contribution=config.monthly_contribution,
            annual_return_rate=config.annual_return_rate,
            years=config.years,
            target_amount=config.target_amount,
            final_value=result["final_value"],
            total_contribution=result["total_contribution"],
            total_profit=result["total_profit"],
            target_achieved=result["target_achieved"],
            result_json=result,
        )
        session.add(run)
        session.commit()
        result["projection_run_id"] = run.id

    return result


def persist_projection(
    session,
    config: ProjectionConfig,
    result: dict,
    name: str | None = None,
):
    """Persist an already-computed projection result as a ``ProjectionRun``
    row. ``result_json`` is JSONB — only call against a real Postgres
    session."""
    from app.models import ProjectionRun

    run = ProjectionRun(
        name=name,
        initial_amount=config.initial_amount,
        monthly_contribution=config.monthly_contribution,
        annual_return_rate=config.annual_return_rate,
        years=config.years,
        target_amount=config.target_amount,
        final_value=result["final_value"],
        total_contribution=result["total_contribution"],
        total_profit=result["total_profit"],
        target_achieved=result["target_achieved"],
        result_json=result,
    )
    session.add(run)
    session.commit()
    return run
