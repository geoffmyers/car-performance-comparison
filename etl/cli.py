#!/usr/bin/env python3
"""
CLI for the car performance ETL pipeline.

Commands:
- run: Run ETL pipeline for specified sources
- validate: Validate data without writing
- report: Generate quality report
- generate-types: Regenerate TypeScript types
- list-sources: List available data sources
- schema: Show data schema
"""

import argparse
import glob
import json
import sys
from pathlib import Path
from typing import Any

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from etl.core.schema import Schema
from etl.core.manufacturers import ManufacturerNormalizer
from etl.core.merger import DataMerger
from etl.core.converters import ValueConverter
from etl.core.enricher import DataEnricher
from etl.core.cleaner import DataCleaner
from etl.parsers.registry import ParserRegistry, get_parser as get_parser_class
from etl.outputs.csv_writer import CSVWriter
from etl.outputs.sqlite_writer import SQLiteWriter
from etl.outputs.typescript_gen import TypeScriptGenerator
from etl.outputs.quality_report import QualityReportGenerator
from etl.validators.range_validator import RangeValidator
from etl.validators.consistency import ConsistencyValidator

# Import all parsers to register them
from etl.parsers import caranddriver, wikipedia


def load_sources_config() -> dict:
    """Load sources configuration."""
    import yaml

    config_path = Path(__file__).parent / "config" / "sources.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_data_path() -> Path:
    """Get the base path for data files."""
    return PROJECT_ROOT / "public" / "data"


def get_output_csv_path() -> Path:
    """Get the path to the master CSV file."""
    return get_data_path() / "car-performance-data.csv"


def get_output_sqlite_path() -> Path:
    """Get the path to the SQLite database file."""
    return get_data_path() / "car-performance-data.db"


