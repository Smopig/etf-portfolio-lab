"""Tests for data quality checks using an in-memory SQLite DB."""

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
    StockIndustry,
)
from app.utils.data_quality import (
    FAIL,
    PASS,
    WARN,
    check_data_freshness,
    check_dividend_duplicates,
    check_holding_industry_coverage,
    check_holding_missing_asset_symbol,
    check_holding_weight_sum,
    persist_results,
    run_all_checks,
)

TABLES = [
    EtfMaster.__table__,
    EtfHolding.__table__,
    StockIndustry.__table__,
    EtfPrice.__table__,
    EtfDividend.__table__,
    DataQualityCheck.__table__,
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

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal


# ---------------------------------------------------------------------
# holding_weight_sum
# ---------------------------------------------------------------------

def _add_holding(session, **kwargs):
    defaults = dict(
        etf_symbol="0050",
        holding_date=dt.date(2026, 6, 1),
        asset_symbol="2330",
        asset_name="TSMC",
        weight=10.0,
        source_name="TWSE",
    )
    defaults.update(kwargs)
    session.add(EtfHolding(**defaults))


def test_holding_weight_sum_pass(sqlite_session):
    session = sqlite_session()
    try:
        for i in range(10):
            _add_holding(session, asset_symbol=f"S{i}", weight=10.0)
        session.commit()

        results = check_holding_weight_sum(session)
        assert len(results) == 1
        assert results[0].status == PASS
        assert "100.00%" in results[0].message
    finally:
        session.close()


def test_holding_weight_sum_warn(sqlite_session):
    session = sqlite_session()
    try:
        # sum = 92% -> WARN
        for i in range(10):
            weight = 9.2
            _add_holding(session, asset_symbol=f"S{i}", weight=weight)
        session.commit()

        results = check_holding_weight_sum(session)
        assert results[0].status == WARN
        assert "92.00%" in results[0].message
    finally:
        session.close()


def test_holding_weight_sum_fail(sqlite_session):
    session = sqlite_session()
    try:
        # sum = 50% -> FAIL
        for i in range(10):
            _add_holding(session, asset_symbol=f"S{i}", weight=5.0)
        session.commit()

        results = check_holding_weight_sum(session)
        assert results[0].status == FAIL
        assert "50.00%" in results[0].message
    finally:
        session.close()


def test_holding_weight_sum_fraction_scale(sqlite_session):
    session = sqlite_session()
    try:
        # weights stored as fractions summing to ~1.0 (100%)
        for i in range(10):
            _add_holding(session, asset_symbol=f"S{i}", weight=0.1)
        session.commit()

        results = check_holding_weight_sum(session)
        assert results[0].status == PASS
        assert "100.00%" in results[0].message
    finally:
        session.close()


# ---------------------------------------------------------------------
# holding_missing_asset_symbol
# ---------------------------------------------------------------------

def test_holding_missing_asset_symbol_warn(sqlite_session):
    session = sqlite_session()
    try:
        _add_holding(session, asset_symbol="2330", weight=50.0)
        _add_holding(session, asset_symbol=None, weight=50.0)
        session.commit()

        results = check_holding_missing_asset_symbol(session)
        assert results[0].status == WARN
        assert "1 holding row(s)" in results[0].message
    finally:
        session.close()


def test_holding_missing_asset_symbol_pass(sqlite_session):
    session = sqlite_session()
    try:
        _add_holding(session, asset_symbol="2330", weight=50.0)
        _add_holding(session, asset_symbol="2317", weight=50.0)
        session.commit()

        results = check_holding_missing_asset_symbol(session)
        assert results[0].status == PASS
    finally:
        session.close()


# ---------------------------------------------------------------------
# holding_industry_coverage
# ---------------------------------------------------------------------

def test_holding_industry_coverage_warn(sqlite_session):
    session = sqlite_session()
    try:
        _add_holding(session, asset_symbol="2330", weight=50.0)
        _add_holding(session, asset_symbol="2317", weight=50.0)
        session.add(
            StockIndustry(stock_symbol="2330", stock_name="TSMC", industry_level_1="Tech")
        )
        # 2317 has no industry row at all
        session.commit()

        results = check_holding_industry_coverage(session)
        assert results[0].status == WARN
        assert "1 holding(s)" in results[0].message
    finally:
        session.close()


def test_holding_industry_coverage_pass(sqlite_session):
    session = sqlite_session()
    try:
        _add_holding(session, asset_symbol="2330", weight=100.0)
        session.add(
            StockIndustry(stock_symbol="2330", stock_name="TSMC", industry_level_1="Tech")
        )
        session.commit()

        results = check_holding_industry_coverage(session)
        assert results[0].status == PASS
    finally:
        session.close()


# ---------------------------------------------------------------------
# dividend_duplicates
# ---------------------------------------------------------------------

def test_dividend_duplicates_fail(sqlite_session):
    session = sqlite_session()
    try:
        session.add(
            EtfDividend(
                etf_symbol="0050",
                ex_dividend_date=dt.date(2026, 1, 15),
                dividend_amount=1.0,
                source_name="TWSE",
            )
        )
        session.add(
            EtfDividend(
                etf_symbol="0050",
                ex_dividend_date=dt.date(2026, 1, 15),
                dividend_amount=1.0,
                source_name="MOPS",
            )
        )
        session.commit()

        results = check_dividend_duplicates(session)
        assert results[0].status == FAIL
        assert "2026-01-15" in results[0].message
    finally:
        session.close()


def test_dividend_duplicates_pass(sqlite_session):
    session = sqlite_session()
    try:
        session.add(
            EtfDividend(
                etf_symbol="0050",
                ex_dividend_date=dt.date(2026, 1, 15),
                dividend_amount=1.0,
                source_name="TWSE",
            )
        )
        session.add(
            EtfDividend(
                etf_symbol="0050",
                ex_dividend_date=dt.date(2026, 4, 15),
                dividend_amount=1.0,
                source_name="TWSE",
            )
        )
        session.commit()

        results = check_dividend_duplicates(session)
        assert results[0].status == PASS
    finally:
        session.close()


# ---------------------------------------------------------------------
# data_freshness
# ---------------------------------------------------------------------

def test_data_freshness_fail_stale(sqlite_session):
    session = sqlite_session()
    try:
        session.add(
            EtfMaster(
                symbol="0050",
                name="Test ETF",
                issuer="Yuanta",
                asset_class="Equity",
                tracking_index="TWSE",
                data_date=dt.date(2024, 1, 1),
                source_name="TWSE",
            )
        )
        session.commit()

        results = check_data_freshness(session, today=dt.date(2026, 6, 12))
        assert len(results) == 1
        assert results[0].status == FAIL
        assert results[0].dataset_type == "etf_master"
    finally:
        session.close()


def test_data_freshness_pass_recent(sqlite_session):
    session = sqlite_session()
    try:
        session.add(
            EtfMaster(
                symbol="0050",
                name="Test ETF",
                issuer="Yuanta",
                asset_class="Equity",
                tracking_index="TWSE",
                data_date=dt.date(2026, 6, 1),
                source_name="TWSE",
            )
        )
        session.commit()

        results = check_data_freshness(session, today=dt.date(2026, 6, 12))
        assert results[0].status == PASS
    finally:
        session.close()


# ---------------------------------------------------------------------
# run_all_checks + persist_results: clean dataset -> all PASS, persisted
# ---------------------------------------------------------------------

def test_run_all_checks_clean_dataset_and_persist(sqlite_session):
    session = sqlite_session()
    try:
        session.add(
            EtfMaster(
                symbol="0050",
                name="Test ETF",
                issuer="Yuanta",
                asset_class="Equity",
                tracking_index="TWSE",
                data_date=dt.date(2026, 6, 1),
                source_name="TWSE",
            )
        )
        session.add(
            StockIndustry(
                stock_symbol="2330",
                stock_name="TSMC",
                industry_level_1="Tech",
                source_name="TWSE",
            )
        )
        _add_holding(session, asset_symbol="2330", weight=100.0)
        session.add(
            EtfDividend(
                etf_symbol="0050",
                ex_dividend_date=dt.date(2026, 5, 15),
                dividend_amount=1.0,
                source_name="TWSE",
            )
        )
        session.commit()

        results = run_all_checks(session, today=dt.date(2026, 6, 12))
        assert len(results) > 0
        assert all(r.status == PASS for r in results)

        persist_results(session, results)

        saved = session.query(DataQualityCheck).all()
        assert len(saved) == len(results)
        assert all(row.checked_at is not None for row in saved)
        assert all(row.status == PASS for row in saved)
    finally:
        session.close()
