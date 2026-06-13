"""Pydantic v2 request schemas for backtest endpoints."""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field, model_validator


class BacktestRequest(BaseModel):
    portfolio_id: int | None = None
    symbols: list[str] | None = None
    weights: list[float] | None = None

    start_date: dt.date
    end_date: dt.date

    initial_amount: float
    monthly_contribution: float = 0.0
    dividend_reinvest: bool = True
    rebalance_frequency: str = "none"
    transaction_cost_rate: float = 0.0
    risk_free_rate: float = 0.0

    benchmark_symbol: str | None = None

    name: str | None = None

    @model_validator(mode="after")
    def _check_source(self) -> "BacktestRequest":
        if self.portfolio_id is None:
            if not self.symbols or not self.weights:
                raise ValueError(
                    "Either portfolio_id or both symbols and weights must be provided."
                )
            if len(self.symbols) != len(self.weights):
                raise ValueError("symbols and weights must have the same length.")
        return self
