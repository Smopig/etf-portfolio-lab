"""Background "full refresh" job: ETF list + recent prices (CLAUDE.md §7).

Provides the reusable core used by both ``scripts/fetch_all.py`` (CLI) and
the ``/api/data/refresh`` endpoints (background thread). Real network fetches
only -- no fabricated data.

A single module-level ``RefreshJob`` singleton tracks the state of the most
recent (or in-progress) refresh run, guarded by a lock so at most one refresh
runs at a time.
"""

from __future__ import annotations

import datetime as dt
import threading
import time
from collections.abc import Callable

from app.core.database import SessionLocal
from app.models import (
    EtfDividend,
    EtfDividendFrequencyOverride,
    EtfHolding,
    EtfHoldingSnapshot,
    EtfHoldingSnapshotItem,
    EtfMaster,
    EtfPrice,
)
from app.services.dividend_ranking_service import classify_frequency
from app.providers.data.factory import get_data_provider
from app.services.data_fetch_service import run_fetch

ProgressCallback = Callable[[dict], None]


def run_full_fetch(
    progress: ProgressCallback | None = None,
    *,
    prices: bool = True,
    price_range: str = "1y",
    limit: int | None = None,
    market: str = "both",
    holdings: bool = True,
    dividends: bool = True,
) -> dict:
    """Run the full ETF-list + prices fetch, creating its own DB session.

    Mirrors ``scripts/fetch_all.py``'s flow: fetch the ETF master list (TWSE
    ISIN listing pages), then -- unless ``prices`` is False -- fetch recent
    daily prices for each symbol from Yahoo Finance.

    ``progress``, if given, is called with a state dict as the job advances:
    ``{"phase": "listing"|"prices"|"done", "total": int, "processed": int,
    "succeeded": int, "failed": int, "message": str}``.

    Returns a summary dict.
    """

    def report(**kwargs: object) -> None:
        if progress is not None:
            progress(dict(kwargs))

    session = SessionLocal()
    try:
        report(phase="listing", total=0, processed=0, succeeded=0, failed=0, message="抓取 ETF 清單中...")

        provider = get_data_provider("twse-etf-list")
        list_summary = run_fetch(session, provider, "etf_master", persist=True, market=market)

        symbols = [s for (s,) in session.query(EtfMaster.symbol).order_by(EtfMaster.symbol).all()]

        result: dict = {
            "list_summary": list_summary,
            "symbols_total": len(symbols),
            "prices": None,
        }

        if not prices:
            report(
                phase="done",
                total=0,
                processed=0,
                succeeded=0,
                failed=0,
                message="完成（未抓取價格）",
            )
            return result

        if limit is not None:
            symbols = symbols[:limit]

        n_total = len(symbols)
        n_succeeded = 0
        n_failed = 0

        report(
            phase="prices",
            total=n_total,
            processed=0,
            succeeded=0,
            failed=0,
            message=f"抓取價格中 0/{n_total}",
        )

        for i, symbol in enumerate(symbols, start=1):
            price_provider = get_data_provider("yahoo-finance")
            ok = False
            try:
                for suffix in (".TW", ".TWO"):
                    yahoo_symbol = f"{symbol}{suffix}"
                    summary = run_fetch(
                        session,
                        price_provider,
                        "etf_prices",
                        persist=True,
                        symbol=yahoo_symbol,
                        etf_symbol=symbol,
                        range=price_range,
                    )
                    if summary["status"] == "success" and summary["rows_fetched"] > 0:
                        ok = True
                        break
            except Exception:  # noqa: BLE001
                ok = False

            if ok:
                n_succeeded += 1
            else:
                n_failed += 1

            report(
                phase="prices",
                total=n_total,
                processed=i,
                succeeded=n_succeeded,
                failed=n_failed,
                message=f"抓取價格中 {i}/{n_total}",
            )

            time.sleep(0.4)

        result["prices"] = {
            "symbols_processed": n_total,
            "succeeded": n_succeeded,
            "failed": n_failed,
        }

        done_parts = [f"價格 成功 {n_succeeded} / 失敗 {n_failed}"]

        if holdings:
            holdings_summary = _run_holdings_phase(session, report)
            result["holdings"] = holdings_summary
            done_parts.append(
                f"成分股 成功 {holdings_summary['succeeded']} / "
                f"失敗 {holdings_summary['failed']}"
            )

        if dividends:
            dividends_summary = _run_dividends_phase(session, report)
            result["dividends"] = dividends_summary
            done_parts.append(
                f"配息 成功 {dividends_summary['succeeded']} / "
                f"失敗 {dividends_summary['failed']}"
            )

        report(
            phase="done",
            total=n_total,
            processed=n_total,
            succeeded=n_succeeded,
            failed=n_failed,
            message="完成：" + "；".join(done_parts),
        )
        return result
    finally:
        session.close()


