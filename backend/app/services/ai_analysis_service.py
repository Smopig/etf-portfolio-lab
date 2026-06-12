"""AI analysis service (Phase 13).

Builds structured context dictionaries from existing system services and
hands them to an AI provider (default: mock, see CLAUDE.md §7). The AI is
never allowed to invent ETF holdings, industry weights, or give buy/sell
advice - it must only describe the data it is given, cite the data
source/date, and repeat the standard disclaimers.
"""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.providers.ai.base import AIResult
from app.providers.ai.factory import get_ai_provider
from app.services import portfolio_service
from app.services.concentration_service import get_top_holdings
from app.services.etf_card_service import get_etf_card
from app.services.exposure_service import get_industry_exposure

DISCLAIMER = (
    "本分析僅基於系統現有資料提供研究與風險提醒，不構成買賣建議；"
    "回測與模擬結果不代表未來績效，亦不保證未來表現。"
)

SYSTEM_PROMPT = """你是「ETF Portfolio Lab」的投資組合研究助理。請嚴格遵守以下規則：

1. 你只能根據使用者提供的「系統資料」（JSON 格式的上下文）進行分析，不可自行推測或捏造任何
   ETF 成分股、產業占比、權重、報酬率或其他數字。若資料缺失，請明確說明「資料不足」。
2. 回答中必須引用資料來源（source）與資料日期（data_date），讓使用者知道數據的時效性與可信度。
3. 絕對不可給出「買進」、「賣出」、「加碼」、「減碼」等具體買賣指令或投資建議，只能提供研究分析
   與風險提醒。
4. 若內容涉及回測（backtest）或財務模擬（projection），必須明確說明「回測結果不代表未來績效」、
   「模擬結果不保證未來表現」。
5. 請一律使用繁體中文回答，語氣中立、客觀、專業。
"""


def _provenance_source_date(provenance: dict | None) -> tuple[str | None, str | None]:
    if not provenance:
        return None, None
    source = provenance.get("source_name")
    date = provenance.get("data_date")
    if date is not None:
        date = str(date)
    return source, date


def _no_data_result(reason: str) -> dict:
    return {
        "analysis_text": f"資料不足，無法分析：{reason}",
        "provider": None,
        "model": None,
        "refused": False,
        "data_sources": [],
        "data_dates": [],
        "disclaimer": DISCLAIMER,
    }


def _render_user_prompt(question: str, context: dict) -> str:
    context_json = json.dumps(context, ensure_ascii=False, indent=2, default=str)
    return (
        f"以下是系統資料（JSON），請僅根據這些資料回答問題：\n\n"
        f"```json\n{context_json}\n```\n\n"
        f"問題：{question}"
    )


