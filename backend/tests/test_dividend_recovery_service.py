"""Tests for dividend_recovery_service (填息天數, sqlite, CLAUDE.md §7).

Covers: a dividend that fills (填息) in N trading days → days_to_recover=N,
recovered=True with the right recovered_date; a dividend not yet recovered →
recovered=False / days_to_recover=None; pre_ex_close picked from the last
trading day before the ex-date.
"""

from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import sessionmaker

from app.models import EtfDividend, EtfMaster, EtfPrice
from app.services.dividend_recovery_service import get_dividend_recovery

TABLES = [
    EtfMaster.__table__,
    EtfDividend.__table__,
    EtfPrice.__table__,
]


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


def _price(session, symbol, trade_date, close):
    session.add(EtfPrice(etf_symbol=symbol, trade_date=trade_date, close=close))


def _div(session, symbol, ex_date, amount):
    session.add(
        EtfDividend(
            etf_symbol=symbol,
            ex_dividend_date=ex_date,
            dividend_amount=amount,
            source_name="Yahoo奇摩股市",
        )
    )


def test_recovers_in_n_trading_days(sqlite_session):
    session = sqlite_session()
    session.add(EtfMaster(symbol="0050", name="元大台灣50", is_active=True))

    # Consecutive trading days. ex_date = day 3 (2026-01-05).
    # Pre-ex close = day before ex (2026-01-02) = 100.
    # Closes drop on ex then climb back to >= 100 on day 4 of the post-ex walk.
    _price(session, "0050", dt.date(2026, 1, 2), 100.0)  # pre-ex
    _price(session, "0050", dt.date(2026, 1, 5), 98.0)   # ex-date  -> trading day 1
    _price(session, "0050", dt.date(2026, 1, 6), 98.5)   # day 2
    _price(session, "0050", dt.date(2026, 1, 7), 99.0)   # day 3
    _price(session, "0050", dt.date(2026, 1, 8), 100.0)  # day 4 -> recovered
    _div(session, "0050", dt.date(2026, 1, 5), 2.0)
    session.commit()

    rows = get_dividend_recovery(session, "0050")
    assert len(rows) == 1
    r = rows[0]
    assert r["ex_date"] == dt.date(2026, 1, 5)
    assert r["dividend_amount"] == 2.0
    assert r["pre_ex_close"] == 100.0
    assert r["recovered"] is True
    assert r["days_to_recover"] == 4
    assert r["recovered_date"] == dt.date(2026, 1, 8)


def test_not_yet_recovered(sqlite_session):
    session = sqlite_session()
    session.add(EtfMaster(symbol="00878", name="國泰永續高股息", is_active=True))

    _price(session, "00878", dt.date(2026, 2, 2), 20.0)  # pre-ex
    _price(session, "00878", dt.date(2026, 2, 3), 18.0)  # ex-date
    _price(session, "00878", dt.date(2026, 2, 4), 18.5)  # never reaches 20
    _price(session, "00878", dt.date(2026, 2, 5), 19.0)
    _div(session, "00878", dt.date(2026, 2, 3), 0.5)
    session.commit()

    rows = get_dividend_recovery(session, "00878")
    assert len(rows) == 1
    r = rows[0]
    assert r["pre_ex_close"] == 20.0
    assert r["recovered"] is False
    assert r["days_to_recover"] is None
    assert r["recovered_date"] is None
