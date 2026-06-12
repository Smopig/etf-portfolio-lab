"""Dashboard summary and cross-ETF ranking aggregations."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import DataQualityCheck, EtfHolding, EtfMaster, EtfPrice
from app.services.concentration_service import get_concentration
from app.services.exposure_service import get_industry_exposure

WARN_FAIL_STATUSES = ("WARN", "FAIL")

RANKING_METRICS = (
    "hhi",
    "effective_holdings",
    "top1",
    "top10",
    "num_holdings",
    "industry_concentration",
    "industry_diversification",
    "industry_exposure",
)


def get_dashboard_summary(session: Session) -> dict:
    """Return high-level data availability counts for the dashboard.

    {
      total_etfs, active_etfs,
      etfs_with_holdings, etfs_with_prices,
      last_updated, recent_quality_warnings,
    }
    """
    total_etfs = session.query(func.count(EtfMaster.id)).scalar() or 0
    active_etfs = (
        session.query(func.count(EtfMaster.id)).filter(EtfMaster.is_active.is_(True)).scalar()
        or 0
    )

    etfs_with_holdings = (
        session.query(func.count(func.distinct(EtfHolding.etf_symbol))).scalar() or 0
    )
    etfs_with_prices = (
        session.query(func.count(func.distinct(EtfPrice.etf_symbol))).scalar() or 0
    )

    last_updated = session.query(func.max(DataQualityCheck.checked_at)).scalar()

    recent_quality_warnings = (
        session.query(func.count(DataQualityCheck.id))
        .filter(DataQualityCheck.status.in_(WARN_FAIL_STATUSES))
        .scalar()
        or 0
    )

    return {
        "total_etfs": total_etfs,
        "active_etfs": active_etfs,
        "etfs_with_holdings": etfs_with_holdings,
        "etfs_with_prices": etfs_with_prices,
        "last_updated": last_updated,
        "recent_quality_warnings": recent_quality_warnings,
    }


def get_holdings_and_price_symbol_sets(session: Session) -> tuple[set[str], set[str]]:
    """Return (symbols_with_holdings, symbols_with_prices) as sets, single query each."""
    holdings_symbols = {
        row[0] for row in session.query(func.distinct(EtfHolding.etf_symbol)).all()
    }
    price_symbols = {row[0] for row in session.query(func.distinct(EtfPrice.etf_symbol)).all()}
    return holdings_symbols, price_symbols


def _etf_symbols_with_holdings(session: Session) -> list[str]:
    return [row[0] for row in session.query(func.distinct(EtfHolding.etf_symbol)).all()]


def rank_etfs(
    session: Session,
    metric: str,
    order: str = "desc",
    limit: int = 10,
    industry: str | None = None,
    level: int = 1,
) -> list[dict]:
    """Rank ETFs by a concentration/exposure metric.

    Concentration metrics (hhi, effective_holdings, top1, top10, num_holdings):
        computed via concentration_service.get_concentration on each ETF's
        latest holdings.

    industry_concentration / industry_diversification:
        both use the ETF's max_industry weight (the single largest industry
        share). "concentration" sorts this value descending by default
        (most concentrated first); "diversification" sorts the same value
        ascending by default (lowest max-industry share = most diversified).
        Callers may override via `order`.

    industry_exposure:
        requires `industry`; ranks ETFs by their weight_fraction in that
        specific industry at the given `level`.

    ETFs with no holdings are skipped.
    """
    if metric not in RANKING_METRICS:
        raise ValueError(f"Unknown ranking metric: {metric}")
    if metric == "industry_exposure" and not industry:
        raise ValueError("industry parameter is required for metric=industry_exposure")

    descending = order != "asc"

    name_map = {
        row[0]: row[1] for row in session.query(EtfMaster.symbol, EtfMaster.name).all()
    }

    symbols = _etf_symbols_with_holdings(session)

    results: list[dict] = []
    for symbol in symbols:
        if metric in ("hhi", "effective_holdings", "top1", "top10", "num_holdings"):
            concentration = get_concentration(session, symbol)
            if concentration["holding_date"] is None:
                continue
            if metric == "top1":
                value = concentration["top1_fraction"]
            elif metric == "top10":
                value = concentration["top10_fraction"]
            else:
                value = concentration[metric]
            if value is None:
                continue
            results.append(
                {
                    "etf_symbol": symbol,
                    "name": name_map.get(symbol),
                    "value": value,
                    "holding_date": concentration["holding_date"],
                    "num_holdings": concentration["num_holdings"],
                }
            )
        elif metric in ("industry_concentration", "industry_diversification"):
            exposure = get_industry_exposure(session, symbol, level=level)
            if exposure["holding_date"] is None or exposure["max_industry"] is None:
                continue
            value = exposure["max_industry"]["weight_fraction"]
            results.append(
                {
                    "etf_symbol": symbol,
                    "name": name_map.get(symbol),
                    "value": value,
                    "holding_date": exposure["holding_date"],
                    "max_industry": exposure["max_industry"]["industry"],
                    "level": level,
                }
            )
        elif metric == "industry_exposure":
            exposure = get_industry_exposure(session, symbol, level=level)
            if exposure["holding_date"] is None:
                continue
            entry = next(
                (i for i in exposure["industries"] if i["industry"] == industry), None
            )
            value = entry["weight_fraction"] if entry else 0.0
            results.append(
                {
                    "etf_symbol": symbol,
                    "name": name_map.get(symbol),
                    "value": value,
                    "holding_date": exposure["holding_date"],
                    "industry": industry,
                    "level": level,
                }
            )

    # Default sort direction for industry_diversification: ascending (lowest
    # max-industry share = most diversified), unless caller overrides order.
    if metric == "industry_diversification" and order == "desc":
        descending = False

    results.sort(key=lambda r: r["value"], reverse=descending)
    return results[:limit]
