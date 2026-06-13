"""Run data quality checks across the database and persist results.

Usage:
    python -m scripts.run_quality_checks [--dataset-type X] [--quiet] [--no-persist]

By default runs all checks across all data currently in the DB, persists
each result as a ``DataQualityCheck`` row, and prints a summary grouped by
status. Exits with a non-zero status code if any FAIL results exist.
"""

from __future__ import annotations

import argparse
import sys

from app.core.database import SessionLocal
from app.utils.data_quality import (
    DATASET_CHECKS,
    FAIL,
    PASS,
    WARN,
    persist_results,
    run_all_checks,
    run_checks_for_dataset,
    summarize,
)


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run data quality checks.")
    parser.add_argument(
        "--dataset-type",
        default=None,
        choices=sorted(DATASET_CHECKS.keys()),
        help="Only run checks relevant to this dataset type",
    )
    parser.add_argument("--quiet", action="store_true", help="Only print the summary line")
    parser.add_argument(
        "--no-persist", action="store_true", help="Dry read-only run; do not write results"
    )
    return parser.parse_args(argv)


def main(argv=None) -> None:
    args = parse_args(argv)

    session = SessionLocal()
    try:
        if args.dataset_type:
            results = run_checks_for_dataset(session, args.dataset_type)
        else:
            results = run_all_checks(session)

        if not args.no_persist:
            persist_results(session, results)

        counts = summarize(results)

        if not args.quiet:
            for status in (FAIL, WARN, PASS):
                group = [r for r in results if r.status == status]
                if not group:
                    continue
                print(f"=== {status} ({len(group)}) ===")
                for r in group:
                    print(f"  [{r.severity}] {r.check_name} ({r.dataset_type}:{r.dataset_key}): {r.message}")

        print(
            f"data quality: {counts.get(PASS, 0)} pass / "
            f"{counts.get(WARN, 0)} warn / {counts.get(FAIL, 0)} fail"
        )

        if counts.get(FAIL, 0) > 0:
            sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