def _is_yuanta(issuer: str | None) -> bool:
    """True if the ETF issuer is Yuanta (元大投信).

    Matches on the Chinese name fragment "元大" or the English "yuanta"
    (case-insensitive). Missing/ambiguous issuers return False so the caller
    defaults to the Yahoo provider.
    """
    if not issuer:
        return False
    low = issuer.lower()
    return "元大" in issuer or "yuanta" in low


def _run_holdings_phase(session, report) -> dict:
    """Holdings phase: fetch Yahoo holdings for active ETFs with price data.

    For each ETF:
    - Replace existing rows with the same (etf_symbol, holding_date, asset_symbol)
      (delete-then-insert for that snapshot date).
    - Insert one EtfHoldingSnapshot row.

    On provider failure or empty result: DO NOT delete existing rows.
    Per-ETF failures never abort the job.
    """
    # ETFs that are active AND have at least one price row, with issuer so we
    # can pick the best holdings provider per ETF.
    rows = (
        session.query(EtfMaster.symbol, EtfMaster.issuer)
        .filter(EtfMaster.is_active.is_(True))
        .filter(
            session.query(EtfPrice.id)
            .filter(EtfPrice.etf_symbol == EtfMaster.symbol)
            .exists()
        )
        .order_by(EtfMaster.symbol)
        .all()
    )
    symbols = [(s, issuer) for (s, issuer) in rows]
    n_total = len(symbols)
    n_succ = 0
    n_fail = 0

    report(
        phase="holdings",
        total=n_total,
        processed=0,
        succeeded=0,
        failed=0,
        message=f"抓取成分股中 0/{n_total}",
    )

    yahoo_provider = get_data_provider("yahoo-holdings")
    yuanta_provider = get_data_provider("yuanta-holdings")

    for i, (symbol, issuer) in enumerate(symbols, start=1):
        ok = False
        try:
            result = None
            # Yuanta-issued ETFs: use the issuer's authoritative full-list API
            # (HIGH confidence). Fall back to Yahoo top-10 if it yields nothing.
            if _is_yuanta(issuer):
                result = yuanta_provider.fetch(symbol=symbol)
                if not result.records:
                    result = yahoo_provider.fetch(symbol=symbol)
            else:
                result = yahoo_provider.fetch(symbol=symbol)
            if result.records:
                _replace_holdings_for_snapshot(session, symbol, result)
                ok = True
        except Exception:  # noqa: BLE001
            # Roll back so a failed ETF (e.g. an integrity error) does NOT
            # poison the session and cascade-fail every subsequent ETF.
            session.rollback()
            ok = False

        if ok:
            n_succ += 1
        else:
            n_fail += 1

        report(
            phase="holdings",
            total=n_total,
            processed=i,
            succeeded=n_succ,
            failed=n_fail,
            message=f"抓取成分股中 {i}/{n_total}",
        )
        time.sleep(0.4)

    return {
        "symbols_processed": n_total,
        "succeeded": n_succ,
        "failed": n_fail,
    }


