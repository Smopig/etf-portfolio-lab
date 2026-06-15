"""Tests for FubonHoldingProvider (offline, no network, CLAUDE.md §7).

Covers: happy path (server-rendered Assets.aspx parsed across futures + stock
tables with code/name/weight/shares, the per-class 合計 total row skipped, data
date + AUM/NAV captured, confidence HIGH), a non-Fubon symbol (absent from the
ETFSeries list -> empty + error so the caller falls back to Yahoo), and an empty
ETFSeries list (-> every symbol filtered out). The provider must NEVER fabricate
rows.

Fixtures reproduce the real HTML shapes verified live against
``websys.fsit.com.tw`` on 2026-06-15 (00900/006208).
"""

from __future__ import annotations

from app.providers.data.fubon_holding_provider import FubonHoldingProvider

_SERIES_HTML = """
<html><body>
  <a href="/FubonETF/Fund/Profile.aspx?stkId=006208">了解更多</a>
  <a href="/FubonETF/Fund/Assets.aspx?stkId=00900">了解更多</a>
  <a href="/FubonETF/Fund/Assets.aspx?stkId=00892">了解更多</a>
  <a href="/FubonETF/Fund/Assets.aspx?stkId=00675L">了解更多</a>
</body></html>
""".encode("utf-8")

# Assets.aspx for 00900: a futures table (with 合計 total) + a stock table.
_ASSETS_00900 = """
<html><body>
  <span>資料日期：2026/06/15</span>
  <div>淨資產(新台幣) 33,754,868,613 基金在外流通單位數 1,000</div>
  <div>每單位淨值(新台幣) 19.61</div>
  <table>
    <tr><th>期貨代碼</th><th>期貨名稱</th><th>口數</th><th>金額</th><th>權重(%)</th></tr>
    <tr><td>WTXN6F</td><td>2026/07台股指數期貨</td><td>33</td><td>302,412,000</td><td>0.8959</td></tr>
    <tr><td>期貨合計</td><td>302,412,000</td><td>0.8959</td></tr>
  </table>
  <table>
    <tr><th>股票代碼</th><th>股票名稱</th><th>股數</th><th>金額</th><th>權重(%)</th></tr>
    <tr><td>2454</td><td>聯發科</td><td>768,000</td><td>3,432,960,000</td><td>10.1702</td></tr>
    <tr><td>2303</td><td>聯電</td><td>20,243,000</td><td>2,864,384,500</td><td>8.4858</td></tr>
    <tr><td>股票合計</td><td>33,335,941,400</td><td>98.7573</td></tr>
  </table>
</body></html>
""".encode("utf-8")


def _http_get_factory(assets: bytes = _ASSETS_00900, *, series: bytes = _SERIES_HTML):
    calls: list[str] = []

    def fake_http_get(url: str) -> bytes:
        calls.append(url)
        if url.endswith("/Fund/ETFSeries.aspx"):
            return series
        if "/Fund/Assets.aspx" in url:
            return assets
        raise AssertionError(f"unexpected url {url}")

    return fake_http_get, calls


def test_happy_path_parses_futures_and_stock_tables():
    fake, calls = _http_get_factory()
    provider = FubonHoldingProvider(http_get=fake)
    result = provider.fetch(symbol="00900")

    assert result.dataset_type == "etf_holdings"
    assert result.source_name == "富邦投信"
    assert result.reliability_level == "high"
    assert result.errors == []
    # 1 futures + 2 stocks = 3 rows; both 合計 total rows skipped.
    assert len(result.records) == 3
    symbols = [r["asset_symbol"] for r in result.records]
    assert symbols == ["WTXN6F", "2454", "2303"]
    assert all("合計" not in s for s in symbols)

    fut = result.records[0]
    assert fut["asset_name"] == "2026/07台股指數期貨"
    assert fut["weight"] == 0.8959
    assert fut["shares"] == 33.0  # 口數
    stock = result.records[1]
    assert stock["asset_symbol"] == "2454"
    assert stock["weight"] == 10.1702
    assert stock["shares"] == 768000.0
    assert stock["confidence_level"] == "HIGH"

    assert result.data_date.isoformat() == "2026-06-15"
    assert result.fund_meta["aum"] == 33754868613.0
    assert result.fund_meta["nav"] == 19.61
    assert result.fund_meta["nav_date"].isoformat() == "2026-06-15"


def test_non_fubon_symbol_returns_empty_without_assets_call():
    fake, calls = _http_get_factory()
    provider = FubonHoldingProvider(http_get=fake)
    result = provider.fetch(symbol="0050")  # not in ETFSeries list

    assert result.records == []
    assert result.errors
    # Self-filtered via the fund set; no Assets.aspx call wasted.
    assert not any("/Fund/Assets.aspx" in u for u in calls)


def test_empty_series_filters_everything():
    fake, _ = _http_get_factory(series=b"<html></html>")
    provider = FubonHoldingProvider(http_get=fake)
    result = provider.fetch(symbol="00900")

    assert result.records == []
    assert result.errors
