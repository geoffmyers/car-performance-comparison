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

    SOURCE_NAME = "Car & Driver"

    # Files to skip
    SKIP_FILES = {
        "car-review-specs-old.csv",
        "car-review-specs-test.csv",
        "car-review-specs-test2.csv",
        "compare-model-data.csv",
    }

    # Engine configuration patterns
    ENGINE_CONFIG_PATTERNS = [
        (r"\bW-?16\b", "W16"),
        (r"\bW-?12\b", "W12"),
        (r"\bV-?12\b", "V12"),
        (r"\bV-?10\b", "V10"),
        (r"\bV-?8\b", "V8"),
        (r"\bV-?6\b", "V6"),
        (r"\bflat-?6\b", "H6"),
        (r"\bflat-?four\b", "H4"),
        (r"\bflat-?4\b", "H4"),
        (r"\binline-?6\b", "I6"),
        (r"\binline-?5\b", "I5"),
        (r"\binline-?4\b", "I4"),
        (r"\binline-?3\b", "I3"),
        (r"\b4-in-line\b", "I4"),
        (r"\b3-in-line\b", "I3"),
        (r"\brotary\b", "Rotary"),
    ]

    # Body style patterns
    BODY_STYLE_PATTERNS = [
        (r"\bsedan\b", "Sedan"),
        (r"\bcoupe\b", "Coupe"),
        (r"\bconvertible\b", "Convertible"),
        (r"\broadster\b", "Roadster"),
        (r"\btarga\b", "Targa"),
        (r"\bwagon\b", "Wagon"),
        (r"\bhatchback\b", "Hatchback"),
        (r"\bsuv\b", "SUV"),
        (r"\bcrossover\b", "Crossover"),
        (r"\bvan\b", "Van"),
        (r"\btruck\b", "Truck"),
        (r"\bpickup\b", "Truck"),
    ]

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
        engine_type_raw = row.get("engine_type", "")
        propulsion = self._detect_propulsion(engine_type_raw, model)

        # Parse vehicle_type for body style, engine placement, and drivetrain
        vehicle_type = row.get("vehicle_type", "")
        body_style = self._extract_body_style(vehicle_type)
        engine_placement = self._extract_engine_placement(vehicle_type)
        drivetrain = self._extract_drivetrain(vehicle_type)

        # Parse engine configuration, aspiration, and displacement
        engine_config = self._extract_engine_config(engine_type_raw, propulsion)
        engine_aspiration = self._extract_engine_aspiration(engine_type_raw, propulsion)
        displacement_raw = row.get("displacement", "")
        engine_displacement = self._parse_displacement(displacement_raw)

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

        # Add vehicle characteristics
        if body_style:
            data["body_style"] = body_style
        if engine_config:
            data["engine_type"] = engine_config
        if engine_displacement:
            data["engine_displacement"] = engine_displacement
        if engine_aspiration:
            data["engine_aspiration"] = engine_aspiration
        if engine_placement:
            data["engine_placement"] = engine_placement
        if drivetrain:
            data["drivetrain"] = drivetrain

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

    def _extract_body_style(self, vehicle_type: str) -> Optional[str]:
        """Extract body style from vehicle_type string.

        Args:
            vehicle_type: Raw vehicle type string like "front-engine, rear-wheel-drive, 4-passenger, 2-door coupe"

        Returns:
            Normalized body style or None
        """
        if not vehicle_type:
            return None

        vehicle_type_lower = vehicle_type.lower()
        for pattern, style in self.BODY_STYLE_PATTERNS:
            if re.search(pattern, vehicle_type_lower, re.IGNORECASE):
                return style
        return None

    def _extract_engine_placement(self, vehicle_type: str) -> Optional[str]:
        """Extract engine/motor placement from vehicle_type string.

        Args:
            vehicle_type: Raw vehicle type string

        Returns:
            Engine placement (Front, Mid, Rear) or None
        """
        if not vehicle_type:
            return None

        vehicle_type_lower = vehicle_type.lower()

        # Check for mid-engine/mid-motor first (more specific)
        if "mid-engine" in vehicle_type_lower or "mid-motor" in vehicle_type_lower:
            return "Mid"
        # Check for rear-engine/rear-motor
        if "rear-engine" in vehicle_type_lower or "rear-motor" in vehicle_type_lower:
            return "Rear"
        # Check for front-engine/front-motor
        if "front-engine" in vehicle_type_lower or "front-motor" in vehicle_type_lower:
            return "Front"

        return None

    def _extract_drivetrain(self, vehicle_type: str) -> Optional[str]:
        """Extract drivetrain from vehicle_type string.

        Args:
            vehicle_type: Raw vehicle type string

        Returns:
            Drivetrain (FWD, RWD, AWD, 4WD) or None
        """
        if not vehicle_type:
            return None

        vehicle_type_lower = vehicle_type.lower()

        # Check patterns - order matters for overlapping patterns
        if "all-wheel-drive" in vehicle_type_lower:
            return "AWD"
        if "4-wheel-drive" in vehicle_type_lower or "four-wheel-drive" in vehicle_type_lower:
            return "4WD"
        if "rear-wheel-drive" in vehicle_type_lower:
            return "RWD"
        if "front-wheel-drive" in vehicle_type_lower:
            return "FWD"

        return None

    def _extract_engine_config(self, engine_type: str, propulsion: str) -> Optional[str]:
        """Extract engine configuration from engine_type string.

        Args:
            engine_type: Raw engine type string like "twin-turbocharged DOHC 32-valve V-8"
            propulsion: Detected propulsion type

        Returns:
            Engine configuration (I4, V6, V8, etc.) or None
        """
        if not engine_type:
            return None

        # For electric vehicles, return "Electric"
        if propulsion == "Electric":
            return "Electric"

        # Check for engine configuration patterns
        for pattern, config in self.ENGINE_CONFIG_PATTERNS:
            if re.search(pattern, engine_type, re.IGNORECASE):
                return config

        return None

    def _extract_engine_aspiration(self, engine_type: str, propulsion: str) -> Optional[str]:
        """Extract engine aspiration type from engine_type string.

        Args:
            engine_type: Raw engine type string like "twin-turbocharged DOHC 32-valve V-8"
            propulsion: Detected propulsion type

        Returns:
            Aspiration type: TC (Turbocharged), SC (Supercharged), NA (Naturally Aspirated), or None
        """
        if not engine_type:
            return None

        # Electric vehicles don't have aspiration
        if propulsion == "Electric":
            return None

        engine_type_lower = engine_type.lower()

        # Check for turbocharging (includes twin-turbo, bi-turbo, etc.)
        if "turbo" in engine_type_lower:
            return "TC"

        # Check for supercharging
        if "supercharged" in engine_type_lower:
            return "SC"

        # If no forced induction is mentioned and it's an ICE engine, it's naturally aspirated
        # Only return NA if we have enough info to determine it's a combustion engine
        if any(re.search(pattern, engine_type, re.IGNORECASE) for pattern, _ in self.ENGINE_CONFIG_PATTERNS):
            return "NA"

        return None

    def _parse_displacement(self, displacement_str: str) -> Optional[float]:
        """Parse displacement from cubic inches to liters.

        Args:
            displacement_str: Displacement in cubic inches

        Returns:
            Displacement in liters or None
        """
        if not displacement_str:
            return None

        try:
            # Convert cubic inches to liters (1 cubic inch = 0.0163871 liters)
            cubic_inches = float(displacement_str)
            liters = cubic_inches * 0.0163871
            return round(liters, 1)
        except (ValueError, TypeError):
            return None
