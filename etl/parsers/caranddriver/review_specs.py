#!/usr/bin/env python3
"""
Parser for Car and Driver car-review-specs.csv data.

This parser handles the main Car and Driver instrumented test data,
extracting performance metrics like 0-60 times, quarter mile, braking, etc.
"""

import csv
import re
from pathlib import Path
from typing import Optional

from etl.parsers.base import BaseParser, CarRecord, ParseResult
from etl.parsers.registry import register_parser


@register_parser("caranddriver.review_specs")
class ReviewSpecsParser(BaseParser):
    """Parser for Car and Driver review specs CSV data."""

    SOURCE_NAME = "caranddriver"

    # Files to skip
    SKIP_FILES = {
        "car-review-specs-old.csv",
        "car-review-specs-test.csv",
        "car-review-specs-test2.csv",
        "compare-model-data.csv",
    }

    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the file."""
        if file_path.name in self.SKIP_FILES:
            return False
        return (
            file_path.suffix.lower() == ".csv"
            and "car-review-specs" in file_path.name.lower()
        )

    def parse_file(self, file_path: Path) -> ParseResult:
        """Parse car-review-specs.csv file."""
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
                "skipped_rows": row_count - len(records),
            },
        )

    def _parse_row(
        self, row: dict, file_path: Path, row_num: int
    ) -> Optional[CarRecord]:
        """Parse a single row from the CSV."""
        # Get manufacturer and model - handle case where make includes model info
        make_raw = row.get("make", "")
        model_raw = row.get("model", "")

        # Extract manufacturer from make (may include model)
        manufacturer, model_prefix = self._extract_manufacturer_from_make(make_raw)

        if not manufacturer:
            return None

        # Combine model_prefix with model_raw if needed
        if model_prefix and model_raw:
            full_model = f"{model_prefix} {model_raw}"
        elif model_prefix:
            full_model = model_prefix
        else:
            full_model = model_raw

        if not full_model:
            return None

        # Handle special case where "Alfa" was split from "Romeo"
        # Model might start with "Romeo " which should be stripped
        if manufacturer == "Alfa Romeo" and full_model.lower().startswith("romeo "):
            full_model = full_model[6:].strip()

        # Clean model name
        model = self._clean_model_name(full_model, manufacturer)

        # Get year
        year = self._parse_year(row.get("year", ""))

        # Detect propulsion type
        engine_type = row.get("engine_type", "")
        propulsion = self._detect_propulsion(engine_type, model)

        # Parse performance metrics
        zero_to_60 = self._parse_float(row.get("zero_to_60_mph", ""))
        zero_to_100 = self._parse_float(row.get("zero_to_100_mph", ""))
        quarter_mile_time = self._parse_float(row.get("quarter_mile_time", ""))
        quarter_mile_speed = self._parse_float(row.get("quarter_mile_speed", ""))
        top_speed = self._parse_float(row.get("top_speed", ""))
        braking_70_0 = self._parse_float(row.get("braking_70_0", ""))
        braking_100_0 = self._parse_float(row.get("braking_100_0", ""))
        skidpad_g = self._parse_float(row.get("skidpad_g", ""))
        power_hp = self._parse_float(row.get("power_hp", ""))
        torque = row.get("torque_lb_ft", "")
        curb_weight = self._parse_float(row.get("curb_weight", ""))

        # Skip entries with no performance data
        has_performance = any(
            [
                zero_to_60,
                zero_to_100,
                quarter_mile_time,
                top_speed,
                braking_70_0,
                skidpad_g,
            ]
        )

        if not has_performance:
            return None

        # Build data dict
        data = {}

        if zero_to_60:
            data["0_60_mph_sec"] = zero_to_60
        if zero_to_100:
            data["0_100_mph_sec"] = zero_to_100
        if quarter_mile_time:
            data["quarter_mile_sec"] = quarter_mile_time
        if quarter_mile_speed:
            data["quarter_mile_speed_mph"] = quarter_mile_speed
        if top_speed:
            data["top_speed_mph"] = top_speed
        if braking_70_0:
            data["braking_70_0_ft"] = braking_70_0
        if braking_100_0:
            data["braking_100_0_ft"] = braking_100_0
        if skidpad_g:
            data["skidpad_g"] = skidpad_g
        if power_hp:
            data["power_hp"] = power_hp
            # Calculate kW
            data["power_kw"] = round(power_hp * 0.7457, 1)
        if torque:
            # Format torque with unit
            torque_val = self._parse_float(torque)
            if torque_val:
                data["torque"] = f"{torque_val:.0f} lb-ft"
        if curb_weight:
            data["curb_weight_lb"] = curb_weight

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
            source_url=row.get("url", ""),
        )
