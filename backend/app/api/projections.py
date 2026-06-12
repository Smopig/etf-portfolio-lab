"""Projection / financial planning endpoints: thin wrapper over projection_service."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.responses import ok
from app.core.database import get_db
from app.schemas.projection import GoalSeekRequest, ProjectionRequest, ScenarioRequest
from app.services.projection_service import (
    ProjectionConfig,
    project_scenarios,
    required_annual_return,
    required_monthly_contribution,
    required_years,
    run_projection,
)

router = APIRouter(prefix="/projections", tags=["projections"])


@router.post("")
def project(payload: ProjectionRequest, db: Session = Depends(get_db)) -> dict:
    config = ProjectionConfig(
        initial_amount=payload.initial_amount,
        monthly_contribution=payload.monthly_contribution,
        annual_return_rate=payload.annual_return_rate,
        years=payload.years,
        target_amount=payload.target_amount,
    )
    result = run_projection(db, config, persist=payload.persist, name=payload.name)
    return ok(result)


@router.post("/scenarios")
def scenarios(payload: ScenarioRequest) -> dict:
    result = project_scenarios(
        initial_amount=payload.initial_amount,
        monthly_contribution=payload.monthly_contribution,
        years=payload.years,
        scenarios=payload.scenarios,
        target_amount=payload.target_amount,
    )
    return ok(result)


@router.post("/goal-seek")
def goal_seek(payload: GoalSeekRequest) -> dict:
    if payload.solve_for == "years":
        result = required_years(
            initial_amount=payload.initial_amount,
            monthly_contribution=payload.monthly_contribution,
            annual_return_rate=payload.annual_return_rate,
            target_amount=payload.target_amount,
        )
    elif payload.solve_for == "monthly_contribution":
        result = required_monthly_contribution(
            initial_amount=payload.initial_amount,
            annual_return_rate=payload.annual_return_rate,
            years=payload.years,
            target_amount=payload.target_amount,
        )
    else:  # annual_return
        result = required_annual_return(
            initial_amount=payload.initial_amount,
            monthly_contribution=payload.monthly_contribution,
            years=payload.years,
            target_amount=payload.target_amount,
        )
    return ok(result)
