"""Pydantic v2 request schemas for portfolio endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PortfolioItemIn(BaseModel):
    etf_symbol: str
    target_weight: float


class PortfolioCreate(BaseModel):
    name: str
    description: str | None = None
    base_currency: str = "TWD"
    items: list[PortfolioItemIn] = Field(default_factory=list)


class PortfolioUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    base_currency: str | None = None
    items: list[PortfolioItemIn] | None = None


class PortfolioAnalyzeRequest(BaseModel):
    items: list[PortfolioItemIn]
