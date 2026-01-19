#!/usr/bin/env python3
"""
Parser for Wikipedia Top Gear test track Power Lap times.

Parses CSV data extracted from Wikipedia's Top Gear lap times article.
"""

import csv
from pathlib import Path
from typing import Optional

from etl.parsers.base import BaseParser, CarRecord, ParseResult
from etl.parsers.registry import register_parser


@register_parser("wikipedia.top_gear")
class TopGearParser(BaseParser):
    """Parser for Wikipedia Top Gear lap time data."""

    SOURCE_NAME = "top_gear"

    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the file."""
        return (
            file_path.suffix.lower() == ".csv"
            and "top_gear" in str(file_path).lower()
        )

    def parse_file(self, file_path: Path) -> ParseResult:
        """Parse Top Gear lap times CSV file."""
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
        """Parse a single row from Top Gear CSV."""
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

        # Filter out unrealistic times (< 1 min or > 3 min)
        if lap_time_sec < 60 or lap_time_sec > 180:
            self._warn(
                f"Lap time {lap_time_sec}s out of range for: '{vehicle}'",
                file_path,
                row_num,
            )
            return None

        # Get episode info
        episode = self._clean_text(row.get("Episode", ""))

        # Try to extract year from vehicle name
        year = self._parse_year(vehicle)

        data = {
            "top_gear_lap_sec": lap_time_sec,
        }
        if episode:
            data["top_gear_episode"] = episode

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
