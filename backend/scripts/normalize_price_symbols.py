"""One-off, idempotent normalization of ``etf_prices.etf_symbol`` values.

Older runs of ``fetch_all`` stored the Yahoo ticker (e.g. ``"0050.TW"`` or
``"0052.TWO"``) as ``etf_symbol`` instead of the bare ETF symbol
(``"0050"``). This left ``etf_prices`` rows that the price API
(``/api/etfs/{symbol}/prices``, which queries by bare symbol) can never
find.

This script strips everything from the first "." in ``etf_symbol`` for all
affected rows, so e.g. ``"0050.TW"`` -> ``"0050"`` and ``"0052.TWO"`` ->
``"0052"``.

Usage:
    docker compose exec backend python -m scripts.normalize_price_symbols

Safe to run multiple times: rows whose ``etf_symbol`` has no "." are left
untouched, so a second run is a no-op.

If a row with the bare symbol already exists for the same
(trade_date, source_name), the unique constraint
``(etf_symbol, trade_date, source_name)`` would be violated by a plain
UPDATE. In that case the suffixed (stale/duplicate) row is deleted instead,
keeping the existing bare-symbol row.

Equivalent manual SQL (run only if no duplicate rows exist for the bare
symbol):

    UPDATE etf_prices SET etf_symbol = split_part(etf_symbol, '.', 1)
    WHERE etf_symbol LIKE '%.%';
"""

from __future__ import annotations

from app.core.database import SessionLocal
from app.models import EtfPrice


def normalize_price_symbols(session) -> dict:
    """Strip exchange suffixes from ``etf_prices.etf_symbol``.

    Returns a summary dict with counts of updated and deleted rows.
    """
    rows = session.query(EtfPrice).filter(EtfPrice.etf_symbol.contains(".")).all()

    updated = 0
    deleted = 0

    for row in rows:
        bare_symbol = row.etf_symbol.split(".")[0]

        conflict = (
            session.query(EtfPrice)
            .filter(
                EtfPrice.etf_symbol == bare_symbol,
                EtfPrice.trade_date == row.trade_date,
                EtfPrice.source_name == row.source_name,
            )
            .first()
        )

        if conflict is not None:
            # A bare-symbol row already exists for this (date, source) -
            # the suffixed row is a stale duplicate; drop it.
            session.delete(row)
            deleted += 1
        else:
            row.etf_symbol = bare_symbol
            updated += 1

    session.commit()
    return {"rows_examined": len(rows), "updated": updated, "deleted": deleted}


def main() -> None:
    session = SessionLocal()
    try:
        summary = normalize_price_symbols(session)
        print("=" * 60)
        print("Price symbol normalization complete")
        print(f"  rows examined (contain '.'): {summary['rows_examined']}")
        print(f"  rows updated (suffix stripped): {summary['updated']}")
        print(f"  rows deleted (duplicate of bare symbol): {summary['deleted']}")
        print("=" * 60)
    finally:
        session.close()


if __name__ == "__main__":
    main()
