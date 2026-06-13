"""Tests for app.services.data_fetch_service (SQLite, offline)."""

from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import sessionmaker

from app.models import (
    DataQualityCheck,
    EtfDividend,
    EtfHolding,
    EtfMaster,
    EtfPrice,
    FetchLog,
    StockIndustry,
)
from app.providers.data.csv_file_provider import CsvFileProvider
from app.services.data_fetch_service import run_fetch

TABLES = [
    EtfMaster.__table__,
    EtfHolding.__table__,
    StockIndustry.__table__,
    EtfPrice.__table__,
    EtfDividend.__table__,
    DataQualityCheck.__table__,
    FetchLog.__table__,
]


@pytest.fixture()
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test.db")
    metadata = MetaData()
    for table in TABLES:
        new_table = table.to_metadata(metadata)
        for column in new_table.columns:
            if column.server_default is not None:
                column.server_default = None
    metadata.create_all(engine)

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


@pytest.fixture()
def csv_path(tmp_path):
    path = tmp_path / "prices.csv"
    path.write_text(
        "etf_symbol,trade_date,close,source_name\n"
        "ETF0050,2026-06-01,150.5,test-source\n"
        "ETF0050,2026-06-02,151.0,test-source\n"
    )
    return path


def test_run_fetch_inserts_rows_and_writes_fetch_log(session, csv_path):
    provider = CsvFileProvider()

    summary = run_fetch(
        session,
        provider,
        "etf_prices",
        persist=True,
        file_path=csv_path,
        preserve_raw=False,
    )

    assert summary["status"] == "success"
    assert summary["rows_fetched"] == 2
    assert summary["rows_inserted"] == 2

    rows = session.query(EtfPrice).all()
    assert len(rows) == 2
    assert {r.trade_date for r in rows} == {dt.date(2026, 6, 1), dt.date(2026, 6, 2)}

    logs = session.query(FetchLog).all()
    assert len(logs) == 1
    assert logs[0].status == "success"
    assert logs[0].rows_fetched == 2
    assert logs[0].rows_inserted == 2
    assert logs[0].provider_name == "local-file"


def test_run_fetch_skips_existing_rows_on_rerun(session, csv_path):
    provider = CsvFileProvider()
    params = dict(
        file_path=csv_path,
        preserve_raw=False,
    )

    run_fetch(session, provider, "etf_prices", persist=True, **params)
    summary2 = run_fetch(session, provider, "etf_prices", persist=True, **params)

    assert summary2["rows_fetched"] == 2
    assert summary2["rows_inserted"] == 0
    assert session.query(EtfPrice).count() == 2
    assert session.query(FetchLog).count() == 2


def test_run_fetch_persist_false_writes_nothing(session, csv_path):
    provider = CsvFileProvider()

    summary = run_fetch(
        session,
        provider,
        "etf_prices",
        persist=False,
        file_path=csv_path,
        preserve_raw=False,
    )

    assert summary["rows_fetched"] == 2
    assert session.query(EtfPrice).count() == 0
    assert session.query(FetchLog).count() == 0


def test_run_fetch_missing_file_returns_error_status(session, tmp_path):
    provider = CsvFileProvider()

    summary = run_fetch(
        session,
        provider,
        "etf_prices",
        persist=True,
        file_path=tmp_path / "missing.csv",
        preserve_raw=False,
    )

    assert summary["status"] == "error"
    assert summary["rows_fetched"] == 0
    assert session.query(EtfPrice).count() == 0

    log = session.query(FetchLog).first()
    assert log.status == "error"
    assert log.message
