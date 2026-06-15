"""Tests for CathayHoldingProvider (offline, no network, CLAUDE.md §7).

Covers: happy path (GetIndexStockWeights parsed to full constituents with
code/name/weight, data date + AUM/NAV from GetETFAssets, confidence HIGH), a
non-Cathay symbol (absent from GetFundList -> empty + error, no weights call),
and a bond ETF whose stockWeights is empty (-> empty + error so the caller
falls back to Yahoo). The provider must NEVER fabricate rows.

Fixtures reproduce the real cwapi JSON shapes verified live on 2026-06-15
(00878=CN equity, 00687B=A8 bond).
"""

from __future__ import annotations

import json

from app.providers.data.cathay_holding_provider import CathayHoldingProvider

_FUND_LIST = json.dumps(
    {
        "result": [
            {"stockCode": "00878", "fundCode": "CN", "isETF": True},
            {"stockCode": "00687B", "fundCode": "A8", "isETF": True},
            {"stockCode": "00751", "fundCode": "ZZ", "isETF": False},  # not an ETF
        ],
        "success": True,
    }
).encode("utf-8")

_WEIGHTS_CN = json.dumps(
    {
        "result": {
            "date": "2026/06/15",
            "stockWeights": [
                {"stockCode": "2382", "stockName": "廣達", "weights": "10.31"},
                {"stockCode": "2891", "stockName": "中信金", "weights": "10.25"},
                {"stockCode": "2882", "stockName": "國泰金", "weights": "6.44"},
            ],
        },
        "success": True,
        "returnMessage": "成功",
    }
).encode("utf-8")

_WEIGHTS_BOND = json.dumps(
    {"result": {"date": "2026/06/15", "stockWeights": []}, "success": True, "returnMessage": "成功"}
).encode("utf-8")

_ASSETS_CN = json.dumps(
    {
        "result": {
            "preDate": "2026/06/15",
            "fundNav": "605,930,262,106",
            "fundOutstandingShares": "18,457,790,000",
            "fundPerNav": "32.83",
        },
        "success": True,
    }
).encode("utf-8")


def _http_get_factory(weights: bytes = _WEIGHTS_CN):
    calls: list[str] = []

    def fake_http_get(url: str) -> bytes:
        calls.append(url)
        if "GetFundList" in url:
            return _FUND_LIST
        if "GetIndexStockWeights" in url:
            return weights
        if "GetETFAssets" in url:
            return _ASSETS_CN
        raise AssertionError(f"unexpected url {url}")

    return fake_http_get, calls


def test_happy_path_parses_index_stock_weights():
    fake, calls = _http_get_factory()
    provider = CathayHoldingProvider(http_get=fake)
    result = provider.fetch(symbol="00878")

    assert result.dataset_type == "etf_holdings"
    assert result.source_name == "國泰投信"
    assert result.reliability_level == "high"
    assert result.errors == []
    assert len(result.records) == 3

    rec = result.records[0]
    assert rec["asset_symbol"] == "2382"
    assert rec["asset_name"] == "廣達"
    assert rec["weight"] == 10.31
    assert rec["shares"] is None  # not exposed by this endpoint (never invented)
    assert rec["confidence_level"] == "HIGH"
    assert rec["holding_date"].isoformat() == "2026-06-15"

    assert result.data_date.isoformat() == "2026-06-15"
    assert result.fund_meta["aum"] == 605930262106.0
    assert result.fund_meta["nav"] == 32.83
    # Resolved 00878 -> fundCode CN.
    assert any("fundCode=CN" in u for u in calls)


def test_non_cathay_symbol_returns_empty_without_weights_call():
    fake, calls = _http_get_factory()
    provider = CathayHoldingProvider(http_get=fake)
    result = provider.fetch(symbol="0050")

    assert result.records == []
    assert result.errors
    assert not any("GetIndexStockWeights" in u for u in calls)


def test_bond_etf_empty_weights_returns_empty_with_error():
    fake, _ = _http_get_factory(weights=_WEIGHTS_BOND)
    provider = CathayHoldingProvider(http_get=fake)
    result = provider.fetch(symbol="00687B")

    assert result.records == []
    assert result.errors
