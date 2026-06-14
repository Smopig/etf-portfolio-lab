"""Tests for YahooDividendProvider (CLAUDE.md §7: no fabrication)."""

from __future__ import annotations

import datetime as dt

from app.providers.data.yahoo_dividend_provider import YahooDividendProvider

# Sanitized fixture mirroring the real Yahoo dividend page: a YEAR summary row
# (must be skipped), two paid SUB rows, and one upcoming SUB row. Slashes are
# unicode-escaped exactly as Yahoo emits them.
HTML_OK = (
    b'<html><head></head><body><script>window.__data={'
    b'"symbol":"00929","dividends":['
    b'{"yearBySort":"2026","recordType":"YEAR","period":"","exDividend":{"cash":"0.92"}},'
    b'{"exDate":"2026-06-17T00:00:00+08:00","year":"2026","period":"M5",'
    b'"symbol":"00929","totalDividend":"0.26","isUpcoming":false,'
    b'"exDividend":{"cash":"0.26","cashPayDate":"2026-07-13T00:00:00+08:00"},'
    b'"recordType":"SUB"},'
    b'{"exDate":"2026-05-20T00:00:00+08:00","year":"2026","period":"M4",'
    b'"symbol":"00929","totalDividend":"0.13","isUpcoming":false,'
    b'"exDividend":{"cash":"0.13","cashPayDate":"2026-06-13T00:00:00+08:00"},'
    b'"recordType":"SUB"},'
    b'{"exDate":"2026-07-16T00:00:00+08:00","year":"2026","period":"M6",'
    b'"symbol":"00929","totalDividend":"0.25","isUpcoming":true,'
    b'"exDividend":{"cash":"0.25"},"recordType":"SUB"}'
    b']};</script></body></html>'
)

HTML_NO_BLOB = b"<html><body>no data here</body></html>"

HTML_MALFORMED = (
    b'<html><body><script>{"dividends":[{"exDate":"oops","recordType":"SUB"'
    b'</script></body></html>'
)


def _provider(payload, *, raises=None):
    def http_get(url):
        if raises is not None:
            raise raises
        return payload

    return YahooDividendProvider(http_get=http_get)


def test_happy_path_parses_sub_rows():
    result = _provider(HTML_OK).fetch(symbol="00929")
    assert result.errors == []
    # YEAR row skipped; 3 SUB rows parsed (2 paid + 1 upcoming).
    assert len(result.records) == 3

    by_date = {r["ex_dividend_date"]: r for r in result.records}

    paid = by_date[dt.date(2026, 6, 17)]
    assert paid["dividend_amount"] == 0.26
    assert paid["payment_date"] == dt.date(2026, 7, 13)
    assert paid["is_upcoming"] is False
    assert paid["period"] == "M5"
    assert paid["source_name"] == "Yahoo奇摩股市"
    assert paid["confidence_level"] == "MEDIUM"

    # Unicode-escaped slash in pay date decoded correctly.
    assert by_date[dt.date(2026, 5, 20)]["payment_date"] == dt.date(2026, 6, 13)

    upcoming = by_date[dt.date(2026, 7, 16)]
    assert upcoming["is_upcoming"] is True
    assert upcoming["dividend_amount"] == 0.25

    assert result.data_date == dt.date(2026, 7, 16)


def test_non_200_returns_empty_with_errors():
    err = Exception("boom")
    err.code = 404
    result = _provider(None, raises=err).fetch(symbol="00929")
    assert result.records == []
    assert result.errors
    assert "404" in result.errors[0]


def test_no_dividends_blob_returns_empty():
    result = _provider(HTML_NO_BLOB).fetch(symbol="00929")
    assert result.records == []
    assert result.errors == ["no dividends blob found in Yahoo page"]


def test_malformed_json_returns_empty():
    result = _provider(HTML_MALFORMED).fetch(symbol="00929")
    assert result.records == []
    assert result.errors  # never fabricates


def test_empty_response_returns_empty():
    result = _provider(b"").fetch(symbol="00929")
    assert result.records == []
    assert result.errors
