#!/usr/bin/env python3
"""
De-duplicate the shipped car-performance CSV/SQLite outputs in place.

Why this exists (2026-09-17 audit): the shipped database carried 106+
duplicated (year, manufacturer, model) keys - the same car shipped twice
under two different car_ids - most caused by DataMerger.deduplicate() not
resolving a manufacturer alias ("Lucid" vs "Lucid Motors") or a repeated
manufacturer name inside the model field ("Audi A6 Allroad" vs "A6 Allroad")
before hashing. Both are now fixed in etl/core/merger.py.

This script applies ONLY DataMerger.deduplicate() to the data already on
disk - it does NOT call DataMerger.merge() to re-ingest the raw source
files, and does NOT run DataCleaner. That is deliberate, not a shortcut:

    DataMerger.merge()'s incremental grouping keys on _create_key(), which
    calls _normalize_model(). That helper strips ANY parenthetical content
    from a model for key-matching ("Remove extra specifications in
    parentheses for basic matching"), on the theory that a paren holds a
    non-identifying spec. For most sources that is true. For Autoevolution's
    own convention of appending a chassis/generation code, it is false: a
    full merge() pass on this dataset merges "Mercedes-Benz BENZ C-Class
    (W205)" (a C-Class sedan) into "Mercedes-Benz BENZ C-Class (A205)" (a
    C-Class Cabriolet on a DIFFERENT chassis) - two different cars, one
    discarded. deduplicate() alone does not have this problem: its
    authoritative key is car_id, from generate_car_id(), which strips only
    punctuation (folds "GT-R" and "GT R" together, as intended) and keeps
    every alphanumeric character - "(W205)" and "(A205)" hash differently,
    so they are correctly left as two records.

    That _normalize_model() behaviour is pre-existing (not introduced by
    the 2026-09-17 fix) and out of scope for this script; see the
    2026-09-17 fix report for the reproduction. A full `python -m etl.cli
    run` will still hit it. Until _normalize_model() is taught to tell a
    chassis code from a decorative spec, prefer this script - or a
    dry-run-and-inspect pass - over a blind `etl.cli run` when the goal is
    only to remove duplicates from data that is otherwise already correct.

Usage:
    python scripts/dedupe_existing_data.py            # writes csv + sqlite
    python scripts/dedupe_existing_data.py --dry-run   # report only
    python scripts/dedupe_existing_data.py --format csv|sqlite|both
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from etl.core.manufacturers import ManufacturerNormalizer
from etl.core.merger import DataMerger
from etl.core.schema import Schema
from etl.outputs.csv_writer import CSVWriter
from etl.outputs.sqlite_writer import SQLiteWriter
from etl.validators.consistency import ConsistencyValidator


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Report only, write nothing")
    parser.add_argument(
        "--format", choices=["csv", "sqlite", "both"], default="both",
        help="Which output(s) to write (default: both)",
    )
    parser.add_argument(
        "--csv-path", type=Path,
        default=PROJECT_ROOT / "public" / "data" / "car-performance-data.csv",
    )
    parser.add_argument(
        "--sqlite-path", type=Path,
        default=PROJECT_ROOT / "public" / "data" / "car-performance-data.db",
    )
    args = parser.parse_args()

    normalizer = ManufacturerNormalizer()
    schema = Schema()
    merger = DataMerger(normalizer, schema)

    print(f"Loading {args.csv_path}")
    existing = merger.load_existing_csv(args.csv_path)
    print(f"  {len(existing):,} records loaded")

    deduped = merger.deduplicate(existing)
    removed = len(existing) - len(deduped)
    print(f"deduplicate(): {len(deduped):,} records ({removed:,} duplicate rows merged away)")

    validator = ConsistencyValidator(normalizer)
    result = validator.validate(deduped)
    dup_issues = [i for i in result.issues if i.field == "duplicate"]
    if dup_issues:
        print(f"WARNING: {len(dup_issues)} duplicate key(s) remain after dedup:")
        for issue in dup_issues:
            print(f"  {issue}")
    else:
        print("Zero duplicate (year, manufacturer, model) keys remain.")

    if args.dry_run:
        print("\nDry run - not writing output")
        return 1 if dup_issues else 0

    if args.format in ("csv", "both"):
        csv_writer = CSVWriter(schema)
        count = csv_writer.write(deduped, args.csv_path)
        print(f"Wrote {count:,} records to {args.csv_path}")

    if args.format in ("sqlite", "both"):
        sqlite_writer = SQLiteWriter(schema)
        count = sqlite_writer.write(deduped, args.sqlite_path)
        print(f"Wrote {count:,} records to {args.sqlite_path}")
        is_valid, errors = sqlite_writer.validate_output(args.sqlite_path)
        if not is_valid:
            print("SQLite validation errors:")
            for error in errors:
                print(f"  {error}")
        else:
            print("SQLite database validated successfully")

    return 1 if dup_issues else 0


if __name__ == "__main__":
    sys.exit(main())
