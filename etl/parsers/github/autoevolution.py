#!/usr/bin/env python3
"""
Parser for GitHub autoevolution automobile-models-and-specs data.

This parser joins automobiles.csv with engines.csv and brands.csv
to extract detailed performance specifications from autoevolution.com data.
"""

import csv
import json
import re
from pathlib import Path
from typing import Optional

from etl.parsers.base import BaseParser, CarRecord, ParseResult
from etl.parsers.registry import register_parser


@register_parser("github.autoevolution")
class AutoevolutionParser(BaseParser):
    """Parser for GitHub autoevolution automobile specs data."""

    SOURCE_NAME = "Autoevolution"

    # Drive type mapping
    DRIVE_TYPE_MAP = {
        "Rear Wheel Drive": "RWD",
        "Front Wheel Drive": "FWD",
        "All Wheel Drive": "AWD",
        "Four Wheel Drive": "4WD",
        "4WD": "4WD",
        "AWD": "AWD",
        "RWD": "RWD",
        "FWD": "FWD",
    }

    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the file."""
        return (
            file_path.suffix.lower() == ".csv"
            and file_path.name == "engines.csv"
            and "automobile-models-and-specs" in str(file_path.parent)
        )

    def parse_file(self, file_path: Path) -> ParseResult:
        """Parse autoevolution engines.csv joined with automobiles.csv and brands.csv."""
        self._reset_messages()
        records = []
        row_count = 0
        skipped_count = 0

        file_hash = self._compute_file_hash(file_path)

        # Load brands for manufacturer lookup
        brands_path = file_path.parent / "brands.csv"
        brands = self._load_brands(brands_path)

        # Load automobiles for model/year lookup
        automobiles_path = file_path.parent / "automobiles.csv"
        automobiles = self._load_automobiles(automobiles_path)

        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row_num, row in enumerate(reader, start=2):
                row_count += 1
                record = self._parse_row(row, file_path, row_num, brands, automobiles)
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

    def _load_brands(self, brands_path: Path) -> dict:
        """Load brands.csv into a lookup dictionary.

        Note: The brand_id in automobiles.csv corresponds to url_hash in brands.csv,
        not the id column.
        """
        brands = {}
        if not brands_path.exists():
            return brands

        with open(brands_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Use url_hash as the key since that's what automobiles.csv references
                url_hash = row.get("url_hash", "")
                name = row.get("name", "").strip()
                if url_hash and name:
                    brands[url_hash] = name
        return brands

    def _load_automobiles(self, automobiles_path: Path) -> dict:
        """Load automobiles.csv into a lookup dictionary.

        Note: The CSV columns appear shifted in this dataset:
        - 'name' column contains URL
        - 'image' column contains the actual car name/title
        """
        automobiles = {}
        if not automobiles_path.exists():
            return automobiles

        with open(automobiles_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                auto_id = row.get("id", "")
                # Note: 'image' column actually contains the car name due to column shift
                name = row.get("image", "").strip()
                brand_id = row.get("brand_id", "")
                # 'name' column actually contains the URL
                url = row.get("name", "")
                if auto_id:
                    automobiles[auto_id] = {
                        "name": name,
                        "brand_id": brand_id,
                        "url": url,
                    }
        return automobiles

    def _parse_row(
        self,
        row: dict,
        file_path: Path,
        row_num: int,
        brands: dict,
        automobiles: dict,
    ) -> Optional[CarRecord]:
        """Parse a single engine row."""
        automobile_id = row.get("automobile_id", "")
        specs_json = row.get("specs", "")
        engine_name = row.get("name", "")

        if not automobile_id or not specs_json:
            return None

        # Get automobile info
        auto_info = automobiles.get(automobile_id, {})
        if not auto_info:
            return None

        # Get car name (contains manufacturer at start, like "AC  Aceca 1998-2000...")
        auto_name = auto_info.get("name", "")
        if not auto_name:
            return None

        # Extract manufacturer and model from car name
        # The format is typically "BRAND  Model Year-Year Photos..."
        manufacturer, model, year = self._extract_from_auto_name(auto_name)
        if not model:
            return None

        # Parse specs JSON
        try:
            specs = json.loads(specs_json)
        except (json.JSONDecodeError, TypeError):
            return None

        # Extract performance data
        engine_specs = specs.get("Engine Specs", {})
        perf_specs = specs.get("Performance Specs", {})
        trans_specs = specs.get("Transmission Specs", {})
        weight_specs = specs.get("Weight Specs", {})

        # Build data dict
        data = {}

        # Engine configuration
        engine_config = self._parse_engine_config(engine_specs.get("Cylinders:", ""))
        if engine_config:
            data["engine_type"] = engine_config

        # Displacement
        displacement = self._parse_displacement_cm3(engine_specs.get("Displacement:", ""))
        if displacement:
            data["engine_displacement"] = displacement

        # Aspiration from fuel system
        aspiration = self._parse_aspiration(engine_specs.get("Fuel System:", ""))
        if aspiration:
            data["engine_aspiration"] = aspiration

        # Drivetrain
        drivetrain = self._parse_drivetrain(trans_specs.get("Drive Type:", ""))
        if drivetrain:
            data["drivetrain"] = drivetrain

        # Propulsion
        propulsion = self._detect_propulsion_from_fuel(engine_specs.get("Fuel:", ""))

        # Performance: Top Speed
        top_speed_mph, top_speed_kmh = self._parse_top_speed(perf_specs.get("Top Speed:", ""))
        if top_speed_mph:
            data["top_speed_mph"] = top_speed_mph
        if top_speed_kmh:
            data["top_speed_kmh"] = top_speed_kmh

        # Performance: 0-62 mph (0-100 km/h)
        accel = self._parse_acceleration(perf_specs.get("Acceleration 0-62 Mph (0-100 Kph):", ""))
        if accel:
            data["0_100_kmh_sec"] = accel
            # 0-62 mph is essentially 0-100 km/h, so use same value for 0-60
            data["0_60_mph_sec"] = accel

        # Power
        power_hp, power_kw = self._parse_power(engine_specs.get("Power:", ""))
        if power_hp:
            data["power_hp"] = power_hp
        if power_kw:
            data["power_kw"] = power_kw

        # Torque
        torque = self._parse_torque(engine_specs.get("Torque:", ""))
        if torque:
            data["torque"] = torque

        # Curb weight
        weight = self._parse_weight(weight_specs.get("Unladen Weight:", ""))
        if weight:
            data["curb_weight_lb"] = weight

        # Only create record if we have useful performance data
        if not data:
            return None

        return CarRecord(
            manufacturer=manufacturer,
            model=model,
            year=str(year) if year else None,
            country=self._get_country(manufacturer),
            propulsion=propulsion,
            data=data,
            source=self.SOURCE_NAME,
            source_file=str(file_path),
            source_row=row_num,
            source_url=auto_info.get("url", ""),
        )

    def _extract_from_auto_name(self, auto_name: str) -> tuple[str, str, Optional[int]]:
        """Extract manufacturer, model, and year from automobile name.

        Examples:
            'AC  Aceca 1998-2000 Photos, engines &amp; full specs' -> ('AC', 'Aceca', 1998)
            'BMW  3 Series Sedan 2019 Photos...' -> ('BMW', '3 Series Sedan', 2019)
            'ALFA ROMEO  Giulia 2016 Photos...' -> ('Alfa Romeo', 'Giulia', 2016)

        Returns:
            Tuple of (manufacturer, model, year)
        """
        if not auto_name:
            return "", "", None

        # Remove HTML entities
        auto_name = auto_name.replace("&amp;", "&")

        # Remove common suffixes
        suffixes = [
            "Photos, engines & full specs",
            "Photos, engines &amp; full specs",
            "Photos",
        ]
        for suffix in suffixes:
            if suffix in auto_name:
                auto_name = auto_name.replace(suffix, "").strip()

        # Extract year range pattern (e.g., "1998-2000" or just "2019")
        year_match = re.search(r"(\d{4})(?:-\d{4})?\s*$", auto_name)
        year = None
        if year_match:
            year = int(year_match.group(1))
            auto_name = auto_name[:year_match.start()].strip()

        # The format is "BRAND  Model" with double space separator
        # Split on double space to get manufacturer and model
        parts = auto_name.split("  ", 1)
        if len(parts) == 2:
            make_raw = parts[0].strip()
            model_raw = parts[1].strip()
        else:
            # Try single space split for brands with multiple words
            make_raw, model_raw = self._parse_car_name(auto_name)

        # Normalize manufacturer
        manufacturer = self._normalize_manufacturer(make_raw)
        if not manufacturer:
            return "", "", None

        # Clean model name
        model = self._clean_model_name(model_raw, manufacturer)

        return manufacturer, model, year

    def _parse_engine_config(self, cylinders: str) -> Optional[str]:
        """Parse engine configuration from cylinders string."""
        if not cylinders:
            return None

        cylinders_upper = cylinders.upper().strip()

        # Direct mapping for common configs
        config_map = {
            "V8": "V8",
            "V6": "V6",
            "V10": "V10",
            "V12": "V12",
            "W12": "W12",
            "W16": "W16",
            "I4": "I4",
            "I6": "I6",
            "I3": "I3",
            "H4": "H4",
            "H6": "H6",
            "FLAT 4": "H4",
            "FLAT 6": "H6",
            "FLAT-4": "H4",
            "FLAT-6": "H6",
        }

        for key, value in config_map.items():
            if key in cylinders_upper:
                return value

        # Try to extract number of cylinders
        num_match = re.search(r"(\d+)", cylinders)
        if num_match:
            num = int(num_match.group(1))
            if "V" in cylinders_upper:
                return f"V{num}"
            if "W" in cylinders_upper:
                return f"W{num}"
            # Default to inline for small numbers
            if num <= 6:
                return f"I{num}"

        return None

    def _parse_displacement_cm3(self, displacement: str) -> Optional[float]:
        """Parse displacement from string (in cm3) to liters."""
        if not displacement:
            return None

        # Extract number from strings like "3506 Cm3"
        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:cm3|cc)", displacement, re.IGNORECASE)
        if match:
            cm3 = float(match.group(1))
            liters = cm3 / 1000
            return round(liters, 1)

        return None

    def _parse_aspiration(self, fuel_system: str) -> Optional[str]:
        """Parse aspiration from fuel system string."""
        if not fuel_system:
            return None

        fuel_lower = fuel_system.lower()

        if "turbo" in fuel_lower:
            return "TC"
        if "supercharged" in fuel_lower or "compressor" in fuel_lower:
            return "SC"
        if "naturally aspirated" in fuel_lower:
            return "NA"

        return None

    def _parse_drivetrain(self, drive_type: str) -> Optional[str]:
        """Map drive type to drivetrain."""
        if not drive_type:
            return None

        for key, value in self.DRIVE_TYPE_MAP.items():
            if key.lower() in drive_type.lower():
                return value

        return None

    def _detect_propulsion_from_fuel(self, fuel: str) -> str:
        """Detect propulsion from fuel type."""
        if not fuel:
            return ""

        fuel_lower = fuel.lower()
        if "electric" in fuel_lower:
            return "Electric"
        if "hybrid" in fuel_lower:
            return "Hybrid"
        if "diesel" in fuel_lower:
            return "ICE"
        if "gasoline" in fuel_lower or "petrol" in fuel_lower:
            return "ICE"
        return ""

    def _parse_top_speed(self, speed_str: str) -> tuple[Optional[float], Optional[float]]:
        """Parse top speed from string like '155 Mph (249 Km/H)'."""
        if not speed_str:
            return None, None

        mph = None
        kmh = None

        # Extract mph
        mph_match = re.search(r"(\d+(?:\.\d+)?)\s*mph", speed_str, re.IGNORECASE)
        if mph_match:
            mph = float(mph_match.group(1))

        # Extract km/h
        kmh_match = re.search(r"(\d+(?:\.\d+)?)\s*km/?h", speed_str, re.IGNORECASE)
        if kmh_match:
            kmh = float(kmh_match.group(1))

        return mph, kmh

    def _parse_acceleration(self, accel_str: str) -> Optional[float]:
        """Parse acceleration time from string like '5.6 S'."""
        if not accel_str:
            return None

        match = re.search(r"(\d+(?:\.\d+)?)\s*s", accel_str, re.IGNORECASE)
        if match:
            return float(match.group(1))

        return None

    def _parse_power(self, power_str: str) -> tuple[Optional[float], Optional[float]]:
        """Parse power from string like '257.4 Kw @ 6500 Rpm\n350 Hp @ 6500 Rpm'."""
        if not power_str:
            return None, None

        hp = None
        kw = None

        # Extract hp (look for "Hp" or "HP")
        hp_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:hp|bhp)", power_str, re.IGNORECASE)
        if hp_match:
            hp = float(hp_match.group(1))

        # Extract kW
        kw_match = re.search(r"(\d+(?:\.\d+)?)\s*kw", power_str, re.IGNORECASE)
        if kw_match:
            kw = float(kw_match.group(1))

        return hp, kw

    def _parse_torque(self, torque_str: str) -> Optional[str]:
        """Parse torque from string like '300 Lb-Ft @ 4000 Rpm'."""
        if not torque_str:
            return None

        # Extract lb-ft value
        match = re.search(r"(\d+(?:\.\d+)?)\s*lb-ft", torque_str, re.IGNORECASE)
        if match:
            val = float(match.group(1))
            return f"{val:.0f} lb-ft"

        return None

    def _parse_weight(self, weight_str: str) -> Optional[float]:
        """Parse weight from string like '3560 Lbs (1615 Kg)'."""
        if not weight_str:
            return None

        # Extract lbs value
        match = re.search(r"(\d+(?:\.\d+)?)\s*lbs?", weight_str, re.IGNORECASE)
        if match:
            return float(match.group(1))

        return None
