#!/usr/bin/env python3
"""
Parser for Kaggle Car Specification Dataset by Jahaidul Islam.

This parser extracts vehicle specification data from the comprehensive
Kaggle dataset covering cars from 1945-2020, providing body style,
engine configuration, drivetrain, performance metrics, and more.
"""

import csv
import re
from pathlib import Path
from typing import Optional

from etl.parsers.base import BaseParser, CarRecord, ParseResult
from etl.parsers.registry import register_parser


@register_parser("kaggle.jahaidul")
class JahaidulParser(BaseParser):
    """Parser for Kaggle Jahaidul Islam car specification data."""

    SOURCE_NAME = "Kaggle - Car Specifications"

    # Body type mapping to standardized body styles
    BODY_TYPE_MAP = {
        "Sedan": "Sedan",
        "Hatchback": "Hatchback",
        "Hatchback 3 doors": "Hatchback",
        "Wagon": "Wagon",
        "Crossover": "Crossover",
        "Minivan": "Van",
        "Coupe": "Coupe",
        "Pickup": "Truck",
        "Cabriolet": "Convertible",
        "Liftback": "Hatchback",
        "hardtop": "Coupe",
        "Roadster": "Roadster",
        "Targa": "Targa",
        "Fastback": "Coupe",
        "Limousine": "Sedan",
        "SUV": "SUV",
    }

    # Cylinder layout to engine type prefix
    CYLINDER_LAYOUT_MAP = {
        "Inline": "I",
        "inline": "I",
        "V-type": "V",
        "V-type with small angle": "V",
        "Opposed": "H",  # Flat/Boxer
        "opposed": "H",
        "W-type": "W",
        "Rotary-piston": "Rotary",
        "Rotary": "Rotary",
    }

    # Boost type to aspiration
    BOOST_TYPE_MAP = {
        "Turbo": "TC",
        "turbine": "TC",
        "Biturbo": "TC",
        "Twin-scroll": "TC",
        "Triple turbo": "TC",
        "compressor": "SC",
        "Turbine + compressor": "TC",  # Compound forced induction
        "none": "NA",
        "Intercooler": "TC",  # Intercooler implies turbo
    }

    # Drive wheels to drivetrain
    DRIVE_WHEELS_MAP = {
        "Front wheel drive": "FWD",
        "Rear wheel drive": "RWD",
        "All wheel drive (AWD)": "AWD",
        "Four wheel drive (4WD)": "4WD",
        "full": "AWD",
        "Constant all wheel drive": "AWD",
    }

    # Engine placement mapping
    ENGINE_PLACEMENT_MAP = {
        "front, cross-section": "Front",
        "front, longitudinal": "Front",
        "Front, longitudinally": "Front",
        "Front": "Front",
        "central": "Mid",
        "rear": "Rear",
    }

    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the file."""
        return (
            file_path.suffix.lower() == ".csv"
            and "jahaidul" in str(file_path.parent).lower()
            and "car specification" in file_path.name.lower()
        )

    def parse_file(self, file_path: Path) -> ParseResult:
        """Parse Kaggle Jahaidul car specification CSV file."""
        self._reset_messages()
        records = []
        row_count = 0
        skipped_count = 0

        file_hash = self._compute_file_hash(file_path)

        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row_num, row in enumerate(reader, start=2):
                row_count += 1
                record = self._parse_row(row, file_path, row_num)
                if record:
                    records.append(record)
                else:
                    skipped_count += 1

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
                "skipped_rows": skipped_count,
            },
        )

    def _parse_row(
        self, row: dict, file_path: Path, row_num: int
    ) -> Optional[CarRecord]:
        """Parse a single row from the CSV."""
        # Note: Column is misspelled as "Modle" in the source data
        make_raw = row.get("Make", "").strip()
        model_raw = row.get("Modle", "").strip()
        year_from = row.get("Year_from", "").strip()
        trim = row.get("Trim", "").strip()

        if not make_raw or not model_raw:
            return None

        # Normalize manufacturer
        manufacturer = self._normalize_manufacturer(make_raw)
        if not manufacturer:
            return None

        # Build model name from model + trim
        if trim and trim != model_raw:
            full_model = f"{model_raw} {trim}"
        else:
            full_model = model_raw

        # Clean model name
        model = self._clean_model_name(full_model, manufacturer)
        if not model:
            return None

        # Parse year (use Year_from)
        year = self._parse_year(year_from)

        # Extract specifications
        body_style = self._parse_body_style(row.get("Body_type", ""))
        engine_type = self._parse_engine_type(
            row.get("cylinder_layout", ""),
            row.get("number_of_cylinders", "")
        )
        engine_aspiration = self._parse_aspiration(row.get("boost_type", ""))
        engine_placement = self._parse_engine_placement(row.get("engine_placement", ""))
        drivetrain = self._parse_drivetrain(row.get("drive_wheels", ""))

        # Parse displacement (convert cm3 to liters)
        displacement = self._parse_displacement(row.get("capacity_cm3", ""))

        # Detect propulsion from engine_type field
        propulsion = self._detect_propulsion(row.get("engine_type", ""))

        # Parse performance metrics
        accel_0_100 = self._parse_float(row.get("acceleration_0_100_km/h_s", ""))
        top_speed_kmh = self._parse_float(row.get("max_speed_km_per_h", ""))
        power_hp = self._parse_float(row.get("engine_hp", ""))
        power_kw = self._parse_float(row.get("max_power_kw", ""))
        torque_nm = self._parse_float(row.get("maximum_torque_n_m", ""))
        curb_weight_kg = self._parse_float(row.get("curb_weight_kg", ""))

        # Build data dict - only include non-empty values
        data = {}

        if body_style:
            data["body_style"] = body_style
        if engine_type:
            data["engine_type"] = engine_type
        if displacement:
            data["engine_displacement"] = displacement
        if engine_aspiration:
            data["engine_aspiration"] = engine_aspiration
        if engine_placement:
            data["engine_placement"] = engine_placement
        if drivetrain:
            data["drivetrain"] = drivetrain

        # Performance metrics
        if accel_0_100:
            data["0_100_kmh_sec"] = accel_0_100
            # Convert 0-100 km/h to 0-60 mph (approximate)
            # 60 mph = 96.56 km/h, so 0-60 is ~96.56% of 0-100
            data["0_60_mph_sec"] = round(accel_0_100 * 0.9656, 2)

        if top_speed_kmh:
            data["top_speed_kmh"] = top_speed_kmh
            # Convert to mph
            data["top_speed_mph"] = round(top_speed_kmh * 0.621371, 1)

        if power_hp:
            data["power_hp"] = power_hp
            # Calculate kW if not provided
            if not power_kw:
                data["power_kw"] = round(power_hp * 0.7457, 1)
        elif power_kw:
            data["power_kw"] = power_kw
            data["power_hp"] = round(power_kw / 0.7457, 1)

        if torque_nm:
            # Convert N·m to lb-ft
            torque_lbft = round(torque_nm * 0.737562, 0)
            data["torque"] = f"{torque_lbft:.0f} lb-ft"

        if curb_weight_kg:
            # Convert kg to lb
            data["curb_weight_lb"] = round(curb_weight_kg * 2.20462, 0)

        # Only create record if we have some useful data
        if not data:
            return None

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

    def _parse_body_style(self, body_type: str) -> Optional[str]:
        """Map body type to standardized body style."""
        if not body_type:
            return None
        return self.BODY_TYPE_MAP.get(body_type)

    def _parse_engine_type(
        self, cylinder_layout: str, num_cylinders: str
    ) -> Optional[str]:
        """Derive engine type from cylinder layout and count."""
        if not cylinder_layout or not num_cylinders:
            return None

        # Get layout prefix
        prefix = self.CYLINDER_LAYOUT_MAP.get(cylinder_layout)
        if not prefix:
            return None

        # Handle rotary separately
        if prefix == "Rotary":
            return "Rotary"

        # Parse cylinder count
        try:
            cylinders = int(float(num_cylinders))
        except (ValueError, TypeError):
            return None

        return f"{prefix}{cylinders}"

    def _parse_aspiration(self, boost_type: str) -> Optional[str]:
        """Map boost type to aspiration."""
        if not boost_type:
            return None
        return self.BOOST_TYPE_MAP.get(boost_type)

    def _parse_engine_placement(self, placement: str) -> Optional[str]:
        """Map engine placement to standardized value."""
        if not placement or placement == "-":
            return None
        return self.ENGINE_PLACEMENT_MAP.get(placement)

    def _parse_drivetrain(self, drive_wheels: str) -> Optional[str]:
        """Map drive wheels to drivetrain."""
        if not drive_wheels:
            return None
        return self.DRIVE_WHEELS_MAP.get(drive_wheels)

    def _parse_displacement(self, capacity_cm3: str) -> Optional[float]:
        """Convert displacement from cm3 to liters."""
        if not capacity_cm3:
            return None
        try:
            cm3 = float(capacity_cm3)
            liters = cm3 / 1000
            if liters > 0:
                return round(liters, 1)
            return None
        except (ValueError, TypeError):
            return None

    def _detect_propulsion(self, engine_type: str) -> str:
        """Detect propulsion type from engine type field."""
        if not engine_type:
            return ""

        engine_lower = engine_type.lower()
        is_diesel = "diesel" in engine_lower

        if "electric" in engine_lower:
            return "Electric"
        if "hybrid" in engine_lower:
            return "Electric/Diesel" if is_diesel else "Electric/Petrol"
        if is_diesel:
            return "Diesel"
        if "gasoline" in engine_lower or "petrol" in engine_lower or "gas" in engine_lower:
            return "Petrol"
        return ""