def run_pipeline(
    sources: list[str] | None = None,
    dry_run: bool = False,
    verbose: bool = False,
    output_format: str = "both",
) -> int:
    """Run the ETL pipeline.

    Args:
        sources: List of source names to process, or None for all
        dry_run: If True, don't write output files
        verbose: If True, print detailed output
        output_format: Output format - "csv", "sqlite", or "both"

    Returns:
        Exit code (0 for success)
    """
    config = load_sources_config()
    schema = Schema()
    normalizer = ManufacturerNormalizer()
    converter = ValueConverter()
    merger = DataMerger(normalizer, schema)

    data_path = get_data_path()
    output_path = get_output_csv_path()

    # Load existing data
    if verbose:
        print(f"Loading existing data from {output_path}")

    existing_data = merger.load_existing_csv(output_path)

    if verbose:
        print(f"Loaded {len(existing_data):,} existing records")

    # Process each enabled source
    all_records = []
    source_configs = config.get("sources", {})

    # Determine which sources to process
    if sources:
        sources_to_process = sources
    else:
        # Use processing order from config
        sources_to_process = config.get("processing_order", list(source_configs.keys()))

    for source_name in sources_to_process:
        if source_name not in source_configs:
            print(f"Warning: Unknown source '{source_name}', skipping")
            continue

        source_config = source_configs[source_name]

        # Skip disabled sources
        if not source_config.get("enabled", True):
            if verbose:
                print(f"Skipping disabled source: {source_name}")
            continue

        if verbose:
            print(f"\nProcessing source: {source_name}")

        # Get parser
        parser_name = source_config.get("parser")
        parser_class = get_parser_class(parser_name)

        if parser_class is None:
            print(f"Warning: No parser found for '{parser_name}', skipping {source_name}")
            continue

        parser = parser_class(normalizer, converter, schema)

        # Find files to process
        file_pattern = source_config.get("path", "")
        full_pattern = str(data_path / file_pattern)

        files = glob.glob(full_pattern)

        if not files:
            if verbose:
                print(f"  No files found matching: {file_pattern}")
            continue

        # Process each file
        for file_path in sorted(files):
            file_path = Path(file_path)

            # Skip files in skip_files list
            skip_files = source_config.get("skip_files", [])
            if file_path.name in skip_files:
                if verbose:
                    print(f"  Skipping: {file_path.name}")
                continue

            if verbose:
                print(f"  Parsing: {file_path.name}")

            try:
                result = parser.parse_file(file_path)
                all_records.extend(result.records)

                if verbose:
                    print(f"    Found {len(result.records)} records")
                    if result.warnings:
                        print(f"    Warnings: {len(result.warnings)}")
                    if result.errors:
                        print(f"    Errors: {len(result.errors)}")

            except Exception as e:
                print(f"Error parsing {file_path}: {e}")

    if verbose:
        print(f"\nTotal new records parsed: {len(all_records):,}")

    # Merge with existing data
    merged_data = merger.merge(existing_data, all_records)

    if verbose:
        print(f"Merged data contains {len(merged_data):,} records")

    # Deduplicate using normalized keys
    before_dedup = len(merged_data)
    merged_data = merger.deduplicate(merged_data)
    dedup_removed = before_dedup - len(merged_data)

    if verbose and dedup_removed > 0:
        print(f"  Removed {dedup_removed:,} duplicate records")

    # Post-process: Convert remaining "ICE" to "Petrol" as default
    # and "Hybrid"/"Plug-in Hybrid" to "Electric/Petrol" as default
    ice_converted = 0
    hybrid_converted = 0
    for record in merged_data:
        propulsion = record.get("propulsion", "")
        if propulsion == "ICE":
            record["propulsion"] = "Petrol"
            ice_converted += 1
        elif propulsion in ("Hybrid", "Plug-in Hybrid"):
            record["propulsion"] = "Electric/Petrol"
            hybrid_converted += 1

    if verbose and (ice_converted or hybrid_converted):
        print(f"  Converted {ice_converted:,} ICE records to Petrol")
        print(f"  Converted {hybrid_converted:,} Hybrid records to Electric/Petrol")

    # Enrich data with derived and inferred values
    if verbose:
        print("\nEnriching data with derived values...")

    enricher = DataEnricher(verbose=verbose)
    merged_data = enricher.enrich(merged_data)

    # Clean data - fix implausible values based on cross-field correlation
    if verbose:
        print("\nCleaning implausible values...")

    cleaner = DataCleaner(verbose=verbose)
    merged_data = cleaner.clean(merged_data)

    # Deduplicate again, now that cleaning has run. Cleaning can change the
    # very fields the merge key is built from - most visibly
    # _normalize_manufacturer_case() folding a stray "CHEVROLET" to
    # "Chevrolet" - which can make two records that looked distinct at the
    # first dedup pass (before cleaning touched them) collide afterward.
    # Left at one pass, this is exactly how the 2026-09-17 audit's duplicate
    # keys survived a run that already called deduplicate() once: the first
    # pass ran too early to see the collision cleaning was about to create.
    # deduplicate() is idempotent, so this is a no-op whenever nothing
    # collided.
    before_second_dedup = len(merged_data)
    merged_data = merger.deduplicate(merged_data)
    second_dedup_removed = before_second_dedup - len(merged_data)

    if verbose and second_dedup_removed > 0:
        print(f"  Removed {second_dedup_removed:,} more duplicate records found after cleaning")

    # Validate
    if verbose:
        print("\nRunning validation...")

    range_validator = RangeValidator(schema)
    consistency_validator = ConsistencyValidator(normalizer)

    range_result = range_validator.validate(merged_data)
    consistency_result = consistency_validator.validate(merged_data)

    if verbose:
        print(f"  Range validation: {range_result.error_count} errors, {range_result.warning_count} warnings")
        print(f"  Consistency validation: {consistency_result.error_count} errors, {consistency_result.warning_count} warnings")

    # Write output
    if not dry_run:
        csv_path = get_output_csv_path()
        sqlite_path = get_output_sqlite_path()

        # Write CSV output
        if output_format in ("csv", "both"):
            if verbose:
                print(f"\nWriting CSV output to {csv_path}")

            csv_writer = CSVWriter(schema)
            count = csv_writer.write(merged_data, csv_path)

            if verbose:
                print(f"Wrote {count:,} records to CSV")

        # Write SQLite output
        if output_format in ("sqlite", "both"):
            if verbose:
                print(f"\nWriting SQLite output to {sqlite_path}")

            sqlite_writer = SQLiteWriter(schema)
            count = sqlite_writer.write(merged_data, sqlite_path)

            if verbose:
                print(f"Wrote {count:,} records to SQLite")

            # Validate SQLite output
            is_valid, errors = sqlite_writer.validate_output(sqlite_path)
            if not is_valid:
                print("SQLite validation errors:")
                for error in errors:
                    print(f"  {error}")
            elif verbose:
                print("SQLite database validated successfully")
    else:
        if verbose:
            print("\nDry run - not writing output")

    return 0


