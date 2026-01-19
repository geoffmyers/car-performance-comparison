#!/usr/bin/env python3
"""
Parser for Wikipedia fastest production cars by acceleration.

Parses CSV data extracted from Wikipedia's acceleration records article.
"""

import csv
from pathlib import Path
from typing import Optional

from etl.parsers.base import BaseParser, CarRecord, ParseResult
from etl.parsers.registry import register_parser


@register_parser("wikipedia.acceleration")
class AccelerationParser(BaseParser):
    """Parser for Wikipedia acceleration records data."""

    SOURCE_NAME = "acceleration"

    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the file."""
        return (
            file_path.suffix.lower() == ".csv"
            and "acceleration" in str(file_path).lower()
        )

    def parse_file(self, file_path: Path) -> ParseResult:
        """Parse acceleration records CSV file."""
        self._reset_messages()
        records = []
        row_count = 0

        file_hash = self._compute_file_hash(file_path)

        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row_num, row in enumerate(reader, start=2):
                row_count += 1
                record = self._parse_row(row, file_path, row_num)
                if record:
                    records.append(record)

        return ParseResult(
            records=records,
            source_name=self.SOURCE_NAME,
            source_file=str(file_path),
            file_hash=file_hash,
            warnings=self._warnings.copy(),
            errors=self._errors.copy(),
            stats={
                "total_rows": row_count,
                "parsed_records": len(records),
            },
        )

    def _parse_row(
        self, row: dict, file_path: Path, row_num: int
    ) -> Optional[CarRecord]:
        """Parse a single row from acceleration CSV."""
        # Get vehicle name
        vehicle = row.get("Car", "") or row.get("Vehicle", "")
        vehicle = self._clean_text(vehicle)

        if not vehicle:
            return None

        # Parse manufacturer and model
        manufacturer, model = self._parse_car_name(vehicle)

        if not manufacturer:
            self._warn(f"Unknown manufacturer in: '{vehicle}'", file_path, row_num)
            return None

        # Parse time (0-60 mph)
        time_str = row.get("Time", "") or row.get("0-60 mph", "")
        time_sec = self._parse_float(time_str)

        if time_sec is None:
            self._warn(f"Cannot parse time: '{time_str}'", file_path, row_num)
            return None

        # Filter out unrealistic times
        if time_sec < 1.0 or time_sec > 30.0:
            self._warn(
                f"Time {time_sec}s out of range for: '{vehicle}'",
                file_path,
                row_num,
            )
            return None

        # Get year
        year_str = row.get("Model year", "") or row.get("Year", "")
        year = self._parse_year(year_str)

        # Get propulsion type
        propulsion_str = row.get("Propulsion", "") or row.get("Powertrain", "")
        propulsion = self._detect_propulsion(propulsion_str, model)

        data = {
            "0_60_mph_sec": time_sec,
        }

        return CarRecord(
            manufacturer=manufacturer,
            model=model,
            year=year,
            country=self._get_country(manufacturer),
            propulsion=propulsion,
            data=data,
            source=self.SOURCE_NAME,
            source_file=str(file_path),
            source_row=row_num,
        )
