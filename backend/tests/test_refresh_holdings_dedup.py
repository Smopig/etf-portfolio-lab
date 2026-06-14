"""Regression tests for _replace_holdings_for_snapshot duplicate handling.

A single ETF can legitimately hold several futures contracts sharing one code
(e.g. TX 臺股期貨 across expiries). Such records collide on the unique
constraint (etf_symbol, holding_date, asset_symbol). Before the fix this raised
an IntegrityError that poisoned the whole refresh session and cascade-failed
every subsequent ETF (observed: 5 succeeded / 338 failed). The persist helper
now collapses duplicates, summing weight/shares.
"""

from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import sessionmaker

from app.models import EtfHolding, EtfHoldingSnapshot, EtfHoldingSnapshotItem
from app.services.refresh_service import _replace_holdings_for_snapshot

TABLES = [
    EtfHolding.__table__,
    EtfHoldingSnapshot.__table__,
    EtfHoldingSnapshotItem.__table__,
]

HOLDING_DATE = dt.date(2026, 6, 12)


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


class _Result:
    """Minimal stand-in for ProviderResult."""

    def __init__(self, records):
        self.records = records
        self.data_date = HOLDING_DATE
        self.source_name = "元大投信"
        self.source_url = "https://example/api"


def _rec(asset_symbol, name, weight, shares):
    return {
        "etf_symbol": "0050",
        "holding_date": HOLDING_DATE,
        "asset_symbol": asset_symbol,
        "asset_name": name,
        "weight": weight,
        "shares": shares,
        "source_name": "元大投信",
        "source_url": "https://example/api",
        "fetched_at": dt.datetime(2026, 6, 14, 0, 0, 0),
        "confidence_level": "HIGH",
    }


def test_duplicate_asset_symbols_collapsed_and_summed(sqlite_session):
    session = sqlite_session()
    try:
        result = _Result(
            [
                _rec("2330", "台積電", 57.95, 522327548),
                _rec("TX", "臺股期貨", 0.15, 350),  # duplicate code, expiry A
                _rec("TX", "臺股期貨", 0.11, 268),  # duplicate code, expiry B
            ]
        )
        # Must not raise IntegrityError.
        _replace_holdings_for_snapshot(session, "0050", result)
        session.commit()

        rows = session.query(EtfHolding).filter_by(etf_symbol="0050").all()
        by_symbol = {r.asset_symbol: r for r in rows}
        # Exactly one TX row, weights and shares summed.
        assert sorted(by_symbol) == ["2330", "TX"]
        assert float(by_symbol["TX"].weight) == pytest.approx(0.26)
        assert float(by_symbol["TX"].shares) == pytest.approx(618)
    finally:
        session.close()
