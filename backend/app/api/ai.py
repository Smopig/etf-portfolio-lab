"""AI analysis endpoints (Phase 13 placeholder).

Per CLAUDE.md §7, AI analysis must be grounded in system data with explicit
data sources/dates - these endpoints are stubs only and do NOT call any LLM.
They return a 501 NOT_IMPLEMENTED error until Phase 13 is built.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.responses import not_implemented

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/analyze-etf")
def analyze_etf() -> dict:
    raise not_implemented("AI ETF analysis is not implemented yet (Phase 13).")


@router.post("/analyze-portfolio")
def analyze_portfolio() -> dict:
    raise not_implemented("AI portfolio analysis is not implemented yet (Phase 13).")
