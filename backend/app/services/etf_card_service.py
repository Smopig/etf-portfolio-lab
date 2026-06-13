"""Compact "ETF strategy card" combining master data + concentration + exposure."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import EtfMaster
from app.services.concentration_service import get_concentration
from app.services.exposure_service import get_industry_exposure


def get_etf_card(session: Session, etf_symbol: str) -> dict | None:
    """Assemble a compact ETF card from DB data only.

    Returns None if no EtfMaster row exists for ``etf_symbol``.
    Includes data provenance (source_name, data_date, confidence_level)
    so downstream UI/AI layers always have source + date (CLAUDE.md §7).
    Does not invent any values — nulls are returned where data is absent.
    """
    master = (
        session.query(EtfMaster).filter(EtfMaster.symbol == etf_symbol).first()
    )
    if master is None:
        return None

    concentration = get_concentration(session, etf_symbol)
    exposure = get_industry_exposure(session, etf_symbol, level=1)

    return {
        "symbol": master.symbol,
        "name": master.name,
        "issuer": master.issuer,
        "management_type": master.management_type,
        "asset_class": master.asset_class,
        "investment_style": master.investment_style,
        "strategy_type": master.strategy_type,
        "tracking_index": master.tracking_index,
        "index_provider": master.index_provider,
        "expense_ratio": float(master.expense_ratio)
        if master.expense_ratio is not None
        else None,
        "management_fee": float(master.management_fee)
        if master.management_fee is not None
        else None,
        "custody_fee": float(master.custody_fee)
        if master.custody_fee is not None
        else None,
        "dividend_frequency": master.dividend_frequency,
        "concentration": {
            "holding_date": concentration["holding_date"],
            "num_holdings": concentration["num_holdings"],
            "top1_pct": concentration["top1_pct"],
            "top3_pct": concentration["top3_pct"],
            "top5_pct": concentration["top5_pct"],
            "top10_pct": concentration["top10_pct"],
            "hhi": concentration["hhi"],
            "effective_holdings": concentration["effective_holdings"],
        },
        "top3_industries": exposure["top3_industries"],
        "data_provenance": {
            "source_name": master.source_name,
            "source_url": master.source_url,
            "data_date": master.data_date,
            "fetched_at": master.fetched_at,
            "confidence_level": master.confidence_level,
        },
    }
