"""ETF overlap analysis: pairwise holding overlap, industry similarity, multi-overlap matrix."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import EtfHolding
from app.services.exposure_service import UNCLASSIFIED, get_industry_exposure
from app.utils.finance_math import normalize_weights_to_fraction

TOP_N = 10


def _latest_holding_date(session: Session, etf_symbol: str) -> dt.date | None:
    return (
        session.query(func.max(EtfHolding.holding_date))
        .filter(EtfHolding.etf_symbol == etf_symbol)
        .scalar()
    )


def _resolve_holding_date(
    session: Session, etf_symbol: str, holding_date: dt.date | None
) -> dt.date | None:
    if holding_date is not None:
        return holding_date
    return _latest_holding_date(session, etf_symbol)


def _load_normalized_holdings(
    session: Session, etf_symbol: str, holding_date: dt.date | None
) -> tuple[dt.date | None, dict[str, dict]]:
    """Return (resolved_date, {asset_symbol: {asset_name, weight_fraction}}), sorted by weight desc semantics via dict order."""
    resolved_date = _resolve_holding_date(session, etf_symbol, holding_date)
    if resolved_date is None:
        return None, {}

    holdings = (
        session.query(EtfHolding)
        .filter(
            EtfHolding.etf_symbol == etf_symbol,
            EtfHolding.holding_date == resolved_date,
        )
        .all()
    )
    if not holdings:
        return resolved_date, {}

    raw_weights = [float(h.weight) if h.weight is not None else 0.0 for h in holdings]
    fractions = normalize_weights_to_fraction(raw_weights)

    result: dict[str, dict] = {}
    for h, frac in zip(holdings, fractions):
        if not h.asset_symbol:
            continue
        result[h.asset_symbol] = {
            "asset_name": h.asset_name,
            "weight_fraction": frac,
        }
    return resolved_date, result


def _overlap_rating(weighted_overlap_fraction: float) -> dict:
    if weighted_overlap_fraction >= 0.7:
        label = "高度重疊"
    elif weighted_overlap_fraction >= 0.4:
        label = "中度重疊"
    elif weighted_overlap_fraction >= 0.2:
        label = "低度重疊"
    else:
        label = "極低重疊"
    return {"label": label, "value": weighted_overlap_fraction}


def _empty_pairwise_result(
    symbol_a: str,
    symbol_b: str,
    date_a: dt.date | None,
    date_b: dt.date | None,
) -> dict:
    return {
        "symbol_a": symbol_a,
        "symbol_b": symbol_b,
        "holding_date_a": date_a,
        "holding_date_b": date_b,
        "overlap_count": 0,
        "overlap_assets": [],
        "weighted_overlap_fraction": 0.0,
        "weighted_overlap_pct": 0.0,
        "overlap_rating": _overlap_rating(0.0),
        "jaccard": 0.0,
        "common_top10": [],
    }


def _pairwise_from_holdings(
    symbol_a: str,
    symbol_b: str,
    date_a: dt.date | None,
    date_b: dt.date | None,
    holdings_a: dict[str, dict],
    holdings_b: dict[str, dict],
) -> dict:
    if not holdings_a or not holdings_b:
        return _empty_pairwise_result(symbol_a, symbol_b, date_a, date_b)

    assets_a = set(holdings_a)
    assets_b = set(holdings_b)
    common = assets_a & assets_b
    union = assets_a | assets_b

    overlap_assets = []
    weighted_overlap_fraction = 0.0
    for sym in common:
        wa = holdings_a[sym]["weight_fraction"]
        wb = holdings_b[sym]["weight_fraction"]
        min_w = min(wa, wb)
        weighted_overlap_fraction += min_w
        overlap_assets.append(
            {
                "asset_symbol": sym,
                "asset_name": holdings_a[sym]["asset_name"] or holdings_b[sym]["asset_name"],
                "weight_a_pct": wa * 100,
                "weight_b_pct": wb * 100,
                "min_weight_pct": min_w * 100,
            }
        )
    overlap_assets.sort(key=lambda x: x["min_weight_pct"], reverse=True)

    jaccard = (len(common) / len(union)) if union else 0.0

    top10_a = set(
        sorted(holdings_a, key=lambda s: holdings_a[s]["weight_fraction"], reverse=True)[:TOP_N]
    )
    top10_b = set(
        sorted(holdings_b, key=lambda s: holdings_b[s]["weight_fraction"], reverse=True)[:TOP_N]
    )
    common_top10_symbols = top10_a & top10_b
    common_top10 = [a for a in overlap_assets if a["asset_symbol"] in common_top10_symbols]

    return {
        "symbol_a": symbol_a,
        "symbol_b": symbol_b,
        "holding_date_a": date_a,
        "holding_date_b": date_b,
        "overlap_count": len(common),
        "overlap_assets": overlap_assets,
        "weighted_overlap_fraction": weighted_overlap_fraction,
        "weighted_overlap_pct": weighted_overlap_fraction * 100,
        "overlap_rating": _overlap_rating(weighted_overlap_fraction),
        "jaccard": jaccard,
        "common_top10": common_top10,
    }


def get_pairwise_overlap(
    session: Session,
    symbol_a: str,
    symbol_b: str,
    date_a: dt.date | None = None,
    date_b: dt.date | None = None,
) -> dict:
    resolved_a, holdings_a = _load_normalized_holdings(session, symbol_a, date_a)
    resolved_b, holdings_b = _load_normalized_holdings(session, symbol_b, date_b)
    return _pairwise_from_holdings(symbol_a, symbol_b, resolved_a, resolved_b, holdings_a, holdings_b)


def get_industry_similarity(
    session: Session,
    symbol_a: str,
    symbol_b: str,
    date_a: dt.date | None = None,
    date_b: dt.date | None = None,
    level: int = 1,
) -> dict:
    exposure_a = get_industry_exposure(session, symbol_a, date_a, level)
    exposure_b = get_industry_exposure(session, symbol_b, date_b, level)

    def to_map(exposure: dict) -> dict[str, float]:
        m = {i["industry"]: i["weight_fraction"] for i in exposure["industries"]}
        m[UNCLASSIFIED] = exposure["unclassified"]["weight_fraction"]
        return m

    map_a = to_map(exposure_a)
    map_b = to_map(exposure_b)

    industries = set(map_a) | set(map_b)
    breakdown = []
    similarity_fraction = 0.0
    for industry in industries:
        wa = map_a.get(industry, 0.0)
        wb = map_b.get(industry, 0.0)
        min_w = min(wa, wb)
        similarity_fraction += min_w
        breakdown.append(
            {
                "industry": industry,
                "weight_a_pct": wa * 100,
                "weight_b_pct": wb * 100,
                "min_weight_pct": min_w * 100,
            }
        )
    breakdown.sort(key=lambda x: x["min_weight_pct"], reverse=True)

    return {
        "symbol_a": symbol_a,
        "symbol_b": symbol_b,
        "holding_date_a": exposure_a["holding_date"],
        "holding_date_b": exposure_b["holding_date"],
        "level": level,
        "industry_similarity_fraction": similarity_fraction,
        "industry_similarity_pct": similarity_fraction * 100,
        "breakdown": breakdown,
    }


def get_multi_overlap(
    session: Session,
    symbols: list[str],
    date_map: dict[str, dt.date] | None = None,
) -> dict:
    date_map = date_map or {}
    n = len(symbols)

    if n == 0:
        return {"symbols": [], "matrix": [], "pairs": []}

    holdings_cache: dict[str, tuple[dt.date | None, dict[str, dict]]] = {}
    for sym in symbols:
        holdings_cache[sym] = _load_normalized_holdings(session, sym, date_map.get(sym))

    pair_cache: dict[tuple[str, str], dict] = {}
    matrix: list[list[float]] = [[0.0] * n for _ in range(n)]

    for i in range(n):
        matrix[i][i] = 100.0

    pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            sym_i, sym_j = symbols[i], symbols[j]
            date_i, holdings_i = holdings_cache[sym_i]
            date_j, holdings_j = holdings_cache[sym_j]
            result = _pairwise_from_holdings(
                sym_i, sym_j, date_i, date_j, holdings_i, holdings_j
            )
            pair_cache[(sym_i, sym_j)] = result
            matrix[i][j] = result["weighted_overlap_pct"]
            matrix[j][i] = result["weighted_overlap_pct"]
            pairs.append(
                {
                    "a": sym_i,
                    "b": sym_j,
                    "weighted_overlap_pct": result["weighted_overlap_pct"],
                    "overlap_count": result["overlap_count"],
                }
            )

    return {"symbols": symbols, "matrix": matrix, "pairs": pairs}
