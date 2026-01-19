#!/usr/bin/env python3
"""
CSV output writer for car performance data.

This module provides:
- Writing merged car data to CSV format
- Schema-compliant column ordering
- Backward compatible output format
"""

import csv
from pathlib import Path
from typing import Any

from etl.core.schema import Schema


class CSVWriter:
    """Writes car performance data to CSV format."""

    def __init__(self, schema: Schema):
        """Initialize the CSV writer.

        Args:
            schema: Schema instance for column ordering
        """
        self.schema = schema

    def write(
        self,
        data: list[dict[str, Any]],
        output_path: Path,
        columns: list[str] | None = None,
    ) -> int:
        """Write car data to CSV file.

        Args:
            data: List of car data dictionaries
            output_path: Path to output CSV file
            columns: Optional list of columns to include.
                     Defaults to schema column order.

        Returns:
            Number of records written
        """
        if columns is None:
            columns = self.schema.column_order

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=columns,
                extrasaction="ignore",
            )
            writer.writeheader()

            for record in data:
                # Clean up record for writing
                clean_record = self._clean_record(record, columns)
                writer.writerow(clean_record)

        return len(data)

    def _clean_record(
        self, record: dict[str, Any], columns: list[str]
    ) -> dict[str, Any]:
        """Clean a record for CSV output.

        Args:
            record: Raw record dictionary
            columns: Columns to include

        Returns:
            Cleaned record with proper formatting
        """
        clean = {}

        for col in columns:
            value = record.get(col)

            if value is None or value == "":
                clean[col] = ""
            elif isinstance(value, float):
                # Format floats without unnecessary decimals
                if value == int(value):
                    clean[col] = str(int(value))
                else:
                    clean[col] = str(round(value, 2))
            else:
                clean[col] = str(value)

        return clean

    def append(
        self,
        data: list[dict[str, Any]],
        output_path: Path,
    ) -> int:
        """Append car data to existing CSV file.

        Args:
            data: List of car data dictionaries to append
            output_path: Path to existing CSV file

        Returns:
            Number of records appended
        """
        if not output_path.exists():
            return self.write(data, output_path)

        # Read existing headers
        with open(output_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            columns = next(reader)

        # Append new data
        with open(output_path, "a", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=columns,
                extrasaction="ignore",
            )

            for record in data:
                clean_record = self._clean_record(record, columns)
                writer.writerow(clean_record)

        return len(data)

    def validate_output(self, output_path: Path) -> tuple[bool, list[str]]:
        """Validate a written CSV file.

        Args:
            output_path: Path to CSV file to validate

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        if not output_path.exists():
            return False, ["Output file does not exist"]

        try:
            with open(output_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                # Check headers
                expected = set(self.schema.column_order)
                actual = set(reader.fieldnames or [])

                missing = expected - actual
                if missing:
                    errors.append(f"Missing columns: {', '.join(sorted(missing))}")

                extra = actual - expected
                if extra:
                    errors.append(f"Extra columns: {', '.join(sorted(extra))}")

                # Validate each row
                for row_num, row in enumerate(reader, start=2):
                    row_errors = self.schema.validate_record(row)
                    for field, error in row_errors:
                        errors.append(f"Row {row_num}, {field}: {error}")

                        # Limit errors to prevent overwhelming output
                        if len(errors) > 100:
                            errors.append("... (truncated, too many errors)")
                            return False, errors

        except Exception as e:
            errors.append(f"Error reading file: {str(e)}")

        return len(errors) == 0, errors
