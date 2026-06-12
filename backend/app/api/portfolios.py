"""Portfolio CRUD + look-through analysis endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.responses import not_found, ok
from app.core.database import get_db
from app.schemas.portfolio import PortfolioAnalyzeRequest, PortfolioCreate, PortfolioUpdate
from app.services.portfolio_service import (
    create_portfolio,
    delete_portfolio,
    get_look_through_industry_exposure,
    get_look_through_stock_exposure,
    get_portfolio,
    get_portfolio_concentration,
    get_portfolio_overlap_risk,
    get_portfolio_warnings,
    list_portfolios,
    update_portfolio,
    validate_weights,
)

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


@router.post("")
def create(payload: PortfolioCreate, db: Session = Depends(get_db)) -> dict:
    data = create_portfolio(
        db,
        name=payload.name,
        items=[item.model_dump() for item in payload.items],
        description=payload.description,
        base_currency=payload.base_currency,
    )
    return ok(data)


@router.get("")
def list_all(db: Session = Depends(get_db)) -> dict:
    return ok(list_portfolios(db))


@router.post("/analyze")
def analyze(payload: PortfolioAnalyzeRequest, db: Session = Depends(get_db)) -> dict:
    items = [item.model_dump() for item in payload.items]
    return ok(
        {
            "validation": validate_weights(db, items),
            "stock_exposure": get_look_through_stock_exposure(db, items),
            "industry_exposure": get_look_through_industry_exposure(db, items),
            "concentration": get_portfolio_concentration(db, items),
            "warnings": get_portfolio_warnings(db, items),
        }
    )


@router.get("/{portfolio_id}")
def get_one(portfolio_id: int, db: Session = Depends(get_db)) -> dict:
    data = get_portfolio(db, portfolio_id)
    if data is None:
        raise not_found(f"Portfolio {portfolio_id} not found.")
    return ok(data)


@router.put("/{portfolio_id}")
def update(portfolio_id: int, payload: PortfolioUpdate, db: Session = Depends(get_db)) -> dict:
    existing = get_portfolio(db, portfolio_id)
    if existing is None:
        raise not_found(f"Portfolio {portfolio_id} not found.")
    items = (
        [item.model_dump() for item in payload.items] if payload.items is not None else None
    )
    data = update_portfolio(
        db,
        portfolio_id,
        name=payload.name,
        description=payload.description,
        base_currency=payload.base_currency,
        items=items,
    )
    return ok(data)


@router.delete("/{portfolio_id}")
def delete(portfolio_id: int, db: Session = Depends(get_db)) -> dict:
    existing = get_portfolio(db, portfolio_id)
    if existing is None:
        raise not_found(f"Portfolio {portfolio_id} not found.")
    delete_portfolio(db, portfolio_id)
    return ok({"deleted": True, "id": portfolio_id})


@router.get("/{portfolio_id}/exposure")
def exposure(
    portfolio_id: int,
    level: int = Query(default=1, ge=1, le=2),
    db: Session = Depends(get_db),
) -> dict:
    existing = get_portfolio(db, portfolio_id)
    if existing is None:
        raise not_found(f"Portfolio {portfolio_id} not found.")
    return ok(
        {
            "stock_exposure": get_look_through_stock_exposure(db, portfolio_id),
            "industry_exposure": get_look_through_industry_exposure(
                db, portfolio_id, level=level
            ),
        }
    )


@router.get("/{portfolio_id}/concentration")
def concentration(portfolio_id: int, db: Session = Depends(get_db)) -> dict:
    existing = get_portfolio(db, portfolio_id)
    if existing is None:
        raise not_found(f"Portfolio {portfolio_id} not found.")
    return ok(get_portfolio_concentration(db, portfolio_id))


@router.get("/{portfolio_id}/overlap-risk")
def overlap_risk(portfolio_id: int, db: Session = Depends(get_db)) -> dict:
    existing = get_portfolio(db, portfolio_id)
    if existing is None:
        raise not_found(f"Portfolio {portfolio_id} not found.")
    return ok(get_portfolio_overlap_risk(db, portfolio_id))


@router.get("/{portfolio_id}/warnings")
def warnings(portfolio_id: int, db: Session = Depends(get_db)) -> dict:
    existing = get_portfolio(db, portfolio_id)
    if existing is None:
        raise not_found(f"Portfolio {portfolio_id} not found.")
    return ok(get_portfolio_warnings(db, portfolio_id))
