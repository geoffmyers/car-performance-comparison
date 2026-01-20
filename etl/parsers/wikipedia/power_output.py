#!/usr/bin/env python3
"""
Parser for Wikipedia production cars by power output.

Parses CSV data extracted from Wikipedia's power output article.
"""

import csv
from pathlib import Path
from typing import Optional

from etl.parsers.base import BaseParser, CarRecord, ParseResult
from etl.parsers.registry import register_parser


@register_parser("wikipedia.power_output")
class PowerOutputParser(BaseParser):
    """Parser for Wikipedia power output data."""

    SOURCE_NAME = "Wikipedia"

    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the file."""
        return (
            file_path.suffix.lower() == ".csv"
            and "power_output" in str(file_path).lower()
        )

    def parse_file(self, file_path: Path) -> ParseResult:
        """Parse power output CSV file."""
        self._reset_messages()
        records = []
        row_count = 0

        file_hash = self._compute_file_hash(file_path)

        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row_num, row in enumerate(reader, start=2):
                row_count += 1
                parsed = self._parse_row(row, file_path, row_num)
                if parsed:
                    # Can return multiple records for combined entries
                    if isinstance(parsed, list):
                        records.extend(parsed)
                    else:
                        records.append(parsed)

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
    ) -> Optional[CarRecord | list[CarRecord]]:
        """Parse a single row from power output CSV."""
        # Get vehicle name
        vehicle = row.get("Vehicle", "") or row.get("Car", "")
        vehicle = self._clean_text(vehicle)

        if not vehicle:
            return None

        # Handle combined entries like "Tesla Model S Plaid/Tesla Model X Plaid"
        if "/" in vehicle and not self._is_model_variant(vehicle):
            return self._parse_combined_vehicle(row, file_path, row_num)

        # Parse manufacturer and model
        manufacturer, model = self._parse_car_name(vehicle)

        if not manufacturer:
            self._warn(f"Unknown manufacturer in: '{vehicle}'", file_path, row_num)
            return None

        # Parse power
        power_str = row.get("Power", "")
        hp, kw = self._parse_power(power_str)

        if hp is None and kw is None:
            self._warn(f"Cannot parse power: '{power_str}'", file_path, row_num)
            return None

        # Filter out unrealistic power values
        if hp and hp > 3000:
            self._warn(
                f"Power {hp} hp seems unrealistic for: '{vehicle}'",
                file_path,
                row_num,
            )
            return None

        # Get year
        year_str = row.get("Year", "")
        year = self._parse_year(year_str)

        # Get propulsion type
        type_str = row.get("Type", "")
        propulsion = self._normalize_propulsion(type_str)

        data = {}
        if hp:
            data["power_hp"] = hp
        if kw:
            data["power_kw"] = kw

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

    def _is_model_variant(self, vehicle: str) -> bool:
        """Check if slash indicates model variant rather than two vehicles."""
        # Examples of model variants: "Porsche 911 GT3/GT3 RS"
        # These should NOT be split
        slash_parts = vehicle.split("/")
        if len(slash_parts) != 2:
            return False

        # If second part doesn't have manufacturer prefix, it's a variant
        second_part = slash_parts[1].strip()
        # Check if it starts with a known manufacturer or looks like a full vehicle name
        words = second_part.split()
        if len(words) < 2:
            return True  # Just "GT3 RS" - it's a variant

        # Check if first word is a known manufacturer
        first_word = words[0]
        normalized = self.normalizer.normalize(first_word)
        if normalized != first_word:
            return False  # It's a known manufacturer - not a variant

        # Check multi-word manufacturers
        for mw in self.normalizer.multi_word:
            if second_part.startswith(mw):
                return False

        return True

    def _parse_combined_vehicle(
        self, row: dict, file_path: Path, row_num: int
    ) -> Optional[list[CarRecord]]:
        """Parse a row with multiple vehicles combined with /."""
        vehicle = row.get("Vehicle", "") or row.get("Car", "")
        vehicle = self._clean_text(vehicle)

        # Split on /
        parts = [p.strip() for p in vehicle.split("/")]

        # Get common data
        power_str = row.get("Power", "")
        hp, kw = self._parse_power(power_str)

        year_str = row.get("Year", "")
        type_str = row.get("Type", "")
        propulsion = self._normalize_propulsion(type_str)

        records = []
        year_parts = year_str.split("/") if "/" in year_str else [year_str] * len(parts)

        for i, part in enumerate(parts):
            manufacturer, model = self._parse_car_name(part)

            if not manufacturer:
                self._warn(f"Unknown manufacturer in part: '{part}'", file_path, row_num)
                continue

            # Get corresponding year if available
            year = None
            if i < len(year_parts):
                year = self._parse_year(year_parts[i])

            data = {}
            if hp:
                data["power_hp"] = hp
            if kw:
                data["power_kw"] = kw

            records.append(
                CarRecord(
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
            )

        return records if records else None

    def _normalize_propulsion(self, type_str: str) -> Optional[str]:
        """Normalize propulsion type from Wikipedia format."""
        type_lower = type_str.lower().strip()

        if "electric" in type_lower and "plug" not in type_lower and "hybrid" not in type_lower:
            return "Electric"
        elif "plug-in hybrid" in type_lower or "phev" in type_lower:
            return "Plug-in Hybrid"
        elif "hybrid electric" in type_lower or "hev" in type_lower:
            return "Hybrid"
        elif "hybrid" in type_lower:
            return "Hybrid"
        elif "internal combustion" in type_lower or "ice" in type_lower:
            return "ICE"

        return None
