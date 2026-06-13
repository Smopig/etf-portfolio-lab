"""Orchestrator for provider-based data fetches (Phase 12).

``run_fetch`` calls a :class:`BaseDataProvider`, routes any returned records
through the same upsert logic used by ``scripts/import_*.py`` (idempotent
insert-if-not-exists keyed the same way as those scripts), records a
``FetchLog`` row, and optionally runs the relevant data-quality checks.

Per CLAUDE.md §7: no record is ever fabricated here -- only what the
provider returned (with its source metadata) is written. If the provider
reports ``errors`` and no records, the FetchLog status is "error" / "empty"
and nothing is written to the dataset tables.

``persist=False`` performs no DB writes at all (no FetchLog row, no dataset
rows) -- mirrors ``backtest_service.run_backtest_from_db``.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from app.models import EtfHolding, EtfPrice, FetchLog
from app.providers.data.base import BaseDataProvider
from app.utils.data_quality import run_and_report
from app.utils.importers import _parse_date

STATUS_SUCCESS = "success"
STATUS_ERROR = "error"
STATUS_EMPTY = "empty"


def _upsert_price_row(session: Session, record: dict) -> bool:
    """Insert an EtfPrice row if (etf_symbol, trade_date, source_name) is new.

    Mirrors the unique-key/skip logic in ``scripts/import_prices.py``.
    Returns True if a row was inserted.
    """
    etf_symbol = record.get("etf_symbol")
    trade_date = _parse_date(record.get("trade_date"))
    source_name = record.get("source_name")

    if not etf_symbol or trade_date is None:
        return False

    exists = (
        session.query(EtfPrice)
        .filter_by(etf_symbol=etf_symbol, trade_date=trade_date, source_name=source_name)
        .first()
    )
    if exists:
        return False

    session.add(
        EtfPrice(
            etf_symbol=etf_symbol,
            trade_date=trade_date,
            open=record.get("open"),
            high=record.get("high"),
            low=record.get("low"),
            close=record.get("close"),
            adjusted_close=record.get("adjusted_close"),
            volume=record.get("volume"),
            turnover=record.get("turnover"),
            source_name=source_name,
            source_url=record.get("source_url"),
            fetched_at=dt.datetime.utcnow(),
        )
    )
    return True


def _upsert_holding_row(session: Session, record: dict) -> bool:
    """Insert an EtfHolding row if (etf_symbol, holding_date, asset_symbol) is new.

    Mirrors the unique-key/skip logic in ``scripts/import_holdings.py``
    (current-holdings table only; snapshot tables are out of scope here).
    Returns True if a row was inserted.
    """
    etf_symbol = record.get("etf_symbol")
    holding_date = _parse_date(record.get("holding_date"))
    asset_symbol = record.get("asset_symbol")

    if not etf_symbol or holding_date is None:
        return False

    exists = (
        session.query(EtfHolding)
        .filter_by(etf_symbol=etf_symbol, holding_date=holding_date, asset_symbol=asset_symbol)
        .first()
    )
    if exists:
        return False

    session.add(
        EtfHolding(
            etf_symbol=etf_symbol,
            holding_date=holding_date,
            asset_symbol=asset_symbol,
            asset_name=record.get("asset_name"),
            asset_type=record.get("asset_type"),
            weight=record.get("weight"),
            shares=record.get("shares"),
            market_value=record.get("market_value"),
            source_name=record.get("source_name"),
            source_url=record.get("source_url"),
            fetched_at=dt.datetime.utcnow(),
            confidence_level=record.get("confidence_level"),
        )
    )
    return True


_UPSERT_FUNCS = {
    "etf_prices": _upsert_price_row,
    "etf_holdings": _upsert_holding_row,
}


def run_fetch(
    db: Session,
    provider: BaseDataProvider,
    dataset_type: str,
    persist: bool = True,
    **params,
) -> dict:
    """Run a provider fetch and (optionally) persist results + a FetchLog row.

    Returns a summary dict with keys: status, rows_fetched, rows_inserted,
    errors, source_name, source_url, data_date, quality_summary.
    """
    started_at = dt.datetime.utcnow()
    params.setdefault("dataset_type", dataset_type)
    result = provider.fetch(**params)

    rows_fetched = len(result.records)
    rows_inserted = 0
    quality_summary: str | None = None

    if rows_fetched == 0:
        status = STATUS_ERROR if result.errors else STATUS_EMPTY
    else:
        status = STATUS_SUCCESS
        upsert_fn = _UPSERT_FUNCS.get(dataset_type)
        if upsert_fn is not None and persist:
            for record in result.records:
                if upsert_fn(db, record):
                    rows_inserted += 1
            db.commit()
            quality_summary = run_and_report(db, dataset_type)
        elif upsert_fn is None:
            status = STATUS_ERROR
            result.errors.append(
                f"no upsert path registered for dataset_type '{dataset_type}'"
            )

    finished_at = dt.datetime.utcnow()

    if persist:
        log = FetchLog(
            provider_name=getattr(provider, "name", "unknown"),
            dataset_type=dataset_type,
            status=status,
            rows_fetched=rows_fetched,
            rows_inserted=rows_inserted,
            source_url=result.source_url,
            data_date=result.data_date,
            message="; ".join(result.errors) if result.errors else None,
            started_at=started_at,
            finished_at=finished_at,
        )
        db.add(log)
        db.commit()

    return {
        "status": status,
        "provider": getattr(provider, "name", "unknown"),
        "dataset_type": dataset_type,
        "rows_fetched": rows_fetched,
        "rows_inserted": rows_inserted,
        "errors": result.errors,
        "source_name": result.source_name,
        "source_url": result.source_url,
        "data_date": result.data_date,
        "reliability_level": result.reliability_level,
        "quality_summary": quality_summary,
    }
