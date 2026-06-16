"""Tests for KgiHoldingProvider (offline, no network, CLAUDE.md §7).

Covers: happy path (server-rendered, HTML-entity-encoded holdings table parsed
to code/name/weight/shares, monthly data date from the LastMonthLastDay hidden
input, confidence HIGH), the fund-code scan that maps public code -> internal
fundID, a non-KGI symbol (absent from the map -> empty + error), and a bond ETF
that renders no holdings table (-> empty + error so the caller falls back to
Yahoo). The provider must NEVER fabricate rows.

Fixtures reproduce the real kgifund.com.tw detail-page shapes verified live on
2026-06-16 (J015=00915 equity, J014=00890B bond), including entity-encoded
Chinese (e.g. ``&#x80A1;&#x7968;&#x4EE3;&#x865F;`` = 股票代號).
"""

from __future__ import annotations

from app.providers.data.kgi_holding_provider import KgiHoldingProvider

# 股票代號 / 股票名稱 / 股數 / 權重(%) header, entity-encoded; two stock rows.
_J015 = """
<html><body>
  <h3>(00915 &#x51F1;&#x57FA;&#x53F0;&#x7063;&#x512A;&#x9078;&#x9AD8;&#x80A1;&#x606F;30ETF)</h3>
  <input name="LastMonthLastDay" type="hidden" value="2026/05/31" />
  <table>
    <tr><th>&#x80A1;&#x7968;&#x4EE3;&#x865F;</th><th>&#x80A1;&#x7968;&#x540D;&#x7A31;</th><th>&#x80A1;&#x6578;</th><th>&#x6B0A;&#x91CD;(%)</th></tr>
    <tr><td>2303</td><td>&#x806F;&#x96FB;</td><td>18,797,000</td><td>15.22</td></tr>
    <tr><td>2882</td><td>&#x570B;&#x6CF0;&#x91D1;</td><td>13,303,000</td><td>8.37</td></tr>
  </table>
</body></html>
""".encode("utf-8")

# A KGI bond ETF page: has its own code but NO holdings table.
_J014 = """
<html><body>
  <h3>(00890B &#x51F1;&#x57FA;&#x50B5;&#x5238;)</h3>
  <input name="LastMonthLastDay" type="hidden" value="2026/05/31" />
  <p>&#x50B5;&#x5238; bond fund with no constituent table here.</p>
</body></html>
""".encode("utf-8")


def _http_get_factory():
    calls: list[str] = []

    def fake_http_get(url: str) -> bytes:
        calls.append(url)
        if "fundID=J015" in url:
            return _J015
        if "fundID=J014" in url:
            return _J014
        # Other scanned ids: empty page (no own-code match).
        return b"<html><body>no fund</body></html>"

    return fake_http_get, calls


def test_happy_path_equity_holdings():
    fake, calls = _http_get_factory()
    provider = KgiHoldingProvider(http_get=fake)
    result = provider.fetch(symbol="00915")

    assert result.source_name == "凱基投信"
    assert result.reliability_level == "high"
    assert result.errors == []
    assert len(result.records) == 2

    rec = result.records[0]
    assert rec["asset_symbol"] == "2303"
    assert rec["asset_name"] == "聯電"  # entity-decoded
    assert rec["weight"] == 15.22
    assert rec["shares"] == 18797000.0
    assert rec["confidence_level"] == "HIGH"
    assert rec["holding_date"].isoformat() == "2026-05-31"
    assert result.data_date.isoformat() == "2026-05-31"
    # Resolved 00915 -> J015 via the scan.
    assert any("fundID=J015" in u for u in calls)


def test_non_kgi_symbol_returns_empty():
    fake, _ = _http_get_factory()
    provider = KgiHoldingProvider(http_get=fake)
    result = provider.fetch(symbol="0050")

    assert result.records == []
    assert result.errors


def test_bond_etf_without_table_returns_empty():
    fake, _ = _http_get_factory()
    provider = KgiHoldingProvider(http_get=fake)
    result = provider.fetch(symbol="00890B")

    assert result.records == []
    assert result.errors


def test_fund_map_built_from_scan():
    fake, _ = _http_get_factory()
    provider = KgiHoldingProvider(http_get=fake)
    fund_map = provider._load_fund_map()
    assert fund_map.get("00915") == "J015"
    assert fund_map.get("00890B") == "J014"
