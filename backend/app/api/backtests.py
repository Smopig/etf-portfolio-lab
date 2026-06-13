"""Backtest endpoint: thin wrapper over backtest_service."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.responses import not_found, ok, validation_error
from app.core.database import get_db
from app.schemas.backtest import BacktestRequest
from app.services.backtest_service import BacktestConfig, run_backtest_from_db
from app.services.portfolio_service import get_portfolio

router = APIRouter(prefix="/backtests", tags=["backtests"])


@router.post("")
def run_backtest_endpoint(
    payload: BacktestRequest,
    persist: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> dict:
    if payload.portfolio_id is not None:
        portfolio = get_portfolio(db, payload.portfolio_id)
        if portfolio is None:
            raise not_found(f"Portfolio {payload.portfolio_id} not found.")
        weights = {item["etf_symbol"]: float(item["target_weight"]) for item in portfolio["items"]}
    else:
        weights = dict(zip(payload.symbols, payload.weights))

    if not weights:
        raise validation_error("No ETFs to backtest.")

    try:
        config = BacktestConfig(
            start_date=payload.start_date,
            end_date=payload.end_date,
            weights=weights,
            initial_amount=payload.initial_amount,
            monthly_contribution=payload.monthly_contribution,
            dividend_reinvest=payload.dividend_reinvest,
            rebalance_frequency=payload.rebalance_frequency,
            transaction_cost_rate=payload.transaction_cost_rate,
            risk_free_rate=payload.risk_free_rate,
        )
    except ValueError as exc:
        raise validation_error(str(exc)) from exc

    try:
        result = run_backtest_from_db(
            db,
            config,
            portfolio_id=payload.portfolio_id,
            name=payload.name,
            persist=persist,
            benchmark_symbol=payload.benchmark_symbol,
        )
    except ValueError as exc:
        raise validation_error(str(exc)) from exc

    return ok(result)
