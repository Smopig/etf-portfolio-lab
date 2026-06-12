"""Data quality checks for ETF Portfolio Lab.

Provides individual check functions (each returning a list of
``QualityCheckResult``), an orchestrator ``run_all_checks`` that runs every
check against current DB contents, a ``persist_results`` helper to write
``DataQualityCheck`` rows, and a mapping from dataset_type -> relevant check
functions for use by the import scripts.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import (
    DataQualityCheck,
    EtfDividend,
    EtfHolding,
    EtfMaster,
    EtfPrice,
    StockIndustry,
)

PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"

INFO = "info"
WARNING = "warning"
ERROR = "error"


@dataclass
class QualityCheckResult:
    dataset_type: str
    dataset_key: str
    check_name: str
    status: str
    severity: str | None
    message: str


# ---------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------


def check_holding_weight_sum(session: Session) -> list[QualityCheckResult]:
    """Per (etf_symbol, holding_date): sum of weights should be ~100%."""
    results: list[QualityCheckResult] = []

    groups = (
        session.query(
            EtfHolding.etf_symbol,
            EtfHolding.holding_date,
            func.sum(EtfHolding.weight),
        )
        .group_by(EtfHolding.etf_symbol, EtfHolding.holding_date)
        .all()
    )

    for etf_symbol, holding_date, weight_sum in groups:
        weight_sum = float(weight_sum or 0)
        # Detect scale: if sum is plausibly a fraction (<= ~1.5), treat as
        # fraction and normalize to percent.
        normalized = weight_sum * 100 if weight_sum <= 1.5 else weight_sum

        key = f"{etf_symbol}:{holding_date.isoformat()}"
        if 95 <= normalized <= 105:
            status, severity = PASS, INFO
        elif 90 <= normalized < 95 or 105 < normalized <= 110:
            status, severity = WARN, WARNING
        else:
            status, severity = FAIL, ERROR

        results.append(
            QualityCheckResult(
                dataset_type="etf_holdings",
                dataset_key=key,
                check_name="holding_weight_sum",
                status=status,
                severity=severity,
                message=f"Sum of weights for {etf_symbol} on {holding_date} = {normalized:.2f}%",
            )
        )

    return results


def check_holding_missing_asset_symbol(session: Session) -> list[QualityCheckResult]:
    """Per (etf_symbol, holding_date): count holdings with null/blank asset_symbol."""
    results: list[QualityCheckResult] = []

    keys = (
        session.query(EtfHolding.etf_symbol, EtfHolding.holding_date)
        .distinct()
        .all()
    )

    for etf_symbol, holding_date in keys:
        rows = (
            session.query(EtfHolding)
            .filter_by(etf_symbol=etf_symbol, holding_date=holding_date)
            .all()
        )
        missing = sum(
            1 for r in rows if r.asset_symbol is None or str(r.asset_symbol).strip() == ""
        )

        key = f"{etf_symbol}:{holding_date.isoformat()}"
        if missing:
            status, severity = WARN, WARNING
            message = f"{missing} holding row(s) for {etf_symbol} on {holding_date} have a missing asset_symbol"
        else:
            status, severity = PASS, INFO
            message = f"All holding rows for {etf_symbol} on {holding_date} have an asset_symbol"

        results.append(
            QualityCheckResult(
                dataset_type="etf_holdings",
                dataset_key=key,
                check_name="holding_missing_asset_symbol",
                status=status,
                severity=severity,
                message=message,
            )
        )

    return results


def check_holding_industry_coverage(session: Session) -> list[QualityCheckResult]:
    """Per (etf_symbol, holding_date): check each asset_symbol has an industry mapping."""
    results: list[QualityCheckResult] = []

    keys = (
        session.query(EtfHolding.etf_symbol, EtfHolding.holding_date)
        .distinct()
        .all()
    )

    for etf_symbol, holding_date in keys:
        rows = (
            session.query(EtfHolding)
            .filter_by(etf_symbol=etf_symbol, holding_date=holding_date)
            .all()
        )

        missing = 0
        for r in rows:
            if not r.asset_symbol:
                continue
            industry = (
                session.query(StockIndustry)
                .filter_by(stock_symbol=r.asset_symbol)
                .first()
            )
            if industry is None or industry.industry_level_1 is None:
                missing += 1

        key = f"{etf_symbol}:{holding_date.isoformat()}"
        if missing:
            status, severity = WARN, WARNING
            message = (
                f"{missing} holding(s) for {etf_symbol} on {holding_date} "
                f"have no matching stock_industry.industry_level_1"
            )
        else:
            status, severity = PASS, INFO
            message = f"All holdings for {etf_symbol} on {holding_date} have industry mappings"

        results.append(
            QualityCheckResult(
                dataset_type="etf_holdings",
                dataset_key=key,
                check_name="holding_industry_coverage",
                status=status,
                severity=severity,
                message=message,
            )
        )

    return results


def check_price_date_gaps(session: Session) -> list[QualityCheckResult]:
    """Per etf_symbol: count missing business days (Mon-Fri) in trade_date range."""
    results: list[QualityCheckResult] = []

    symbols = session.query(EtfPrice.etf_symbol).distinct().all()

    for (etf_symbol,) in symbols:
        rows = (
            session.query(EtfPrice.trade_date)
            .filter_by(etf_symbol=etf_symbol)
            .all()
        )
        dates = {r[0] for r in rows}
        if not dates:
            continue

        min_date, max_date = min(dates), max(dates)

        expected_business_days = 0
        cur = min_date
        while cur <= max_date:
            if cur.weekday() < 5:  # Mon-Fri
                expected_business_days += 1
            cur += dt.timedelta(days=1)

        missing = expected_business_days - len(dates & _business_days(min_date, max_date))

        if missing > 0:
            status, severity = WARN, WARNING
            message = (
                f"{missing} business day(s) missing in price data for {etf_symbol} "
                f"between {min_date} and {max_date} (holidays may account for some gaps)"
            )
        else:
            status, severity = PASS, INFO
            message = f"No missing business days for {etf_symbol} between {min_date} and {max_date}"

        results.append(
            QualityCheckResult(
                dataset_type="etf_prices",
                dataset_key=etf_symbol,
                check_name="price_date_gaps",
                status=status,
                severity=severity,
                message=message,
            )
        )

    return results


def _business_days(start: dt.date, end: dt.date) -> set[dt.date]:
    days = set()
    cur = start
    while cur <= end:
        if cur.weekday() < 5:
            days.add(cur)
        cur += dt.timedelta(days=1)
    return days


def check_dividend_duplicates(session: Session) -> list[QualityCheckResult]:
    """Per etf_symbol: duplicate (etf_symbol, ex_dividend_date) rows -> FAIL."""
    results: list[QualityCheckResult] = []

    symbols = session.query(EtfDividend.etf_symbol).distinct().all()

    for (etf_symbol,) in symbols:
        rows = (
            session.query(EtfDividend.ex_dividend_date)
            .filter_by(etf_symbol=etf_symbol)
            .all()
        )
        dates = [r[0] for r in rows]
        seen: dict[dt.date, int] = {}
        for d in dates:
            seen[d] = seen.get(d, 0) + 1
        dup_dates = sorted(d for d, count in seen.items() if count > 1)

        if dup_dates:
            status, severity = FAIL, ERROR
            dup_str = ", ".join(d.isoformat() for d in dup_dates)
            message = f"Duplicate ex_dividend_date(s) for {etf_symbol}: {dup_str}"
        else:
            status, severity = PASS, INFO
            message = f"No duplicate ex_dividend_date for {etf_symbol}"

        results.append(
            QualityCheckResult(
                dataset_type="etf_dividends",
                dataset_key=etf_symbol,
                check_name="dividend_duplicates",
                status=status,
                severity=severity,
                message=message,
            )
        )

    return results


def check_data_freshness(session: Session, today: dt.date | None = None) -> list[QualityCheckResult]:
    """Per dataset_type+key: newest relevant date vs today."""
    if today is None:
        today = dt.date.today()

    results: list[QualityCheckResult] = []

    def _classify(newest: dt.date | None, dataset_type: str, key: str) -> QualityCheckResult:
        if newest is None:
            return QualityCheckResult(
                dataset_type=dataset_type,
                dataset_key=key,
                check_name="data_freshness",
                status=WARN,
                severity=WARNING,
                message=f"No date information available for {key}",
            )
        age = (today - newest).days
        if age > 365:
            status, severity = FAIL, ERROR
        elif age > 90:
            status, severity = WARN, WARNING
        else:
            status, severity = PASS, INFO
        return QualityCheckResult(
            dataset_type=dataset_type,
            dataset_key=key,
            check_name="data_freshness",
            status=status,
            severity=severity,
            message=f"Newest date for {key} is {newest} ({age} days old as of {today})",
        )

    # etf_master: data_date per symbol
    for symbol, data_date in session.query(EtfMaster.symbol, EtfMaster.data_date).all():
        results.append(_classify(data_date, "etf_master", symbol))

    # etf_holdings: latest holding_date per etf_symbol
    for etf_symbol, newest in (
        session.query(EtfHolding.etf_symbol, func.max(EtfHolding.holding_date))
        .group_by(EtfHolding.etf_symbol)
        .all()
    ):
        results.append(_classify(newest, "etf_holdings", etf_symbol))

    # etf_prices: latest trade_date per etf_symbol
    for etf_symbol, newest in (
        session.query(EtfPrice.etf_symbol, func.max(EtfPrice.trade_date))
        .group_by(EtfPrice.etf_symbol)
        .all()
    ):
        results.append(_classify(newest, "etf_prices", etf_symbol))

    # etf_dividends: latest ex_dividend_date per etf_symbol
    for etf_symbol, newest in (
        session.query(EtfDividend.etf_symbol, func.max(EtfDividend.ex_dividend_date))
        .group_by(EtfDividend.etf_symbol)
        .all()
    ):
        results.append(_classify(newest, "etf_dividends", etf_symbol))

    return results


def check_etf_master_required_fields(session: Session) -> list[QualityCheckResult]:
    """Per symbol: name, issuer, asset_class, tracking_index must be present."""
    results: list[QualityCheckResult] = []

    required_fields = ["name", "issuer", "asset_class", "tracking_index"]

    for etf in session.query(EtfMaster).all():
        missing = [f for f in required_fields if not getattr(etf, f)]

        if missing:
            status, severity = WARN, WARNING
            message = f"ETF {etf.symbol} is missing field(s): {', '.join(missing)}"
        else:
            status, severity = PASS, INFO
            message = f"ETF {etf.symbol} has all required fields"

        results.append(
            QualityCheckResult(
                dataset_type="etf_master",
                dataset_key=etf.symbol,
                check_name="etf_master_required_fields",
                status=status,
                severity=severity,
                message=message,
            )
        )

    return results


def check_source_completeness(session: Session) -> list[QualityCheckResult]:
    """Per dataset table: rows missing source_name -> WARN with count."""
    results: list[QualityCheckResult] = []

    dataset_models = {
        "etf_master": EtfMaster,
        "etf_holdings": EtfHolding,
        "etf_prices": EtfPrice,
        "etf_dividends": EtfDividend,
        "stock_industry": StockIndustry,
    }

    for dataset_type, model in dataset_models.items():
        total = session.query(model).count()
        if total == 0:
            continue

        missing = (
            session.query(model)
            .filter((model.source_name.is_(None)) | (model.source_name == ""))
            .count()
        )

        if missing:
            status, severity = WARN, WARNING
            message = f"{missing} of {total} row(s) in {dataset_type} are missing source_name"
        else:
            status, severity = PASS, INFO
            message = f"All {total} row(s) in {dataset_type} have source_name"

        results.append(
            QualityCheckResult(
                dataset_type=dataset_type,
                dataset_key="*",
                check_name="source_completeness",
                status=status,
                severity=severity,
                message=message,
            )
        )

    return results


# ---------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------

# Maps dataset_type (as used by import scripts) -> list of relevant check
# functions to run after a successful (non-dry-run) import of that dataset.
DATASET_CHECKS: dict[str, list] = {
    "etf_master": [
        check_etf_master_required_fields,
        check_data_freshness,
        check_source_completeness,
    ],
    "etf_holdings": [
        check_holding_weight_sum,
        check_holding_missing_asset_symbol,
        check_holding_industry_coverage,
        check_data_freshness,
        check_source_completeness,
    ],
    "etf_prices": [
        check_price_date_gaps,
        check_data_freshness,
        check_source_completeness,
    ],
    "etf_dividends": [
        check_dividend_duplicates,
        check_data_freshness,
        check_source_completeness,
    ],
    "stock_industry": [
        check_source_completeness,
    ],
}


# Checks that don't accept a `today` kwarg.
_NO_TODAY_CHECKS = {
    check_holding_weight_sum,
    check_holding_missing_asset_symbol,
    check_holding_industry_coverage,
    check_price_date_gaps,
    check_dividend_duplicates,
    check_etf_master_required_fields,
    check_source_completeness,
}


def run_all_checks(session: Session, today: dt.date | None = None) -> list[QualityCheckResult]:
    """Run every check against current DB contents."""
    results: list[QualityCheckResult] = []
    results.extend(check_holding_weight_sum(session))
    results.extend(check_holding_missing_asset_symbol(session))
    results.extend(check_holding_industry_coverage(session))
    results.extend(check_price_date_gaps(session))
    results.extend(check_dividend_duplicates(session))
    results.extend(check_data_freshness(session, today=today))
    results.extend(check_etf_master_required_fields(session))
    results.extend(check_source_completeness(session))
    return results


def run_checks_for_dataset(
    session: Session, dataset_type: str, today: dt.date | None = None
) -> list[QualityCheckResult]:
    """Run only the checks relevant to a given dataset_type."""
    checks = DATASET_CHECKS.get(dataset_type, [])
    results: list[QualityCheckResult] = []
    for check_fn in checks:
        if check_fn in _NO_TODAY_CHECKS:
            results.extend(check_fn(session))
        else:
            results.extend(check_fn(session, today=today))
    return results


def persist_results(session: Session, results: list[QualityCheckResult]) -> list[DataQualityCheck]:
    """Write ``DataQualityCheck`` rows for the given results. Returns the ORM objects."""
    now = dt.datetime.utcnow()
    rows = []
    for r in results:
        row = DataQualityCheck(
            dataset_type=r.dataset_type,
            dataset_key=r.dataset_key,
            check_name=r.check_name,
            status=r.status,
            severity=r.severity,
            message=r.message,
            checked_at=now,
        )
        session.add(row)
        rows.append(row)
    session.commit()
    return rows


def summarize(results: list[QualityCheckResult]) -> dict[str, int]:
    """Return counts of PASS/WARN/FAIL."""
    counts = {PASS: 0, WARN: 0, FAIL: 0}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1
    return counts


def summary_line(results: list[QualityCheckResult]) -> str:
    counts = summarize(results)
    return f"data quality: {counts.get(PASS, 0)} pass / {counts.get(WARN, 0)} warn / {counts.get(FAIL, 0)} fail"


def run_and_report(session: Session, dataset_type: str, today: dt.date | None = None) -> str:
    """Run + persist checks relevant to ``dataset_type`` and return a one-line summary.

    Intended to be called by import scripts after a successful (non-dry-run)
    import. Opens no new session beyond the one provided.
    """
    results = run_checks_for_dataset(session, dataset_type, today=today)
    persist_results(session, results)
    return summary_line(results)
