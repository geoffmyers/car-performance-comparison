#!/usr/bin/env python3
"""
Parser for fueleconomy.gov vehicles.csv data.

This parser extracts vehicle specification data from the EPA's fuel economy database,
providing reliable drivetrain, displacement, cylinders, and vehicle class information.
"""

import csv
import re
from pathlib import Path
from typing import Optional

from etl.parsers.base import BaseParser, CarRecord, ParseResult
from etl.parsers.registry import register_parser


@register_parser("fueleconomy.vehicles")
class VehiclesParser(BaseParser):
    """Parser for fueleconomy.gov vehicles CSV data."""

    SOURCE_NAME = "EPA - Fuel Economy"

    # Vehicle class mapping to body style
    VCLASS_TO_BODY_STYLE = {
        "Two Seaters": "Coupe",
        "Minicompact Cars": "Coupe",
        "Subcompact Cars": "Sedan",
        "Compact Cars": "Sedan",
        "Midsize Cars": "Sedan",
        "Large Cars": "Sedan",
        "Small Station Wagons": "Wagon",
        "Midsize Station Wagons": "Wagon",
        "Vans": "Van",
        "Vans Passenger": "Van",
        "Vans, Cargo Type": "Van",
        "Vans, Passenger Type": "Van",
        "Minivan - 2WD": "Van",
        "Minivan - 4WD": "Van",
        "Sport Utility Vehicle": "SUV",
        "Sport Utility Vehicle - 2WD": "SUV",
        "Sport Utility Vehicle - 4WD": "SUV",
        "Small Sport Utility Vehicle 2WD": "SUV",
        "Small Sport Utility Vehicle 4WD": "SUV",
        "Standard Sport Utility Vehicle 2WD": "SUV",
        "Standard Sport Utility Vehicle 4WD": "SUV",
        "Small Pickup Trucks": "Truck",
        "Small Pickup Trucks 2WD": "Truck",
        "Small Pickup Trucks 4WD": "Truck",
        "Standard Pickup Trucks": "Truck",
        "Standard Pickup Trucks 2WD": "Truck",
        "Standard Pickup Trucks 4WD": "Truck",
        "Standard Pickup Trucks/2WD": "Truck",
        "Standard Pickup Trucks 4WD": "Truck",
        "Pickup Trucks": "Truck",
    }

    # Drivetrain mapping
    DRIVE_TO_DRIVETRAIN = {
        "Front-Wheel Drive": "FWD",
        "Rear-Wheel Drive": "RWD",
        "All-Wheel Drive": "AWD",
        "4-Wheel Drive": "4WD",
        "4-Wheel or All-Wheel Drive": "AWD",
        "2-Wheel Drive": "RWD",  # Default assumption for 2WD
        "Part-time 4-Wheel Drive": "4WD",
    }

    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the file."""
        return (
            file_path.suffix.lower() == ".csv"
            and "vehicles" in file_path.name.lower()
            and "fuel-economy" in str(file_path.parent).lower()
        )

    def parse_file(self, file_path: Path) -> ParseResult:
        """Parse fueleconomy.gov vehicles.csv file."""
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
        make_raw = row.get("make", "").strip()
        model_raw = row.get("model", "").strip()
        year_raw = row.get("year", "").strip()

        if not make_raw or not model_raw:
            return None

        # Normalize manufacturer
        manufacturer = self._normalize_manufacturer(make_raw)
        if not manufacturer:
            return None

        # Clean model name
        model = self._clean_model_name(model_raw, manufacturer)
        if not model:
            return None

        # Parse year
        year = self._parse_year(year_raw)

        # Extract specifications
        cylinders = self._parse_cylinders(row.get("cylinders", ""))
        displacement = self._parse_displacement(row.get("displ", ""))
        drivetrain = self._parse_drivetrain(row.get("drive", ""))
        body_style = self._parse_body_style(row.get("VClass", ""))
        aspiration = self._parse_aspiration(
            row.get("tCharger", ""), row.get("sCharger", "")
        )
        engine_type = self._derive_engine_type(cylinders, row.get("cylinders", ""))

        # Build data dict - only include non-empty values
        data = {}

        if body_style:
            data["body_style"] = body_style
        if engine_type:
            data["engine_type"] = engine_type
        if displacement:
            data["engine_displacement"] = displacement
        if aspiration:
            data["engine_aspiration"] = aspiration
        if drivetrain:
            data["drivetrain"] = drivetrain

        # Only create record if we have some useful specification data
        if not data:
            return None

        # Detect propulsion type from fuel type
        fuel_type = row.get("fuelType1", "")
        propulsion = self._detect_propulsion_from_fuel(fuel_type)

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

    def _parse_cylinders(self, cylinders_str: str) -> Optional[int]:
        """Parse cylinder count from string."""
        if not cylinders_str:
            return None
        try:
            return int(float(cylinders_str))
        except (ValueError, TypeError):
            return None

    def _parse_displacement(self, displ_str: str) -> Optional[float]:
        """Parse displacement from string (already in liters)."""
        if not displ_str:
            return None
        try:
            val = float(displ_str)
            if val > 0:
                return round(val, 1)
            return None
        except (ValueError, TypeError):
            return None

    def _parse_drivetrain(self, drive_str: str) -> Optional[str]:
        """Map drive type to drivetrain."""
        if not drive_str:
            return None
        return self.DRIVE_TO_DRIVETRAIN.get(drive_str)

    def _parse_body_style(self, vclass_str: str) -> Optional[str]:
        """Map vehicle class to body style."""
        if not vclass_str:
            return None
        return self.VCLASS_TO_BODY_STYLE.get(vclass_str)

    def _parse_aspiration(self, tcharger: str, scharger: str) -> Optional[str]:
        """Determine aspiration from turbo/supercharger flags."""
        # T = Turbo, S = Supercharger
        if tcharger and tcharger.upper() == "T":
            return "TC"
        if scharger and scharger.upper() == "S":
            return "SC"
        # If neither flag, we can't determine if NA without more context
        return None

    def _derive_engine_type(
        self, cylinders: Optional[int], cylinders_raw: str
    ) -> Optional[str]:
        """Derive engine type from cylinder count.

        Note: fueleconomy.gov doesn't provide engine configuration (V, I, H),
        so we can only provide cylinder count. For common configurations we
        make reasonable assumptions:
        - 3, 4, 5, 6 cylinders inline = I3, I4, I5, I6
        - 6 cylinders could also be V6 (most common for modern 6-cyl)
        - 8 cylinders = V8 (almost always)
        - 10, 12, 16 = V10, V12, W16
        """
        if cylinders is None:
            return None

        # Map cylinder count to likely configuration
        # For 6 cylinders, V6 is more common in modern cars
        config_map = {
            3: "I3",
            4: "I4",
            5: "I5",
            6: "V6",  # V6 more common than I6 in modern cars
            8: "V8",
            10: "V10",
            12: "V12",
            16: "W16",
        }
        return config_map.get(cylinders)

    def _detect_propulsion_from_fuel(self, fuel_type: str) -> str:
        """Detect propulsion type from fuel type."""
        if not fuel_type:
            return ""

        fuel_lower = fuel_type.lower()
        if "electric" in fuel_lower:
            return "Electric"
        if "diesel" in fuel_lower:
            return "ICE"
        if "gasoline" in fuel_lower or "regular" in fuel_lower or "premium" in fuel_lower:
            return "ICE"
        return ""
