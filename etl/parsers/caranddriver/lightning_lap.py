#!/usr/bin/env python3
"""
Parser for Car and Driver Lightning Lap results CSV data.

This parser handles VIR track lap times from the Lightning Lap series.
Format: "Year Make Model, Lap Time" (e.g., "2019 McLaren Senna, 2:34.9")
"""

import csv
import re
from pathlib import Path
from typing import Optional

from etl.parsers.base import BaseParser, CarRecord, ParseResult
from etl.parsers.registry import register_parser


@register_parser("caranddriver.lightning_lap")
class LightningLapParser(BaseParser):
    """Parser for Lightning Lap CSV data."""

    SOURCE_NAME = "Car & Driver"

    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the file."""
        return (
            file_path.suffix.lower() == ".csv"
            and ("lightning_lap" in file_path.name.lower() or "Lightning_Lap" in file_path.name)
        )

    def parse_file(self, file_path: Path) -> ParseResult:
        """Parse Lightning Lap CSV file."""
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
        """Parse a single row from Lightning Lap CSV."""
        # Get year/make/model combined field
        ymm_text = row.get("Year Make Model", "").strip()
        # Handle " Lap Time" (with leading space) from CSV
        time_text = row.get(" Lap Time", row.get("Lap Time", "")).strip()

        if not ymm_text or not time_text:
            return None

        # Parse "2019 McLaren Senna" format
        match = re.match(r"^(\d{4})\s+(.+)$", ymm_text)
        if not match:
            self._warn(f"Cannot parse year/make/model: '{ymm_text}'", file_path, row_num)
            return None

        year = match.group(1)
        make_model = match.group(2).strip()

        # Parse manufacturer and model
        manufacturer, model = self._parse_car_name(make_model)

        if not manufacturer:
            self._warn(f"Unknown manufacturer in: '{make_model}'", file_path, row_num)
            return None

        if not model:
            # If no model parsed, use the whole make_model as model after removing manufacturer
            model = make_model

        # Parse lap time (mm:ss.s format)
        lap_time_sec = self._parse_time(time_text)
        if lap_time_sec is None:
            self._warn(f"Cannot parse lap time: '{time_text}'", file_path, row_num)
            return None

        return CarRecord(
            manufacturer=manufacturer,
            model=model,
            year=year,
            country=self._get_country(manufacturer),
            data={
                "lightning_lap_sec": lap_time_sec,
            },
            source=self.SOURCE_NAME,
            source_file=str(file_path),
            source_row=row_num,
        )
