"""AI analysis endpoints (Phase 13).

Per CLAUDE.md §7, AI analysis must be grounded in system data with explicit
data sources/dates, must not fabricate holdings/exposures, must not give
buy/sell instructions, and must include backtest/projection disclaimers.
The default provider is the Mock provider (no network, no API key needed).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.responses import ok, validation_error
from app.core.database import get_db
from app.schemas.portfolio import PortfolioItemIn
from app.services import ai_analysis_service

router = APIRouter(prefix="/ai", tags=["ai"])


class AnalyzeEtfRequest(BaseModel):
    symbol: str
    question: str | None = None


class AnalyzePortfolioRequest(BaseModel):
    portfolio_id: int | None = None
    items: list[PortfolioItemIn] | None = None
    question: str | None = None


class ExplainBacktestRequest(BaseModel):
    result: dict
    question: str | None = None


class ExplainProjectionRequest(BaseModel):
    result: dict
    question: str | None = None


@router.post("/analyze-etf")
def analyze_etf(payload: AnalyzeEtfRequest, db: Session = Depends(get_db)) -> dict:
    result = ai_analysis_service.analyze_etf(db, payload.symbol, question=payload.question)
    return ok(result)


@router.post("/analyze-portfolio")
def analyze_portfolio(payload: AnalyzePortfolioRequest, db: Session = Depends(get_db)) -> dict:
    if payload.portfolio_id is not None:
        target = payload.portfolio_id
    elif payload.items is not None:
        target = [item.model_dump() for item in payload.items]
    else:
        raise validation_error("Either portfolio_id or items must be provided.")

    result = ai_analysis_service.analyze_portfolio(db, target, question=payload.question)
    return ok(result)


@router.post("/explain-backtest")
def explain_backtest(payload: ExplainBacktestRequest) -> dict:
    result = ai_analysis_service.explain_backtest(payload.result, question=payload.question)
    return ok(result)


@router.post("/explain-projection")
def explain_projection(payload: ExplainProjectionRequest) -> dict:
    result = ai_analysis_service.explain_projection(payload.result, question=payload.question)
    return ok(result)