def _replace_holdings_for_snapshot(session, symbol: str, result) -> None:
    """Replace rows for each (etf_symbol, holding_date, asset_symbol) tuple
    present in ``result.records`` and create a snapshot. Existing rows for
    OTHER holding_dates are untouched. Commits at the end.
    """
    if not result.records:
        return

    # Snapshot date = max holding_date in records (or today).
    snapshot_date = result.data_date or dt.date.today()
    fetched_at = dt.datetime.utcnow()

    # Delete the exact rows we're about to (re)insert, keyed by unique constraint.
    keys_by_date: dict[dt.date, list[str]] = {}
    for rec in result.records:
        d = rec.get("holding_date")
        if isinstance(d, dt.datetime):
            d = d.date()
        if not isinstance(d, dt.date):
            continue
        keys_by_date.setdefault(d, []).append(str(rec.get("asset_symbol")))

    for d, asset_syms in keys_by_date.items():
        session.query(EtfHolding).filter(
            EtfHolding.etf_symbol == symbol,
            EtfHolding.holding_date == d,
            EtfHolding.asset_symbol.in_(asset_syms),
        ).delete(synchronize_session=False)

    # Collapse duplicate (holding_date, asset_symbol) records before insert.
    # A single ETF can legitimately hold several futures contracts that share
    # one code (e.g. TX 臺股期貨 across expiries); these would otherwise violate
    # the unique constraint. Sum their weight/shares so total exposure is kept.
    deduped: dict[tuple, dict] = {}
    for rec in result.records:
        d = rec.get("holding_date")
        if isinstance(d, dt.datetime):
            d = d.date()
        asset_symbol = (
            str(rec.get("asset_symbol")) if rec.get("asset_symbol") is not None else None
        )
        key = (d, asset_symbol)
        if key in deduped:
            prev = deduped[key]
            if rec.get("weight") is not None:
                prev["weight"] = (prev.get("weight") or 0) + rec["weight"]
            if rec.get("shares") is not None:
                prev["shares"] = (prev.get("shares") or 0) + rec["shares"]
        else:
            merged = dict(rec)
            merged["holding_date"] = d
            merged["asset_symbol"] = asset_symbol
            deduped[key] = merged

    # Insert fresh rows.
    for rec in deduped.values():
        session.add(
            EtfHolding(
                etf_symbol=symbol,
                holding_date=rec.get("holding_date"),
                asset_symbol=rec.get("asset_symbol"),
                asset_name=rec.get("asset_name"),
                weight=rec.get("weight"),
                shares=rec.get("shares"),
                source_name=rec.get("source_name"),
                source_url=rec.get("source_url"),
                fetched_at=rec.get("fetched_at") or fetched_at,
                confidence_level=rec.get("confidence_level"),
            )
        )

    # Snapshot row (unique on etf_symbol, snapshot_date, source_name).
    existing_snap = (
        session.query(EtfHoldingSnapshot)
        .filter_by(
            etf_symbol=symbol,
            snapshot_date=snapshot_date,
            source_name=result.source_name,
        )
        .first()
    )
    if existing_snap is None:
        snap = EtfHoldingSnapshot(
            etf_symbol=symbol,
            snapshot_date=snapshot_date,
            source_name=result.source_name,
            source_url=result.source_url,
            fetched_at=fetched_at,
        )
        session.add(snap)
        session.flush()
        snap_id = snap.id
    else:
        existing_snap.source_url = result.source_url
        existing_snap.fetched_at = fetched_at
        snap_id = existing_snap.id
        # Clear old items for this snapshot to avoid duplicates on re-run.
        session.query(EtfHoldingSnapshotItem).filter_by(snapshot_id=snap_id).delete(
            synchronize_session=False
        )

    for rec in result.records:
        session.add(
            EtfHoldingSnapshotItem(
                snapshot_id=snap_id,
                asset_symbol=str(rec.get("asset_symbol")) if rec.get("asset_symbol") is not None else None,
                asset_name=rec.get("asset_name"),
                weight=rec.get("weight"),
                shares=rec.get("shares"),
            )
        )

    session.commit()


def _run_dividends_phase(session, report) -> dict:
    """Dividends phase: fetch Yahoo dividends for active ETFs with price data.

    For each ETF:
    - Replace existing rows keyed by (etf_symbol, ex_dividend_date, source_name)
      with the freshly fetched paid distributions (upcoming rows are NOT
      persisted, so TTM logic never sees unpaid distributions).
    - Set EtfMaster.dividend_frequency from classification IF currently null
      and no override exists (never overwrite an existing value / override).

    On provider failure or empty result: DO NOT delete existing rows.
    Per-ETF failures never abort the job (per-ETF rollback).
    """
    symbols = [
        s
        for (s,) in session.query(EtfMaster.symbol)
        .filter(EtfMaster.is_active.is_(True))
        .filter(
            session.query(EtfPrice.id)
            .filter(EtfPrice.etf_symbol == EtfMaster.symbol)
            .exists()
        )
        .order_by(EtfMaster.symbol)
        .all()
    ]
    n_total = len(symbols)
    n_succ = 0
    n_fail = 0

    report(
        phase="dividends",
        total=n_total,
        processed=0,
        succeeded=0,
        failed=0,
        message=f"抓取配息中 0/{n_total}",
    )

    provider = get_data_provider("yahoo-dividends")

    for i, symbol in enumerate(symbols, start=1):
        ok = False
        try:
            result = provider.fetch(symbol=symbol)
            if result.records:
                _replace_dividends(session, symbol, result)
                _maybe_set_frequency(session, symbol, result)
                session.commit()
                ok = True
        except Exception:  # noqa: BLE001
            # Roll back so a failed ETF does NOT poison the session and
            # cascade-fail every subsequent ETF.
            session.rollback()
            ok = False

        if ok:
            n_succ += 1
        else:
            n_fail += 1

        report(
            phase="dividends",
            total=n_total,
            processed=i,
            succeeded=n_succ,
            failed=n_fail,
            message=f"抓取配息中 {i}/{n_total}",
        )
        time.sleep(0.4)

    return {
        "symbols_processed": n_total,
        "succeeded": n_succ,
        "failed": n_fail,
    }