def validate_data(verbose: bool = False) -> int:
    """Validate existing data without writing.

    Args:
        verbose: If True, print detailed output

    Returns:
        Exit code (0 for valid, 1 for invalid)
    """
    schema = Schema()
    normalizer = ManufacturerNormalizer()
    merger = DataMerger(normalizer, schema)

    output_path = get_output_csv_path()

    print(f"Validating {output_path}")

    # Load data
    data = merger.load_existing_csv(output_path)
    print(f"Loaded {len(data):,} records")

    # Run validators
    range_validator = RangeValidator(schema)
    consistency_validator = ConsistencyValidator(normalizer)

    range_result = range_validator.validate(data)
    consistency_result = consistency_validator.validate(data)

    # Print results
    print(f"\nRange Validation:")
    print(f"  Errors: {range_result.error_count}")
    print(f"  Warnings: {range_result.warning_count}")

    if verbose and range_result.issues:
        print("\n  Issues:")
        for issue in range_result.issues[:20]:
            print(f"    {issue}")
        if len(range_result.issues) > 20:
            print(f"    ... and {len(range_result.issues) - 20} more")

    print(f"\nConsistency Validation:")
    print(f"  Errors: {consistency_result.error_count}")
    print(f"  Warnings: {consistency_result.warning_count}")

    if verbose and consistency_result.issues:
        print("\n  Issues:")
        for issue in consistency_result.issues[:20]:
            print(f"    {issue}")
        if len(consistency_result.issues) > 20:
            print(f"    ... and {len(consistency_result.issues) - 20} more")

    total_errors = range_result.error_count + consistency_result.error_count

    if total_errors == 0:
        print("\nValidation passed!")
        return 0
    else:
        print(f"\nValidation failed with {total_errors} errors")
        return 1


def generate_report(format: str = "text", output: str | None = None) -> int:
    """Generate a quality report.

    Args:
        format: Output format ("text", "json", or "html")
        output: Output file path, or None for stdout

    Returns:
        Exit code (0 for success)
    """
    schema = Schema()
    normalizer = ManufacturerNormalizer()
    merger = DataMerger(normalizer, schema)

    output_path = get_output_csv_path()

    # Load data
    data = merger.load_existing_csv(output_path)

    # Run validators
    range_validator = RangeValidator(schema)
    consistency_validator = ConsistencyValidator(normalizer)

    range_result = range_validator.validate(data)
    consistency_result = consistency_validator.validate(data)

    # Generate report
    generator = QualityReportGenerator(schema)
    report = generator.generate(
        data,
        validation_results=[range_result, consistency_result],
    )

    # Output
    if output:
        generator.write(report, Path(output), format)
        print(f"Report written to {output}")
    else:
        if format == "json":
            print(generator.format_json(report))
        elif format == "html":
            print(generator.format_html(report))
        else:
            print(generator.format_text(report))

    return 0