def _call_provider(
    question: str, context: dict, provider, data_sources: list[str], data_dates: list[str]
) -> dict:
    provider = provider or get_ai_provider()
    user_prompt = _render_user_prompt(question, context)

    # Always append the citation + disclaimer block so it is present even
    # for the mock provider (which echoes the user prompt verbatim).
    citation_lines = []
    if data_sources or data_dates:
        citation_lines.append("資料來源：" + ("、".join(sorted(set(s for s in data_sources if s))) or "未知"))
        citation_lines.append("資料日期：" + ("、".join(sorted(set(d for d in data_dates if d))) or "未知"))
    citation_block = "\n".join(citation_lines)

    full_user_prompt = user_prompt
    if citation_block:
        full_user_prompt += f"\n\n{citation_block}"
    full_user_prompt += f"\n\n{DISCLAIMER}"

    result: AIResult = provider.generate(SYSTEM_PROMPT, full_user_prompt)

    return {
        "analysis_text": result.text,
        "provider": result.provider,
        "model": result.model,
        "refused": result.refused,
        "data_sources": sorted(set(s for s in data_sources if s)),
        "data_dates": sorted(set(d for d in data_dates if d)),
        "disclaimer": DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# Context builders
# ---------------------------------------------------------------------------


def build_etf_context(session: Session, symbol: str) -> dict:
    """Gather ETF context purely from existing services. Returns {} if no data."""
    card = get_etf_card(session, symbol)
    if card is None:
        return {}

    top_holdings = get_top_holdings(session, symbol, n=10)
    exposure = get_industry_exposure(session, symbol, level=1)

    return {
        "symbol": card["symbol"],
        "name": card["name"],
        "issuer": card["issuer"],
        "asset_class": card["asset_class"],
        "expense_ratio": card["expense_ratio"],
        "tracking_index": card["tracking_index"],
        "concentration": card["concentration"],
        "top3_industries": card["top3_industries"],
        "top_holdings": top_holdings,
        "industry_exposure": exposure["industries"],
        "data_provenance": card["data_provenance"],
    }


def build_portfolio_context(session: Session, portfolio_id_or_items) -> dict:
    """Gather portfolio context: validation, look-through, concentration, warnings."""
    items = portfolio_service._resolve_items(session, portfolio_id_or_items)
    if not items:
        return {}

    validation = portfolio_service.validate_weights(session, portfolio_id_or_items)
    stock_exposure = portfolio_service.get_look_through_stock_exposure(
        session, portfolio_id_or_items
    )
    industry_exposure = portfolio_service.get_look_through_industry_exposure(
        session, portfolio_id_or_items
    )
    concentration = portfolio_service.get_portfolio_concentration(
        session, portfolio_id_or_items
    )
    warnings = portfolio_service.get_portfolio_warnings(session, portfolio_id_or_items)

    return {
        "items": items,
        "validation_status": validation.get("status"),
        "top_holdings": stock_exposure["stocks"][:10],
        "num_stocks": stock_exposure["num_stocks"],
        "missing_holdings": stock_exposure["missing_holdings"],
        "industry_exposure": industry_exposure.get("industries", [])[:10],
        "concentration": concentration,
        "warnings": warnings["warnings"],
    }


def build_backtest_context(result_dict: dict) -> dict:
    """Wrap a backtest result dict as context (no fabrication, pass-through)."""
    if not result_dict:
        return {}
    return {"backtest_result": result_dict}


def build_projection_context(result_dict: dict) -> dict:
    """Wrap a projection result dict as context (no fabrication, pass-through)."""
    if not result_dict:
        return {}
    return {"projection_result": result_dict}


# ---------------------------------------------------------------------------
# Analysis entry points
# ---------------------------------------------------------------------------


def analyze_etf(session: Session, symbol: str, provider=None, question: str | None = None) -> dict:
    context = build_etf_context(session, symbol)
    if not context:
        return _no_data_result(f"找不到 ETF {symbol} 的成分股或基本資料。")

    source, date = _provenance_source_date(context.get("data_provenance"))
    data_sources = [source] if source else []
    data_dates = [date] if date else []

    question = question or f"請說明 ETF {symbol} 的基本特性、產業曝險與集中度風險。"
    return _call_provider(question, context, provider, data_sources, data_dates)


def analyze_portfolio(session: Session, portfolio_id_or_items, provider=None, question: str | None = None) -> dict:
    context = build_portfolio_context(session, portfolio_id_or_items)
    if not context:
        return _no_data_result("找不到投資組合或組合內無任何標的。")

    # Collect provenance from each underlying ETF in the portfolio.
    data_sources: list[str] = []
    data_dates: list[str] = []
    for item in context.get("items", []):
        symbol = item.get("etf_symbol") or item.get("symbol")
        if not symbol:
            continue
        card = get_etf_card(session, symbol)
        if card:
            source, date = _provenance_source_date(card.get("data_provenance"))
            if source:
                data_sources.append(source)
            if date:
                data_dates.append(date)

    question = question or "請說明此投資組合的產業曝險分布、集中度與潛在風險。"
    return _call_provider(question, context, provider, data_sources, data_dates)


def explain_backtest(result_dict: dict, provider=None, question: str | None = None) -> dict:
    context = build_backtest_context(result_dict)
    if not context:
        return _no_data_result("沒有提供回測結果資料。")

    question = question or "請說明此回測結果的重點與限制。"
    return _call_provider(question, context, provider, [], [])


def explain_projection(result_dict: dict, provider=None, question: str | None = None) -> dict:
    context = build_projection_context(result_dict)
    if not context:
        return _no_data_result("沒有提供財務模擬結果資料。")

    question = question or "請說明此財務模擬結果的重點與限制。"
    return _call_provider(question, context, provider, [], [])
