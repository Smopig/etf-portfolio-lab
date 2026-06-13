"""Portfolio Builder: CRUD persistence + look-through (穿透) analysis.

NOTE (CLAUDE.md §7): All analysis here is research-only, based on system
data with explicit data dates. No buy/sell advice, no future guarantees.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import EtfHolding, EtfMaster, Portfolio, PortfolioItem, StockIndustry
from app.services.exposure_service import UNCLASSIFIED, _industry_level_attr
from app.services.overlap_service import get_multi_overlap
from app.utils.finance_math import (
    effective_holdings,
    hhi,
    normalize_weights_to_fraction,
    top_n_weight,
)

DISCLAIMER = (
    "本分析僅供研究參考，依系統現有資料計算，不代表未來績效，"
    "亦非投資買賣建議。"
)

SINGLE_STOCK_WARN_THRESHOLD = 0.30
HHI_WARN_THRESHOLD = 0.15  # roughly < ~7 effective holdings
OVERLAP_WARN_THRESHOLD_PCT = 60.0
UNCLASSIFIED_WARN_THRESHOLD = 0.30


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def _portfolio_to_dict(portfolio: Portfolio, items: list[PortfolioItem]) -> dict:
    return {
        "id": portfolio.id,
        "name": portfolio.name,
        "description": portfolio.description,
        "base_currency": portfolio.base_currency,
        "items": [
            {
                "id": item.id,
                "etf_symbol": item.etf_symbol,
                "target_weight": float(item.target_weight),
            }
            for item in items
        ],
        "created_at": portfolio.created_at,
        "updated_at": portfolio.updated_at,
    }


def create_portfolio(
    session: Session,
    name: str,
    items: list[dict],
    description: str | None = None,
    base_currency: str = "TWD",
) -> dict:
    portfolio = Portfolio(name=name, description=description, base_currency=base_currency)
    session.add(portfolio)
    session.flush()

    item_rows = []
    for item in items:
        row = PortfolioItem(
            portfolio_id=portfolio.id,
            etf_symbol=item["etf_symbol"],
            target_weight=item["target_weight"],
        )
        session.add(row)
        item_rows.append(row)

    session.commit()
    return _portfolio_to_dict(portfolio, item_rows)


def get_portfolio(session: Session, portfolio_id: int) -> dict | None:
    portfolio = session.get(Portfolio, portfolio_id)
    if portfolio is None:
        return None
    items = (
        session.query(PortfolioItem)
        .filter(PortfolioItem.portfolio_id == portfolio_id)
        .all()
    )
    return _portfolio_to_dict(portfolio, items)


def list_portfolios(session: Session) -> list[dict]:
    portfolios = session.query(Portfolio).order_by(Portfolio.id).all()
    result = []
    for portfolio in portfolios:
        items = (
            session.query(PortfolioItem)
            .filter(PortfolioItem.portfolio_id == portfolio.id)
            .all()
        )
        result.append(_portfolio_to_dict(portfolio, items))
    return result


def update_portfolio(
    session: Session,
    portfolio_id: int,
    name: str | None = None,
    description: str | None = None,
    base_currency: str | None = None,
    items: list[dict] | None = None,
) -> dict | None:
    portfolio = session.get(Portfolio, portfolio_id)
    if portfolio is None:
        return None

    if name is not None:
        portfolio.name = name
    if description is not None:
        portfolio.description = description
    if base_currency is not None:
        portfolio.base_currency = base_currency
    portfolio.updated_at = dt.datetime.utcnow()

    if items is not None:
        session.query(PortfolioItem).filter(
            PortfolioItem.portfolio_id == portfolio_id
        ).delete()
        for item in items:
            session.add(
                PortfolioItem(
                    portfolio_id=portfolio_id,
                    etf_symbol=item["etf_symbol"],
                    target_weight=item["target_weight"],
                )
            )

    session.commit()
    return get_portfolio(session, portfolio_id)


def delete_portfolio(session: Session, portfolio_id: int) -> bool:
    portfolio = session.get(Portfolio, portfolio_id)
    if portfolio is None:
        return False
    session.query(PortfolioItem).filter(
        PortfolioItem.portfolio_id == portfolio_id
    ).delete()
    session.delete(portfolio)
    session.commit()
    return True


# ---------------------------------------------------------------------------
# Internal resolver: accept either a persisted portfolio_id (int) or an
# ad-hoc items list, both as [{etf_symbol, target_weight}, ...].
# ---------------------------------------------------------------------------

def _resolve_items(session: Session, portfolio_id_or_items) -> list[dict]:
    if isinstance(portfolio_id_or_items, int):
        portfolio = get_portfolio(session, portfolio_id_or_items)
        if portfolio is None:
            return []
        return [
            {"etf_symbol": i["etf_symbol"], "target_weight": i["target_weight"]}
            for i in portfolio["items"]
        ]
    return [
        {"etf_symbol": i["etf_symbol"], "target_weight": float(i["target_weight"])}
        for i in portfolio_id_or_items
    ]


def _latest_holding_date(session: Session, etf_symbol: str) -> dt.date | None:
    return (
        session.query(func.max(EtfHolding.holding_date))
        .filter(EtfHolding.etf_symbol == etf_symbol)
        .scalar()
    )


def _load_etf_holdings_fractions(
    session: Session,
    etf_symbol: str,
    holding_date: dt.date | None = None,
) -> tuple[dt.date | None, list[tuple[str, str | None, float]]]:
    """Return (resolved_date, [(asset_symbol, asset_name, weight_fraction), ...])."""
    resolved_date = holding_date or _latest_holding_date(session, etf_symbol)
    if resolved_date is None:
        return None, []

    holdings = (
        session.query(EtfHolding)
        .filter(
            EtfHolding.etf_symbol == etf_symbol,
            EtfHolding.holding_date == resolved_date,
        )
        .all()
    )
    if not holdings:
        return resolved_date, []

    raw_weights = [float(h.weight) if h.weight is not None else 0.0 for h in holdings]
    fractions = normalize_weights_to_fraction(raw_weights)

    return resolved_date, [
        (h.asset_symbol, h.asset_name, frac)
        for h, frac in zip(holdings, fractions)
        if h.asset_symbol
    ]


def _normalized_etf_weights(items: list[dict]) -> dict[str, float]:
    """Normalize ETF target_weight values across the portfolio to fractions
    summing to 1 (deduped by etf_symbol, last one wins for duplicates)."""
    if not items:
        return {}
    raw_weights = [float(i["target_weight"]) for i in items]
    fractions = normalize_weights_to_fraction(raw_weights)
    total = sum(fractions)
    if total <= 0:
        return {}

    weight_map: dict[str, float] = {}
    for item, frac in zip(items, fractions):
        weight_map[item["etf_symbol"]] = weight_map.get(item["etf_symbol"], 0.0) + (
            frac / total
        )
    return weight_map


# ---------------------------------------------------------------------------
# 3. validate_weights
# ---------------------------------------------------------------------------

def validate_weights(session: Session, portfolio_id_or_items) -> dict:
    items = _resolve_items(session, portfolio_id_or_items)

    if not items:
        return {
            "status": "FAIL",
            "weight_sum_pct": 0.0,
            "message": "配置方案沒有任何 ETF 項目。",
            "duplicate_symbols": [],
            "unknown_symbols": [],
        }

    raw_weights = [float(i["target_weight"]) for i in items]
    fractions = normalize_weights_to_fraction(raw_weights)
    weight_sum_pct = sum(fractions) * 100

    if 99.0 <= weight_sum_pct <= 101.0:
        status = "PASS"
        message = f"權重總和為 {weight_sum_pct:.2f}%，符合 100% 容許範圍。"
    elif 95.0 <= weight_sum_pct <= 105.0:
        status = "WARN"
        message = f"權重總和為 {weight_sum_pct:.2f}%，建議調整為 100%。"
    else:
        status = "FAIL"
        message = f"權重總和為 {weight_sum_pct:.2f}%，與 100% 差異過大，請重新檢查配置。"

    symbols = [i["etf_symbol"] for i in items]
    seen: set[str] = set()
    duplicate_symbols: list[str] = []
    for sym in symbols:
        if sym in seen and sym not in duplicate_symbols:
            duplicate_symbols.append(sym)
        seen.add(sym)

    unknown_symbols: list[str] = []
    if symbols:
        known_rows = (
            session.query(EtfMaster.symbol)
            .filter(EtfMaster.symbol.in_(set(symbols)))
            .all()
        )
        known = {row[0] for row in known_rows}
        unknown_symbols = sorted({s for s in symbols if s not in known})

    if duplicate_symbols and status == "PASS":
        status = "WARN"
        message += f" 注意：重複的 ETF 代號 {', '.join(duplicate_symbols)}。"

    if unknown_symbols and status == "PASS":
        status = "WARN"
        message += f" 注意：未知的 ETF 代號 {', '.join(unknown_symbols)}。"

    return {
        "status": status,
        "weight_sum_pct": weight_sum_pct,
        "message": message,
        "duplicate_symbols": duplicate_symbols,
        "unknown_symbols": unknown_symbols,
    }


# ---------------------------------------------------------------------------
# 4. get_look_through_stock_exposure
# ---------------------------------------------------------------------------

def get_look_through_stock_exposure(
    session: Session,
    portfolio_id_or_items,
    holding_date_map: dict[str, dt.date] | None = None,
) -> dict:
    items = _resolve_items(session, portfolio_id_or_items)
    holding_date_map = holding_date_map or {}

    etf_weights = _normalized_etf_weights(items)

    stock_weights: dict[str, float] = {}
    stock_names: dict[str, str] = {}
    holding_dates: dict[str, dt.date | None] = {}
    missing_holdings: list[str] = []

    for etf_symbol, etf_weight in etf_weights.items():
        resolved_date, holdings = _load_etf_holdings_fractions(
            session, etf_symbol, holding_date_map.get(etf_symbol)
        )
        holding_dates[etf_symbol] = resolved_date
        if not holdings:
            missing_holdings.append(etf_symbol)
            continue
        for asset_symbol, asset_name, frac in holdings:
            contribution = etf_weight * frac
            stock_weights[asset_symbol] = stock_weights.get(asset_symbol, 0.0) + contribution
            if asset_symbol not in stock_names and asset_name:
                stock_names[asset_symbol] = asset_name

    stocks = [
        {
            "asset_symbol": symbol,
            "asset_name": stock_names.get(symbol),
            "weight_fraction": weight,
            "weight_pct": weight * 100,
        }
        for symbol, weight in stock_weights.items()
    ]
    stocks.sort(key=lambda x: x["weight_fraction"], reverse=True)

    total_fraction = sum(s["weight_fraction"] for s in stocks)
    hhi_value = hhi([s["weight_fraction"] for s in stocks])

    return {
        "stocks": stocks,
        "num_stocks": len(stocks),
        "num_effective": effective_holdings(hhi_value),
        "total_weight_fraction": total_fraction,
        "etf_weights": etf_weights,
        "holding_dates": holding_dates,
        "missing_holdings": missing_holdings,
    }


# ---------------------------------------------------------------------------
# 5. get_look_through_industry_exposure
# ---------------------------------------------------------------------------

def get_look_through_industry_exposure(
    session: Session,
    portfolio_id_or_items,
    holding_date_map: dict[str, dt.date] | None = None,
    level: int = 1,
) -> dict:
    stock_exposure = get_look_through_stock_exposure(
        session, portfolio_id_or_items, holding_date_map
    )
    stocks = stock_exposure["stocks"]

    asset_symbols = {s["asset_symbol"] for s in stocks if s["asset_symbol"]}
    industry_attr = _industry_level_attr(level)
    industry_map: dict[str, str | None] = {}
    if asset_symbols:
        rows = (
            session.query(StockIndustry.stock_symbol, industry_attr)
            .filter(StockIndustry.stock_symbol.in_(asset_symbols))
            .all()
        )
        industry_map = {symbol: industry for symbol, industry in rows}

    totals: dict[str, float] = {}
    for s in stocks:
        industry = industry_map.get(s["asset_symbol"]) if s["asset_symbol"] else None
        key = industry if industry else UNCLASSIFIED
        totals[key] = totals.get(key, 0.0) + s["weight_fraction"]

    industries = [
        {"industry": k, "weight_fraction": v, "weight_pct": v * 100}
        for k, v in totals.items()
        if k != UNCLASSIFIED
    ]
    industries.sort(key=lambda x: x["weight_fraction"], reverse=True)

    unclassified_fraction = totals.get(UNCLASSIFIED, 0.0)
    unclassified = {
        "industry": UNCLASSIFIED,
        "weight_fraction": unclassified_fraction,
        "weight_pct": unclassified_fraction * 100,
    }

    return {
        "level": level,
        "industries": industries,
        "max_industry": industries[0] if industries else None,
        "top3_industries": industries[:3],
        "unclassified": unclassified,
    }


# ---------------------------------------------------------------------------
# 6. get_portfolio_concentration
# ---------------------------------------------------------------------------

def get_portfolio_concentration(session: Session, portfolio_id_or_items) -> dict:
    stock_exposure = get_look_through_stock_exposure(session, portfolio_id_or_items)
    weights = [s["weight_fraction"] for s in stock_exposure["stocks"]]

    hhi_value = hhi(weights)

    return {
        "hhi": hhi_value,
        "effective_holdings": effective_holdings(hhi_value),
        "num_stocks": len(weights),
        "top1_pct": top_n_weight(weights, 1) * 100,
        "top3_pct": top_n_weight(weights, 3) * 100,
        "top5_pct": top_n_weight(weights, 5) * 100,
        "top10_pct": top_n_weight(weights, 10) * 100,
    }


# ---------------------------------------------------------------------------
# 7. get_portfolio_overlap_risk
# ---------------------------------------------------------------------------

def get_portfolio_overlap_risk(session: Session, portfolio_id_or_items) -> dict:
    items = _resolve_items(session, portfolio_id_or_items)
    etf_weights = _normalized_etf_weights(items)
    symbols = list(etf_weights.keys())

    if len(symbols) < 2:
        return {
            "symbols": symbols,
            "matrix": [],
            "pairs": [],
            "top_overlapping_pairs": [],
            "note": "組合內 ETF 少於兩個，無法計算重疊風險。",
        }

    multi = get_multi_overlap(session, symbols)
    pairs = sorted(
        multi["pairs"], key=lambda p: p["weighted_overlap_pct"], reverse=True
    )
    top_pairs = pairs[:3]

    if top_pairs and top_pairs[0]["weighted_overlap_pct"] >= OVERLAP_WARN_THRESHOLD_PCT:
        note = (
            f"ETF {top_pairs[0]['a']} 與 {top_pairs[0]['b']} 的重疊度達 "
            f"{top_pairs[0]['weighted_overlap_pct']:.1f}%，配置可能存在重複曝險。"
        )
    else:
        note = "目前組合內 ETF 之間重疊度未達高風險門檻。"

    return {
        "symbols": multi["symbols"],
        "matrix": multi["matrix"],
        "pairs": pairs,
        "top_overlapping_pairs": top_pairs,
        "note": note,
    }


# ---------------------------------------------------------------------------
# 8. get_portfolio_warnings
# ---------------------------------------------------------------------------

def get_portfolio_warnings(
    session: Session,
    portfolio_id_or_items,
    single_stock_threshold: float = SINGLE_STOCK_WARN_THRESHOLD,
) -> dict:
    warnings: list[dict] = []

    validation = validate_weights(session, portfolio_id_or_items)
    if validation["status"] != "PASS":
        warnings.append(
            {
                "code": "WEIGHT_SUM",
                "severity": "WARN" if validation["status"] == "WARN" else "ERROR",
                "message": validation["message"],
            }
        )
    if validation["duplicate_symbols"]:
        warnings.append(
            {
                "code": "DUPLICATE_ETF",
                "severity": "WARN",
                "message": f"重複的 ETF 代號：{', '.join(validation['duplicate_symbols'])}。",
            }
        )
    if validation["unknown_symbols"]:
        warnings.append(
            {
                "code": "UNKNOWN_ETF",
                "severity": "WARN",
                "message": f"找不到 ETF 主檔資料：{', '.join(validation['unknown_symbols'])}。",
            }
        )

    stock_exposure = get_look_through_stock_exposure(session, portfolio_id_or_items)
    for s in stock_exposure["stocks"]:
        if s["weight_fraction"] > single_stock_threshold:
            warnings.append(
                {
                    "code": "SINGLE_STOCK_CONCENTRATION",
                    "severity": "WARN",
                    "message": (
                        f"個股 {s['asset_name'] or s['asset_symbol']} "
                        f"({s['asset_symbol']}) 穿透後權重達 "
                        f"{s['weight_pct']:.1f}%，超過 "
                        f"{single_stock_threshold * 100:.0f}% 門檻，集中度偏高。"
                    ),
                }
            )

    if stock_exposure["missing_holdings"]:
        warnings.append(
            {
                "code": "MISSING_HOLDINGS",
                "severity": "WARN",
                "message": (
                    f"以下 ETF 缺少成分股資料，未納入穿透分析："
                    f"{', '.join(stock_exposure['missing_holdings'])}。"
                ),
            }
        )

    concentration = get_portfolio_concentration(session, portfolio_id_or_items)
    if concentration["hhi"] > HHI_WARN_THRESHOLD:
        eff = concentration["effective_holdings"]
        eff_str = f"{eff:.1f}" if eff else "0"
        warnings.append(
            {
                "code": "HIGH_HHI",
                "severity": "WARN",
                "message": (
                    f"組合穿透後 HHI 為 {concentration['hhi']:.3f}"
                    f"（有效持股數約 {eff_str}），集中度偏高。"
                ),
            }
        )

    overlap = get_portfolio_overlap_risk(session, portfolio_id_or_items)
    if overlap["top_overlapping_pairs"]:
        top = overlap["top_overlapping_pairs"][0]
        if top["weighted_overlap_pct"] >= OVERLAP_WARN_THRESHOLD_PCT:
            warnings.append(
                {
                    "code": "HIGH_ETF_OVERLAP",
                    "severity": "WARN",
                    "message": (
                        f"ETF {top['a']} 與 {top['b']} 重疊度達 "
                        f"{top['weighted_overlap_pct']:.1f}%，可能造成重複曝險。"
                    ),
                }
            )

    industry_exposure = get_look_through_industry_exposure(session, portfolio_id_or_items)
    unclassified_fraction = industry_exposure["unclassified"]["weight_fraction"]
    if unclassified_fraction > UNCLASSIFIED_WARN_THRESHOLD:
        warnings.append(
            {
                "code": "HIGH_UNCLASSIFIED",
                "severity": "WARN",
                "message": (
                    f"穿透後有 {unclassified_fraction * 100:.1f}% 的資產"
                    "缺乏產業分類資料，產業曝險分析可能不完整。"
                ),
            }
        )

    return {
        "warnings": warnings,
        "warning_count": len(warnings),
        "disclaimer": DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# 9. compare_portfolios
# ---------------------------------------------------------------------------

def compare_portfolios(session: Session, ids_or_item_lists: list) -> dict:
    comparisons = []
    for ref in ids_or_item_lists:
        items = _resolve_items(session, ref)
        concentration = get_portfolio_concentration(session, ref)
        industry_exposure = get_look_through_industry_exposure(session, ref)
        stock_exposure = get_look_through_stock_exposure(session, ref)
        warnings = get_portfolio_warnings(session, ref)

        label = ref if isinstance(ref, int) else "(draft)"

        comparisons.append(
            {
                "portfolio_id": ref if isinstance(ref, int) else None,
                "label": label,
                "etf_symbols": [i["etf_symbol"] for i in items],
                "concentration": concentration,
                "top_industries": industry_exposure["top3_industries"],
                "unclassified_pct": industry_exposure["unclassified"]["weight_pct"],
                "top_stocks": stock_exposure["stocks"][:5],
                "warning_count": warnings["warning_count"],
                "warnings": warnings["warnings"],
            }
        )

    return {
        "portfolios": comparisons,
        "disclaimer": DISCLAIMER,
    }