def generate_types(output: str | None = None) -> int:
    """Generate TypeScript types from schema.

    Args:
        output: Output file path, or None for default

    Returns:
        Exit code (0 for success)
    """
    schema = Schema()
    normalizer = ManufacturerNormalizer()

    if output:
        output_path = Path(output)
    else:
        output_path = PROJECT_ROOT / "src" / "types" / "car.ts"

    generator = TypeScriptGenerator(schema, normalizer)
    generator.generate(output_path)

    print(f"TypeScript types generated at {output_path}")
    return 0


def list_sources() -> int:
    """List available data sources.

    Returns:
        Exit code (0 for success)
    """
    config = load_sources_config()
    sources = config.get("sources", {})

    print("Available Data Sources:")
    print("-" * 60)

    for name, source_config in sources.items():
        enabled = source_config.get("enabled", True)
        status = "enabled" if enabled else "disabled"
        description = source_config.get("description", "")
        parser = source_config.get("parser", "")

        print(f"\n{name} [{status}]")
        print(f"  Description: {description}")
        print(f"  Parser: {parser}")
        print(f"  Path: {source_config.get('path', '')}")

    return 0


def show_schema() -> int:
    """Show the data schema.

    Returns:
        Exit code (0 for success)
    """
    schema = Schema()

    print("Car Performance Data Schema")
    print("=" * 60)
    print(f"Version: {schema.version}")
    print(f"Total columns: {len(schema.column_order)}")
    print()

    for category in schema.categories:
        fields = schema.get_fields_by_category(category)
        if not fields:
            continue

        print(f"{category}:")
        print("-" * 40)

        for field_name in fields:
            field = schema.get_field(field_name)
            if field:
                field_type = field.get("type", "string")
                unit = field.get("unit", "")
                header = field.get("header", field_name)

                unit_str = f" ({unit})" if unit else ""
                print(f"  {field_name:25s} {field_type:10s} {header}{unit_str}")

        print()

    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="car-etl",
        description="Car Performance ETL Pipeline",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # run command
    run_parser = subparsers.add_parser("run", help="Run ETL pipeline")
    run_parser.add_argument(
        "--sources",
        nargs="+",
        help="Specific sources to process (default: all)",
    )
    run_parser.add_argument(
        "--all",
        action="store_true",
        help="Process all enabled sources",
    )
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't write output files",
    )
    run_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )
    run_parser.add_argument(
        "--output-format",
        choices=["csv", "sqlite", "both"],
        default="both",
        help="Output format: csv, sqlite, or both (default: both)",
    )

    # validate command
    validate_parser = subparsers.add_parser("validate", help="Validate data")
    validate_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed validation issues",
    )

    # report command
    report_parser = subparsers.add_parser("report", help="Generate quality report")
    report_parser.add_argument(
        "--format",
        choices=["text", "json", "html"],
        default="text",
        help="Output format",
    )
    report_parser.add_argument(
        "--output", "-o",
        help="Output file path (default: stdout)",
    )

    # generate-types command
    types_parser = subparsers.add_parser("generate-types", help="Generate TypeScript types")
    types_parser.add_argument(
        "--output", "-o",
        help="Output file path",
    )

    # list-sources command
    subparsers.add_parser("list-sources", help="List available sources")

    # schema command
    subparsers.add_parser("schema", help="Show data schema")

    args = parser.parse_args()

    if args.command == "run":
        return run_pipeline(
            sources=args.sources,
            dry_run=args.dry_run,
            verbose=args.verbose,
            output_format=args.output_format,
        )
    elif args.command == "validate":
        return validate_data(verbose=args.verbose)
    elif args.command == "report":
        return generate_report(format=args.format, output=args.output)
    elif args.command == "generate-types":
        return generate_types(output=args.output)
    elif args.command == "list-sources":
        return list_sources()
    elif args.command == "schema":
        return show_schema()
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
