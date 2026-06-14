"""Tests for dividend_ranking_service (sqlite, mirrors holdings test style)."""

from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import sessionmaker

from app.models import (
    EtfDividend,
    EtfDividendFrequencyOverride,
    EtfMaster,
    EtfPrice,
)
from app.services.dividend_ranking_service import (
    classify_frequency,
    get_dividend_ranking,
)

TABLES = [
    EtfMaster.__table__,
    EtfDividend.__table__,
    EtfDividendFrequencyOverride.__table__,
    EtfPrice.__table__,
]

TODAY = dt.date.today()


@pytest.fixture()
def sqlite_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test.db")
    metadata = MetaData()
    for table in TABLES:
        new_table = table.to_metadata(metadata)
        for column in new_table.columns:
            if column.server_default is not None:
                column.server_default = None
    metadata.create_all(engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _master(symbol, name, freq=None):
    return EtfMaster(symbol=symbol, name=name, dividend_frequency=freq, is_active=True)


def _price(symbol, close, days_ago=1):
    return EtfPrice(
        etf_symbol=symbol,
        trade_date=TODAY - dt.timedelta(days=days_ago),
        close=close,
    )


def _div(symbol, ex_date, amount, period="M1", pay_date=None):
    return EtfDividend(
        etf_symbol=symbol,
        ex_dividend_date=ex_date,
        payment_date=pay_date,
        dividend_amount=amount,
        source_name="Yahoo奇摩股市",
        source_url="https://example/dividend",
        fetched_at=dt.datetime(2026, 6, 14),
    )


def test_ttm_sum_excludes_old_rows_and_yield_math(sqlite_session):
    session = sqlite_session()
    session.add(_master("00929", "復華台灣科技優息"))
    session.add(_price("00929", 20.0))
    # 4 monthly distributions within 365d = 0.25*4 = 1.0
    for m in range(4):
        session.add(
            _div("00929", TODAY - dt.timedelta(days=30 * (m + 1)), 0.25)
        )
    # One row older than 365 days -> excluded.
    session.add(_div("00929", TODAY - dt.timedelta(days=400), 5.0))
    session.commit()

    rows = get_dividend_ranking(session)
    assert len(rows) == 1
    r = rows[0]
    assert r["ttm_dividend"] == pytest.approx(1.0)
    # yield = 1.0 / 20 * 100 = 5.0 (TTM only, NOT single*frequency)
    assert r["ttm_yield_pct"] == pytest.approx(5.0)
    assert r["payout_per_100k"] == 5000
    assert r["source_name"] == "Yahoo奇摩股市"


def test_future_dated_rows_excluded_from_ttm(sqlite_session):
    session = sqlite_session()
    session.add(_master("00929", "x"))
    session.add(_price("00929", 10.0))
    session.add(_div("00929", TODAY - dt.timedelta(days=10), 0.5))
    # Future ex-date (upcoming should never have been persisted, but defensive).
    session.add(_div("00929", TODAY + dt.timedelta(days=10), 0.5))
    session.commit()

    r = get_dividend_ranking(session)[0]
    assert r["ttm_dividend"] == pytest.approx(0.5)
    assert r["ttm_yield_pct"] == pytest.approx(5.0)


def test_no_price_yields_none(sqlite_session):
    session = sqlite_session()
    session.add(_master("00929", "x"))
    session.add(_div("00929", TODAY - dt.timedelta(days=10), 0.5))
    session.commit()

    r = get_dividend_ranking(session)[0]
    assert r["ttm_yield_pct"] is None
    assert r["payout_per_100k"] is None


def test_override_beats_classification_and_master(sqlite_session):
    session = sqlite_session()
    # Master has 季配, but override says 月配; monthly-spaced history would
    # classify as 月配 too — override must win regardless.
    session.add(_master("00929", "x", freq="季配"))
    session.add(_price("00929", 10.0))
    session.add(
        EtfDividendFrequencyOverride(etf_symbol="00929", frequency="半年配")
    )
    session.add(_div("00929", TODAY - dt.timedelta(days=10), 0.5, period="M1"))
    session.commit()

    r = get_dividend_ranking(session)[0]
    assert r["frequency"] == "半年配"


def test_master_beats_classification(sqlite_session):
    session = sqlite_session()
    session.add(_master("00929", "x", freq="季配"))
    session.add(_price("00929", 10.0))
    session.add(_div("00929", TODAY - dt.timedelta(days=10), 0.5, period="M1"))
    session.commit()

    r = get_dividend_ranking(session)[0]
    assert r["frequency"] == "季配"


def test_classification_fallback_when_no_master(sqlite_session):
    session = sqlite_session()
    session.add(_master("00929", "x"))
    session.add(_price("00929", 10.0))
    for m in range(3):
        session.add(
            _div("00929", TODAY - dt.timedelta(days=30 * (m + 1)), 0.2, period="M1")
        )
    session.commit()

    r = get_dividend_ranking(session)[0]
    assert r["frequency"] == "月配"


def test_sorting_and_frequency_filter(sqlite_session):
    session = sqlite_session()
    # A: 月配, high yield. B: 季配, low yield. Frequency is stored on the
    # master at write time (period is not a DB column), so set it there.
    session.add(_master("AAA", "a", freq="月配"))
    session.add(_master("BBB", "b", freq="季配"))
    session.add(_price("AAA", 10.0))
    session.add(_price("BBB", 100.0))
    session.add(_div("AAA", TODAY - dt.timedelta(days=10), 1.0, period="M1"))
    session.add(_div("BBB", TODAY - dt.timedelta(days=10), 1.0, period="Q1"))
    session.commit()

    desc = get_dividend_ranking(session, order="desc")
    assert [r["etf_symbol"] for r in desc] == ["AAA", "BBB"]

    asc = get_dividend_ranking(session, order="asc")
    assert [r["etf_symbol"] for r in asc] == ["BBB", "AAA"]

    monthly = get_dividend_ranking(session, frequency="月配")
    assert [r["etf_symbol"] for r in monthly] == ["AAA"]

    limited = get_dividend_ranking(session, limit=1)
    assert len(limited) == 1
    assert limited[0]["etf_symbol"] == "AAA"


def test_classify_frequency_spacing_fallback():
    # Blank periods -> infer from ~90d spacing -> 季配.
    records = [
        {"ex_dividend_date": dt.date(2026, 1, 1), "period": ""},
        {"ex_dividend_date": dt.date(2026, 4, 1), "period": ""},
        {"ex_dividend_date": dt.date(2026, 7, 1), "period": ""},
    ]
    assert classify_frequency(records) == "季配"
