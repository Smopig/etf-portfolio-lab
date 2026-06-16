"""Tests for SinopacHoldingProvider (offline, no network, CLAUDE.md §7).

Covers: happy path (fund list from the ``<select name="fundId">`` + POST-selected
holdings table parsed to code/name/weight/shares, data date from 資料日期,
confidence HIGH), the bond schema (ISIN code, blank 股數 -> shares None), a
non-SinoPac symbol (absent from the list -> empty + error, no POST), and an
unparseable holdings page (-> empty + error). The provider must NEVER fabricate.

Fixtures reproduce the real PCF page shapes verified live on 2026-06-16
(00907 equity, 00958B bond).
"""

from __future__ import annotations

from app.providers.data.sinopac_holding_provider import SinopacHoldingProvider

_LIST_PAGE = """
<html><body>
  <select name="fundId">
    <option value="00930">永豐ESG低碳高息</option>
    <option value="00907">永豐優息存股</option>
    <option value="00958B">永豐ESG銀行債15+</option>
  </select>
</body></html>
""".encode("utf-8")

_HOLD_EQUITY = """
<html><body>
  <span>資料日期：2026/06/16</span>
  <table>
    <tr><th>證券代碼</th><th>證券名稱</th><th>股數</th><th>佔基金淨資產之權重(%)</th></tr>
    <tr><td>2603</td><td>長榮</td><td>802,523</td><td>6.25</td></tr>
    <tr><td>2618</td><td>長榮航</td><td>3,502,034</td><td>4.92</td></tr>
  </table>
</body></html>
""".encode("utf-8")

_HOLD_BOND = """
<html><body>
  <span>資料日期：2026/06/15</span>
  <table>
    <tr><th>證券代碼</th><th>證券名稱</th><th>股數</th><th>佔基金淨資產之權重(%)</th></tr>
    <tr><td>US404280DW61</td><td>HSBC 6.332 03/09/44</td><td></td><td>5.63</td></tr>
  </table>
</body></html>
""".encode("utf-8")


def _http_factory(hold: bytes = _HOLD_EQUITY):
    calls: list[tuple[str, dict | None]] = []

    def fake(url: str, data: dict | None = None) -> bytes:
        calls.append((url, data))
        if data is None:
            return _LIST_PAGE
        return hold

    return fake, calls


def test_happy_path_equity():
    fake, calls = _http_factory()
    provider = SinopacHoldingProvider(http_request=fake)
    result = provider.fetch(symbol="00907")

    assert result.source_name == "永豐投信"
    assert result.reliability_level == "high"
    assert result.errors == []
    assert len(result.records) == 2

    rec = result.records[0]
    assert rec["asset_symbol"] == "2603"
    assert rec["asset_name"] == "長榮"
    assert rec["weight"] == 6.25
    assert rec["shares"] == 802523.0
    assert rec["confidence_level"] == "HIGH"
    assert result.data_date.isoformat() == "2026-06-16"
    # Selected via POST fundId=00907.
    assert ("https://sitc.sinopac.com/SinopacEtfs/Etfs/Pcf", {"fundId": "00907"}) in calls


def test_bond_schema_blank_shares():
    fake, _ = _http_factory(hold=_HOLD_BOND)
    provider = SinopacHoldingProvider(http_request=fake)
    result = provider.fetch(symbol="00958B")

    assert len(result.records) == 1
    rec = result.records[0]
    assert rec["asset_symbol"] == "US404280DW61"
    assert rec["weight"] == 5.63
    assert rec["shares"] is None  # blank 股數, never invented
    assert result.data_date.isoformat() == "2026-06-15"


def test_non_sinopac_symbol_returns_empty_without_post():
    fake, calls = _http_factory()
    provider = SinopacHoldingProvider(http_request=fake)
    result = provider.fetch(symbol="0050")

    assert result.records == []
    assert result.errors
    assert all(data is None for _, data in calls)  # no POST issued


def test_unparseable_page_returns_empty():
    fake, _ = _http_factory(hold=b"<html><body>no table</body></html>")
    provider = SinopacHoldingProvider(http_request=fake)
    result = provider.fetch(symbol="00907")

    assert result.records == []
    assert result.errors
