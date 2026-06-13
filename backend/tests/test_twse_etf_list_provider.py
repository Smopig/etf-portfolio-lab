"""Tests for TwseEtfListProvider (offline, no network, CLAUDE.md §7)."""

from __future__ import annotations

import datetime as dt

from app.providers.data.twse_etf_list_provider import TwseEtfListProvider

# Minimal fixture mimicking the TWSE ISIN listing page table structure:
# section header rows (single cell) followed by data rows.
_HTML_FIXTURE = """
<html><body>
<table>
<tr><td colspan="6">股票</td></tr>
<tr><td>2330　台積電</td><td>TW0002330008</td><td>1994/09/05</td><td>上市</td><td>半導體業</td><td>ESVUFR</td></tr>
<tr><td colspan="6">ETF</td></tr>
<tr><td>0050　元大台灣50</td><td>TW0000050004</td><td>2003/06/30</td><td>上市</td><td></td><td>EFTSF1</td></tr>
<tr><td>0056　元大高股息</td><td>TW0000056001</td><td>2007/12/13</td><td>上市</td><td></td><td>EFTSF1</td></tr>
<tr><td colspan="6">ETN</td></tr>
<tr><td>020000　某ETN</td><td>TW0020000001</td><td>2020/01/01</td><td>上市</td><td></td><td>EFTSN1</td></tr>
</table>
</body></html>
"""


def _fake_http_get_factory(html: str, encoding: str = "cp950"):
    def fake_http_get(url: str) -> bytes:
        return html.encode(encoding)

    return fake_http_get


def test_extracts_only_etf_section_rows():
    provider = TwseEtfListProvider(http_get=_fake_http_get_factory(_HTML_FIXTURE))
    result = provider.fetch(market="listed")

    assert result.dataset_type == "etf_master"
    assert result.source_name == "twse-isin"
    assert result.reliability_level == "high"
    assert result.errors == []

    symbols = {r["symbol"] for r in result.records}
    assert symbols == {"0050", "0056"}

    # ETN row and 股票 row must be excluded.
    assert "020000" not in symbols
    assert "2330" not in symbols

    rec = next(r for r in result.records if r["symbol"] == "0050")
    assert rec["symbol"] == "0050"  # leading zero preserved
    assert rec["name"] == "元大台灣50"
    assert rec["listing_date"] == "2003-06-30"
    assert rec["source_name"] == "twse-isin"
    assert rec["source_url"]

    assert result.data_date == dt.date.today()


def test_failing_http_get_returns_no_fabrication():
    def failing_http_get(url: str) -> bytes:
        raise ConnectionError("network down")

    provider = TwseEtfListProvider(http_get=failing_http_get)
    result = provider.fetch(market="listed")

    assert result.records == []
    assert result.errors
    assert "network down" in result.errors[0]
    assert result.data_date is None


def test_both_markets_merge_records():
    provider = TwseEtfListProvider(http_get=_fake_http_get_factory(_HTML_FIXTURE))
    result = provider.fetch(market="both")

    # Same fixture used for both URLs -> 0050 and 0056 each appear twice.
    symbols = [r["symbol"] for r in result.records]
    assert symbols.count("0050") == 2
    assert symbols.count("0056") == 2
