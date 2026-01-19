#!/usr/bin/env python3
"""
Parser for Wikipedia production car speed records.

Parses CSV data extracted from Wikipedia's speed records article.
"""

import csv
from pathlib import Path
from typing import Optional

from etl.parsers.base import BaseParser, CarRecord, ParseResult
from etl.parsers.registry import register_parser


@register_parser("wikipedia.speed_records")
class SpeedRecordsParser(BaseParser):
    """Parser for Wikipedia speed records data."""

    SOURCE_NAME = "speed_records"

    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the file."""
        return (
            file_path.suffix.lower() == ".csv"
            and "speed_records" in str(file_path).lower()
        )

    def parse_file(self, file_path: Path) -> ParseResult:
        """Parse speed records CSV file."""
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
        """Parse a single row from speed records CSV."""
        # Get vehicle name
        vehicle = (
            row.get("Make and model", "")
            or row.get("Vehicle", "")
            or row.get("Car", "")
        )
        vehicle = self._clean_text(vehicle)

        if not vehicle:
            return None

        # Parse manufacturer and model
        manufacturer, model = self._parse_car_name(vehicle)

        if not manufacturer:
            self._warn(f"Unknown manufacturer in: '{vehicle}'", file_path, row_num)
            return None

        # Parse top speed
        speed_str = row.get("Top speed", "") or row.get("Speed", "")
        mph, kmh = self._parse_speed(speed_str)

        if mph is None and kmh is None:
            self._warn(f"Cannot parse speed: '{speed_str}'", file_path, row_num)
            return None

        # Filter out unrealistic speeds
        if mph and (mph < 50 or mph > 350):
            self._warn(
                f"Speed {mph} mph out of range for: '{vehicle}'",
                file_path,
                row_num,
            )
            return None

        # Get year
        year_str = row.get("Year", "")
        year = self._parse_year(year_str)

        # Get engine info
        engine = self._clean_text(row.get("Engine", ""))

        data = {}
        if mph:
            data["top_speed_mph"] = mph
        if kmh:
            data["top_speed_kmh"] = kmh
        if engine:
            data["engine"] = engine

        return CarRecord(
            manufacturer=manufacturer,
            model=model,
            year=year,
            country=self._get_country(manufacturer),
            data=data,
            source=self.SOURCE_NAME,
            source_file=str(file_path),
            source_row=row_num,
        )
