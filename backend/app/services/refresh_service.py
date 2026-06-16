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
    listing: bool = True,
    prices: bool = True,
    price_range: str = "1y",
    limit: int | None = None,
    market: str = "both",
    holdings: bool = True,
    dividends: bool = True,
    profile: bool = True,
) -> dict:
    """Run per-phase ETF data fetches, creating its own DB session.

    Phases run in order: listing -> prices -> holdings -> dividends. Each phase
    is independently gated by its flag and NEVER short-circuits a later phase,
    so e.g. "only dividends" (``listing=prices=holdings=False, dividends=True``)
    works. The symbol list used by later phases comes from the freshly fetched
    TWSE master list when ``listing`` is True, otherwise from the existing
    ``EtfMaster`` rows already in the DB.

    ``progress``, if given, is called with a state dict as the job advances:
    ``{"phase": "listing"|"prices"|"holdings"|"dividends"|"done", "total": int,
    "processed": int, "succeeded": int, "failed": int, "message": str}``.

    Returns a summary dict.
    """

    def report(**kwargs: object) -> None:
        if progress is not None:
            progress(dict(kwargs))

    session = SessionLocal()
    try:
        result: dict = {
            "list_summary": None,
            "symbols_total": 0,
            "prices": None,
            "holdings": None,
            "dividends": None,
            "profile": None,
        }
        done_parts: list[str] = []

        # ── Phase: listing (ETF master list) ──────────────────────────────
        if listing:
            report(
                phase="listing",
                total=0,
                processed=0,
                succeeded=0,
                failed=0,
                message="抓取 ETF 清單中...",
            )
            provider = get_data_provider("twse-etf-list")
            list_summary = run_fetch(
                session, provider, "etf_master", persist=True, market=market
            )
            result["list_summary"] = list_summary
            done_parts.append("ETF 清單已更新")

        symbols = [
            s
            for (s,) in session.query(EtfMaster.symbol)
            .order_by(EtfMaster.symbol)
            .all()
        ]
        result["symbols_total"] = len(symbols)

        # Edge case: nothing to work with (e.g. listing skipped + empty DB).
        if not symbols and (prices or holdings or dividends):
            report(
                phase="done",
                total=0,
                processed=0,
                succeeded=0,
                failed=0,
                message="資料庫中沒有任何 ETF，請先更新 ETF 清單",
            )
            return result

        # ── Phase: prices ─────────────────────────────────────────────────
        if prices:
            price_symbols = symbols[:limit] if limit is not None else symbols
            n_total = len(price_symbols)
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

            for i, symbol in enumerate(price_symbols, start=1):
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
            done_parts.append(f"價格 成功 {n_succeeded} / 失敗 {n_failed}")

        # ── Phase: holdings ───────────────────────────────────────────────
        if holdings:
            holdings_summary = _run_holdings_phase(session, report)
            result["holdings"] = holdings_summary
            done_parts.append(
                f"成分股 成功 {holdings_summary['succeeded']} / "
                f"失敗 {holdings_summary['failed']}"
            )

        # ── Phase: profile (Yuanta static fund profiles) ──────────────────
        if profile:
            profile_summary = _run_profile_phase(session, report)
            result["profile"] = profile_summary
            done_parts.append(
                f"基本資料 更新 {profile_summary['updated']} / "
                f"略過 {profile_summary['skipped']}"
            )

        # ── Phase: dividends ──────────────────────────────────────────────
        if dividends:
            dividends_summary = _run_dividends_phase(session, report)
            result["dividends"] = dividends_summary
            done_parts.append(
                f"配息 成功 {dividends_summary['succeeded']} / "
                f"失敗 {dividends_summary['failed']}"
            )

        report(
            phase="done",
            total=0,
            processed=0,
            succeeded=0,
            failed=0,
            message="完成：" + "；".join(done_parts) if done_parts else "完成",
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


def _is_fuhua(issuer: str | None) -> bool:
    """True if the ETF issuer is Fuhua (復華投信).

    Matches the Chinese name fragment "復華" or the English "fuhua"/"fh"
    (case-insensitive). Missing/ambiguous issuers return False.
    """
    if not issuer:
        return False
    low = issuer.lower()
    return "復華" in issuer or "fuhua" in low


def _is_fubon(issuer: str | None) -> bool:
    """True if the ETF issuer is Fubon (富邦投信)."""
    if not issuer:
        return False
    low = issuer.lower()
    return "富邦" in issuer or "fubon" in low


def _is_cathay(issuer: str | None) -> bool:
    """True if the ETF issuer is Cathay (國泰投信)."""
    if not issuer:
        return False
    low = issuer.lower()
    return "國泰" in issuer or "cathay" in low


def _is_capital(issuer: str | None) -> bool:
    """True if the ETF issuer is Capital (群益投信)."""
    if not issuer:
        return False
    low = issuer.lower()
    return "群益" in issuer or "capital" in low


def _is_kgi(issuer: str | None) -> bool:
    """True if the ETF issuer is KGI (凱基投信)."""
    if not issuer:
        return False
    low = issuer.lower()
    return "凱基" in issuer or "kgi" in low


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
    fuhua_provider = get_data_provider("fuhua-holdings")
    fubon_provider = get_data_provider("fubon-holdings")
    cathay_provider = get_data_provider("cathay-holdings")
    capital_provider = get_data_provider("capital-holdings")
    kgi_provider = get_data_provider("kgi-holdings")

    for i, (symbol, issuer) in enumerate(symbols, start=1):
        ok = False
        try:
            result = None
            # Pick the cascade of full-list providers to try, ending with the
            # Yahoo top-10 fallback. Each issuer API only returns data for its
            # own funds (a non-matching symbol yields empty), so when the issuer
            # is unknown (many rows have a null issuer) we try every issuer API
            # in turn. Known issuers skip straight to their own API to avoid
            # wasted calls.
            if issuer is None:
                chain = [
                    yuanta_provider,
                    fuhua_provider,
                    fubon_provider,
                    cathay_provider,
                    capital_provider,
                    kgi_provider,
                    yahoo_provider,
                ]
            elif _is_yuanta(issuer):
                chain = [yuanta_provider, yahoo_provider]
            elif _is_fuhua(issuer):
                chain = [fuhua_provider, yahoo_provider]
            elif _is_fubon(issuer):
                chain = [fubon_provider, yahoo_provider]
            elif _is_cathay(issuer):
                chain = [cathay_provider, yahoo_provider]
            elif _is_capital(issuer):
                chain = [capital_provider, yahoo_provider]
            elif _is_kgi(issuer):
                chain = [kgi_provider, yahoo_provider]
            else:
                chain = [yahoo_provider]

            matched = None
            for provider in chain:
                result = provider.fetch(symbol=symbol)
                if result.records:
                    matched = provider
                    break
            if result.records:
                _replace_holdings_for_snapshot(session, symbol, result)
                _maybe_update_aum_nav(session, symbol, result)
                # Backfill issuer when an issuer-specific API matched a null-issuer
                # ETF, so future refreshes route straight to it (skipping wasted
                # probes) and the issuer is shown correctly in the UI.
                if issuer is None:
                    master = (
                        session.query(EtfMaster)
                        .filter(EtfMaster.symbol == symbol)
                        .first()
                    )
                    if master is not None and not master.issuer:
                        if matched is fuhua_provider:
                            master.issuer = "復華投信"
                        elif matched is fubon_provider:
                            master.issuer = "富邦投信"
                        elif matched is cathay_provider:
                            master.issuer = "國泰投信"
                        elif matched is capital_provider:
                            master.issuer = "群益投信"
                        elif matched is kgi_provider:
                            master.issuer = "凱基投信"
                        elif matched is yuanta_provider:
                            master.issuer = "元大投信"
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


def _maybe_update_aum_nav(session, symbol: str, result) -> None:
    """Update EtfMaster.aum/nav/nav_date from a provider's fund_meta block.

    Issuer-authoritative figures, so they always overwrite — but only with
    non-None values (never wipe an existing figure with a missing one).
    Committed by the caller (_replace_holdings_for_snapshot commits).
    """
    meta = getattr(result, "fund_meta", None)
    if not isinstance(meta, dict):
        return
    aum = meta.get("aum")
    nav = meta.get("nav")
    nav_date = meta.get("nav_date")
    if aum is None and nav is None and nav_date is None:
        return
    master = session.query(EtfMaster).filter(EtfMaster.symbol == symbol).first()
    if master is None:
        return
    if aum is not None:
        master.aum = aum
    if nav is not None:
        master.nav = nav
    if nav_date is not None:
        master.nav_date = nav_date


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


def _run_profile_phase(session, report) -> dict:
    """Profile phase: fetch all Yuanta ETF profiles once and update EtfMaster.

    A SINGLE call to the Yuanta ETFBackstage endpoint returns every Yuanta
    fund. For each returned symbol that has a matching EtfMaster row we update
    tracking_index / index_provider / listing_date / management_fee plus source
    provenance. Non-null issuer figures ALWAYS overwrite (issuer-authoritative);
    a null field in the response never wipes an existing value. Symbols not in
    the profile data (non-Yuanta ETFs) are simply skipped — never an error.

    Per-symbol safe; never aborts the job on a single failure.
    """
    report(
        phase="profile",
        total=0,
        processed=0,
        succeeded=0,
        failed=0,
        message="抓取 ETF 基本資料中...",
    )

    provider = get_data_provider("yuanta-profile")
    try:
        result = provider.fetch()
    except Exception as exc:  # noqa: BLE001
        report(
            phase="profile",
            total=0,
            processed=0,
            succeeded=0,
            failed=0,
            message=f"基本資料抓取失敗：{exc}",
        )
        return {"records": 0, "updated": 0, "skipped": 0, "errors": [str(exc)]}

    records = result.records or []
    n_total = len(records)
    n_updated = 0
    n_skipped = 0

    for i, rec in enumerate(records, start=1):
        symbol = rec.get("symbol")
        if not symbol:
            n_skipped += 1
            continue
        try:
            master = (
                session.query(EtfMaster)
                .filter(EtfMaster.symbol == symbol)
                .first()
            )
            if master is None:
                n_skipped += 1
                continue

            changed = False
            for field_name in (
                "tracking_index",
                "index_provider",
                "listing_date",
                "management_fee",
            ):
                value = rec.get(field_name)
                if value is not None:
                    setattr(master, field_name, value)
                    changed = True

            # Every fund in the profile response is Yuanta-issued; backfill the
            # issuer when missing so the holdings phase routes it to the Yuanta
            # full-list API (many rows arrive from TWSE with a null issuer).
            if not master.issuer:
                master.issuer = "元大投信"
                changed = True

            if changed:
                master.source_name = rec.get("source_name")
                master.source_url = rec.get("source_url")
                if rec.get("listing_date") is not None:
                    master.data_date = rec.get("listing_date")
                master.fetched_at = rec.get("fetched_at")
                master.confidence_level = rec.get("confidence_level")
                session.commit()
                n_updated += 1
            else:
                n_skipped += 1
        except Exception:  # noqa: BLE001
            session.rollback()
            n_skipped += 1

        report(
            phase="profile",
            total=n_total,
            processed=i,
            succeeded=n_updated,
            failed=n_skipped,
            message=f"更新 ETF 基本資料中 {i}/{n_total}",
        )

    return {
        "records": n_total,
        "updated": n_updated,
        "skipped": n_skipped,
        "errors": result.errors,
    }


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
