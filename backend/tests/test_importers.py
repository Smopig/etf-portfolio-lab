"""Tests for the CSV/Excel import scripts using an in-memory SQLite DB.

We create only the import-target tables (no JSONB columns) directly via
their ORM ``__table__`` metadata, bound to an in-memory SQLite engine, and
monkeypatch ``app.core.database.SessionLocal`` so the scripts under test
write to this engine.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest
from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import sessionmaker

from app.models import (
    DataQualityCheck,
    EtfDividend,
    EtfHolding,
    EtfHoldingSnapshot,
    EtfHoldingSnapshotItem,
    EtfMaster,
    EtfPrice,
    StockIndustry,
)
from scripts import (
    import_dividends,
    import_etf_master,
    import_holdings,
    import_industry,
    import_prices,
)

SAMPLES_DIR = Path("/data/samples")
if not SAMPLES_DIR.exists():
    SAMPLES_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "samples"

TABLES = [
    EtfMaster.__table__,
    EtfHolding.__table__,
    EtfHoldingSnapshot.__table__,
    EtfHoldingSnapshotItem.__table__,
    StockIndustry.__table__,
    EtfPrice.__table__,
    EtfDividend.__table__,
    DataQualityCheck.__table__,
]


@pytest.fixture()
def sqlite_session(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test.db")
    metadata = MetaData()
    for table in TABLES:
        new_table = table.to_metadata(metadata)
        # Postgres-specific server defaults (e.g. "now()") aren't valid
        # SQLite literals; drop them for the test schema.
        for column in new_table.columns:
            if column.server_default is not None:
                column.server_default = None
    metadata.create_all(engine)

    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    monkeypatch.setattr(import_etf_master, "SessionLocal", TestSessionLocal)
    monkeypatch.setattr(import_holdings, "SessionLocal", TestSessionLocal)
    monkeypatch.setattr(import_industry, "SessionLocal", TestSessionLocal)
    monkeypatch.setattr(import_prices, "SessionLocal", TestSessionLocal)
    monkeypatch.setattr(import_dividends, "SessionLocal", TestSessionLocal)

    # Make sure raw-file preservation doesn't fail / pollute real /data/raw
    monkeypatch.setattr(
        "app.utils.importers.RAW_DATA_ROOT", tmp_path / "raw"
    )
    for mod in (import_etf_master, import_holdings, import_industry, import_prices, import_dividends):
        if hasattr(mod, "RAW_DATA_ROOT"):
            monkeypatch.setattr(mod, "RAW_DATA_ROOT", tmp_path / "raw")

    return TestSessionLocal


def _count(session_local, model):
    session = session_local()
    try:
        return session.query(model).count()
    finally:
        session.close()


# ---------------------------------------------------------------------------
# etf_master
# ---------------------------------------------------------------------------

def test_import_etf_master(sqlite_session):
    csv_path = SAMPLES_DIR / "etf_master.csv"
    if not csv_path.exists():
        pytest.skip("sample etf_master.csv not present")

    args = import_etf_master.parse_args([str(csv_path)])
    summary = import_etf_master.run(args)

    assert summary.rows_read > 0
    assert summary.inserted == summary.rows_read
    assert _count(sqlite_session, EtfMaster) == summary.rows_read

    # Re-run: idempotent
    summary2 = import_etf_master.run(args)
    assert summary2.inserted == 0
    assert summary2.skipped_existing == summary.rows_read
    assert _count(sqlite_session, EtfMaster) == summary.rows_read


# ---------------------------------------------------------------------------
# stock_industry
# ---------------------------------------------------------------------------

def test_import_industry(sqlite_session):
    csv_path = SAMPLES_DIR / "stock_industry.csv"
    if not csv_path.exists():
        pytest.skip("sample stock_industry.csv not present")

    args = import_industry.parse_args([str(csv_path)])
    summary = import_industry.run(args)

    assert summary.rows_read > 0
    assert summary.inserted == summary.rows_read
    assert _count(sqlite_session, StockIndustry) == summary.rows_read

    summary2 = import_industry.run(args)
    assert summary2.inserted == 0
    assert summary2.skipped_existing == summary.rows_read
    assert _count(sqlite_session, StockIndustry) == summary.rows_read


# ---------------------------------------------------------------------------
# etf_holdings + snapshots
# ---------------------------------------------------------------------------

def test_import_holdings_with_snapshots(sqlite_session):
    csv_path = SAMPLES_DIR / "0050_holdings.csv"
    if not csv_path.exists():
        pytest.skip("sample 0050_holdings.csv not present")

    args = import_holdings.parse_args([str(csv_path)])
    summary = import_holdings.run(args)

    assert summary.rows_read > 0
    assert summary.inserted == summary.rows_read
    assert _count(sqlite_session, EtfHolding) == summary.rows_read
    assert _count(sqlite_session, EtfHoldingSnapshot) >= 1
    assert _count(sqlite_session, EtfHoldingSnapshotItem) == summary.rows_read

    # Re-run: idempotent for current holdings, snapshot, and snapshot items.
    snapshot_count_before = _count(sqlite_session, EtfHoldingSnapshot)
    item_count_before = _count(sqlite_session, EtfHoldingSnapshotItem)
    summary2 = import_holdings.run(args)
    assert summary2.inserted == 0
    assert summary2.skipped_existing == summary.rows_read
    assert _count(sqlite_session, EtfHolding) == summary.rows_read
    # Snapshot rows themselves should be reused (same key), not duplicated
    assert _count(sqlite_session, EtfHoldingSnapshot) == snapshot_count_before
    # Snapshot items must not be duplicated on re-import
    assert _count(sqlite_session, EtfHoldingSnapshotItem) == item_count_before


def test_import_holdings_reimport_no_duplicate_snapshot_items(sqlite_session):
    csv_path = SAMPLES_DIR / "0050_holdings.csv"
    if not csv_path.exists():
        pytest.skip("sample 0050_holdings.csv not present")

    args = import_holdings.parse_args([str(csv_path)])

    summary1 = import_holdings.run(args)
    item_count_after_first = _count(sqlite_session, EtfHoldingSnapshotItem)
    assert item_count_after_first == summary1.rows_read

    summary2 = import_holdings.run(args)
    item_count_after_second = _count(sqlite_session, EtfHoldingSnapshotItem)

    assert item_count_after_second == item_count_after_first

    session = sqlite_session()
    try:
        snapshots = session.query(EtfHoldingSnapshot).all()
        assert len(snapshots) == 1
        snap = snapshots[0]
        assert (
            session.query(EtfHoldingSnapshot)
            .filter_by(
                etf_symbol=snap.etf_symbol,
                snapshot_date=snap.snapshot_date,
                source_name=snap.source_name,
            )
            .count()
            == 1
        )
    finally:
        session.close()


# ---------------------------------------------------------------------------
# etf_prices
# ---------------------------------------------------------------------------

def test_import_prices(sqlite_session, tmp_path):
    csv_path = SAMPLES_DIR / "0050_prices.csv"
    if not csv_path.exists():
        # Generate a small temp CSV
        csv_path = tmp_path / "0050_prices.csv"
        csv_path.write_text(
            "etf_symbol,trade_date,open,high,low,close,adjusted_close,volume,turnover,source_name,source_url\n"
            "0050,2026-05-06,186.50,187.20,186.30,186.80,186.80,8500000,1587400000,Yahoo Finance,https://finance.yahoo.com\n"
            "0050,2026-05-07,187.00,187.65,186.95,187.30,187.30,9200000,1724396000,Yahoo Finance,https://finance.yahoo.com\n",
            encoding="utf-8",
        )

    args = import_prices.parse_args([str(csv_path)])
    summary = import_prices.run(args)

    assert summary.rows_read > 0
    assert summary.inserted == summary.rows_read
    assert _count(sqlite_session, EtfPrice) == summary.rows_read

    summary2 = import_prices.run(args)
    assert summary2.inserted == 0
    assert summary2.skipped_existing == summary.rows_read
    assert _count(sqlite_session, EtfPrice) == summary.rows_read


# ---------------------------------------------------------------------------
# etf_dividends
# ---------------------------------------------------------------------------

def test_import_dividends(sqlite_session, tmp_path):
    csv_path = SAMPLES_DIR / "0050_dividends.csv"
    if not csv_path.exists():
        csv_path = tmp_path / "0050_dividends.csv"
        csv_path.write_text(
            "etf_symbol,ex_dividend_date,payment_date,dividend_amount,dividend_yield,source_name,source_url\n"
            "0050,2024-07-16,2024-08-15,2.10,1.18,公開資訊觀測站,https://mops.twse.com.tw\n"
            "0050,2024-12-24,2025-01-30,2.45,1.35,公開資訊觀測站,https://mops.twse.com.tw\n",
            encoding="utf-8",
        )

    args = import_dividends.parse_args([str(csv_path)])
    summary = import_dividends.run(args)

    assert summary.rows_read > 0
    assert summary.inserted == summary.rows_read
    assert _count(sqlite_session, EtfDividend) == summary.rows_read

    summary2 = import_dividends.run(args)
    assert summary2.inserted == 0
    assert summary2.skipped_existing == summary.rows_read
    assert _count(sqlite_session, EtfDividend) == summary.rows_read


# ---------------------------------------------------------------------------
# cp950-encoded CSV
# ---------------------------------------------------------------------------

def test_import_cp950_csv(sqlite_session, tmp_path):
    csv_path = tmp_path / "stock_industry_cp950.csv"
    content = (
        "stock_symbol,stock_name,market,industry_level_1,industry_level_2,"
        "industry_level_3,source_name,source_url\n"
        "2330,台積電,上市,半導體,積體電路製造,晶圓代工,台灣證券交易所,https://www.twse.com.tw\n"
        "2317,鴻海,上市,電子,電子零組件,電源供應器,台灣證券交易所,https://www.twse.com.tw\n"
    )
    csv_path.write_bytes(content.encode("cp950"))

    args = import_industry.parse_args([str(csv_path)])
    summary = import_industry.run(args)

    assert summary.rows_read == 2
    assert summary.inserted == 2
    assert _count(sqlite_session, StockIndustry) == 2

    session = sqlite_session()
    try:
        row = session.query(StockIndustry).filter_by(stock_symbol="2330").first()
        assert row.stock_name == "台積電"
    finally:
        session.close()


# ---------------------------------------------------------------------------
# dry-run
# ---------------------------------------------------------------------------

def test_dry_run_writes_nothing(sqlite_session, tmp_path):
    csv_path = tmp_path / "etf_master_dry.csv"
    csv_path.write_text(
        "symbol,name,issuer,confidence_level\n"
        "0050,元大台灣50,元大投信,高\n",
        encoding="utf-8",
    )

    args = import_etf_master.parse_args([str(csv_path), "--dry-run"])
    summary = import_etf_master.run(args)

    assert summary.dry_run is True
    assert summary.rows_read == 1
    assert summary.inserted == 1  # would-be inserted, counted but not written
    assert _count(sqlite_session, EtfMaster) == 0
