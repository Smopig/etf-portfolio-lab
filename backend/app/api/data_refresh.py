"""One-click background data refresh (ETF list + prices)."""

from __future__ import annotations

from fastapi import APIRouter, Body

from app.api.responses import ok
from app.services import refresh_service

router = APIRouter(tags=["data-refresh"])


@router.post("/data/refresh")
def start_data_refresh(payload: dict | None = Body(default=None)) -> dict:
    payload = payload or {}
    opts = {
        "prices": payload.get("prices", True),
        "price_range": payload.get("range", "1y"),
        "limit": payload.get("limit"),
        "market": payload.get("market", "both"),
    }
    status, state = refresh_service.start_refresh(**opts)
    return ok({"status": status, **state})


@router.get("/data/refresh/status")
def get_data_refresh_status() -> dict:
    return ok(refresh_service.get_status())