def _replace_dividends(session, symbol: str, result) -> None:
    """Replace dividend rows for this ETF keyed by the unique constraint.

    Only paid (non-upcoming) distributions are persisted so TTM never sees
    unpaid rows. Does NOT commit (the caller commits once per ETF).
    """
    paid = [rec for rec in result.records if not rec.get("is_upcoming")]
    if not paid:
        return

    # Delete the exact rows we're about to (re)insert, keyed by the unique
    # constraint (etf_symbol, ex_dividend_date, source_name).
    keys = {
        (rec.get("ex_dividend_date"), rec.get("source_name"))
        for rec in paid
        if rec.get("ex_dividend_date") is not None
    }
    for ex_date, source_name in keys:
        session.query(EtfDividend).filter(
            EtfDividend.etf_symbol == symbol,
            EtfDividend.ex_dividend_date == ex_date,
            EtfDividend.source_name == source_name,
        ).delete(synchronize_session=False)

    # Collapse duplicate (ex_dividend_date, source_name) records.
    deduped: dict[tuple, dict] = {}
    for rec in paid:
        ex_date = rec.get("ex_dividend_date")
        if ex_date is None:
            continue
        deduped[(ex_date, rec.get("source_name"))] = rec

    for rec in deduped.values():
        session.add(
            EtfDividend(
                etf_symbol=symbol,
                ex_dividend_date=rec.get("ex_dividend_date"),
                payment_date=rec.get("payment_date"),
                dividend_amount=rec.get("dividend_amount"),
                source_name=rec.get("source_name"),
                source_url=rec.get("source_url"),
                fetched_at=rec.get("fetched_at"),
            )
        )


def _maybe_set_frequency(session, symbol: str, result) -> None:
    """Set EtfMaster.dividend_frequency from classification if currently null.

    Never overwrites an existing value, and never overrides a manual
    EtfDividendFrequencyOverride row.
    """
    master = (
        session.query(EtfMaster).filter(EtfMaster.symbol == symbol).first()
    )
    if master is None or master.dividend_frequency:
        return

    has_override = (
        session.query(EtfDividendFrequencyOverride.id)
        .filter(EtfDividendFrequencyOverride.etf_symbol == symbol)
        .first()
        is not None
    )
    if has_override:
        return

    paid = [rec for rec in result.records if not rec.get("is_upcoming")]
    if not paid:
        return
    master.dividend_frequency = classify_frequency(paid)


class RefreshJob:
    """Thread-safe singleton tracking the state of the background refresh."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state: dict = {
            "running": False,
            "phase": "idle",
            "total": 0,
            "processed": 0,
            "succeeded": 0,
            "failed": 0,
            "started_at": None,
            "finished_at": None,
            "message": "尚未執行",
        }

    def get_status(self) -> dict:
        with self._lock:
            return dict(self._state)

    def _update(self, **kwargs: object) -> None:
        with self._lock:
            self._state.update(kwargs)

    def start(self, **opts: object) -> tuple[str, dict]:
        with self._lock:
            if self._state["running"]:
                return "already_running", dict(self._state)

            self._state.update(
                running=True,
                phase="listing",
                total=0,
                processed=0,
                succeeded=0,
                failed=0,
                started_at=dt.datetime.utcnow().isoformat(),
                finished_at=None,
                message="抓取 ETF 清單中...",
            )
            state_copy = dict(self._state)

        def progress(update: dict) -> None:
            self._update(**update)

        def worker() -> None:
            try:
                run_full_fetch(progress=progress, **opts)
            except Exception as exc:  # noqa: BLE001
                self._update(
                    phase="error",
                    message=f"發生錯誤：{exc}",
                    finished_at=dt.datetime.utcnow().isoformat(),
                )
            finally:
                with self._lock:
                    self._state["running"] = False
                    if self._state.get("finished_at") is None:
                        self._state["finished_at"] = dt.datetime.utcnow().isoformat()

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        return "started", state_copy


# Module-level singleton.
_job = RefreshJob()


def start_refresh(**opts: object) -> tuple[str, dict]:
    return _job.start(**opts)


def get_status() -> dict:
    return _job.get_status()
