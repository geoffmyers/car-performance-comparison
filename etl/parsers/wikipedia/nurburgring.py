#!/usr/bin/env python3
"""
Parser for Wikipedia Nürburgring Nordschleife lap times.

Parses CSV data extracted from Wikipedia's Nürburgring lap times article.
"""

import csv
import re
from pathlib import Path
from typing import Optional

from etl.parsers.base import BaseParser, CarRecord, ParseResult
from etl.parsers.registry import register_parser


@register_parser("wikipedia.nurburgring")
class NurburgringParser(BaseParser):
    """Parser for Wikipedia Nürburgring lap time data."""

    SOURCE_NAME = "Wikipedia"

    # Skip race cars (not production vehicles)
    RACE_CAR_PATTERNS = [
        r"\bF1\b",
        r"\bF2\b",
        r"\bF3\b",
        r"\bFormula\b",
        r"\bGT3\b",
        r"\bGT2\b",
        r"\bGT1\b",
        r"\bLMP\d?\b",
        r"\bDTM\b",
        r"\bWRC\b",
        r"\bTCR\b",
        r"\bRace\s*Car\b",
        r"\bPro(?:totype)?\s*Class\b",
        r"\bcycling\b",
        r"\bbicycle\b",
    ]

    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the file."""
        return (
            file_path.suffix.lower() == ".csv"
            and "nurburgring" in str(file_path).lower()
        )

    def parse_file(self, file_path: Path) -> ParseResult:
        """Parse Nürburgring lap times CSV file."""
        self._reset_messages()
        records = []
        row_count = 0
        skipped_race_cars = 0

        file_hash = self._compute_file_hash(file_path)

        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row_num, row in enumerate(reader, start=2):
                row_count += 1

                # Get vehicle name
                vehicle = row.get("Vehicle", "") or row.get("Car", "")
                vehicle = self._clean_text(vehicle)

                # Skip race cars
                if self._is_race_car(vehicle):
                    skipped_race_cars += 1
                    continue

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
                "skipped_race_cars": skipped_race_cars,
            },
        )

    def _is_race_car(self, vehicle: str) -> bool:
        """Check if vehicle is a race car (not production)."""
        for pattern in self.RACE_CAR_PATTERNS:
            if re.search(pattern, vehicle, re.IGNORECASE):
                return True
        return False

    def _parse_row(
        self, row: dict, file_path: Path, row_num: int
    ) -> Optional[CarRecord]:
        """Parse a single row from Nürburgring CSV."""
        # Get vehicle name
        vehicle = row.get("Vehicle", "") or row.get("Car", "")
        vehicle = self._clean_text(vehicle)

        if not vehicle:
            return None

        # Parse manufacturer and model
        manufacturer, model = self._parse_car_name(vehicle)

        if not manufacturer:
            self._warn(f"Unknown manufacturer in: '{vehicle}'", file_path, row_num)
            return None

        # Parse lap time
        time_str = row.get("Time", "") or row.get("Lap Time", "")
        lap_time_sec = self._parse_time(time_str)

        if lap_time_sec is None:
            self._warn(f"Cannot parse lap time: '{time_str}'", file_path, row_num)
            return None

        # Filter out unrealistic times (< 5 min or > 15 min)
        if lap_time_sec < 300 or lap_time_sec > 900:
            self._warn(
                f"Lap time {lap_time_sec}s out of range for: '{vehicle}'",
                file_path,
                row_num,
            )
            return None

        # Get driver and date
        driver = self._clean_text(row.get("Driver", ""))
        date = self._clean_text(row.get("Date", ""))

        # Try to extract year from vehicle name or date
        year = None
        if date:
            year = self._parse_year(date)
        if not year:
            year = self._parse_year(vehicle)

        data = {
            "nurburgring_lap_sec": lap_time_sec,
        }
        if driver:
            data["nurburgring_driver"] = driver
        if date:
            data["nurburgring_date"] = date

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
