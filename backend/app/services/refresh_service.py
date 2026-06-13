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
from app.models import EtfMaster
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

        report(
            phase="done",
            total=n_total,
            processed=n_total,
            succeeded=n_succeeded,
            failed=n_failed,
            message=f"完成：成功 {n_succeeded} / 失敗 {n_failed}",
        )
        return result
    finally:
        session.close()


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
