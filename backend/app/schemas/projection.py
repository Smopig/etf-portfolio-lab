"""Pydantic v2 request schemas for projection endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ProjectionRequest(BaseModel):
    initial_amount: float
    monthly_contribution: float = 0.0
    annual_return_rate: float = 0.0
    years: int = 0
    target_amount: float | None = None
    name: str | None = None
    persist: bool = False


class ScenarioRequest(BaseModel):
    initial_amount: float
    monthly_contribution: float = 0.0
    years: int = 0
    scenarios: dict[str, float] | None = None
    target_amount: float | None = None


class GoalSeekRequest(BaseModel):
    solve_for: Literal["years", "monthly_contribution", "annual_return"]

    initial_amount: float
    monthly_contribution: float = 0.0
    annual_return_rate: float = 0.0
    years: int = 0
    target_amount: float
