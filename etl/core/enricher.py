#!/usr/bin/env python3
"""
Data enrichment module for filling missing values.

This module provides:
- Cross-field derivation (calculate missing values from related fields)
- Pattern-based inference (infer values from model names, body styles, etc.)
- Unit conversions for missing equivalent fields
"""

import re
from typing import Any, Optional


class DataEnricher:
    """Enriches car data by deriving and inferring missing values."""

    # Unit conversion factors
    MPH_TO_KMH = 1.60934
    KMH_TO_MPH = 0.621371
    HP_TO_KW = 0.7457
    KW_TO_HP = 1.341
    # 0-60 mph ≈ 0-100 km/h * 0.9656 (since 60 mph ≈ 96.56 km/h)
    ACCEL_060_TO_0100 = 1.036  # 0-100 km/h is slightly longer than 0-60 mph

    # Engine placement patterns: (manufacturer, model_pattern) -> placement
    ENGINE_PLACEMENT_PATTERNS = [
        # Rear-engine
        (r"^porsche$", r"911|carrera|targa|turbo s$|gt3|gt2", "Rear"),
        (r"^porsche$", r"718|boxster|cayman|spyder", "Mid"),
        (r"^porsche$", r"taycan|panamera|cayenne|macan", "Front"),
        # Mid-engine supercars
        (r"^ferrari$", r"f8|sf90|296|488|458|f430|360|355|348|328|308|288|dino|testarossa|512|enzo|laferrari|f40|f50", "Mid"),
        (r"^ferrari$", r"812|roma|portofino|gtc4|ff|599|612|f12|550|575|456|california|mondial", "Front"),
        (r"^lamborghini$", r"huracan|aventador|gallardo|murcielago|diablo|countach", "Mid"),
        (r"^lamborghini$", r"urus", "Front"),
        (r"^mclaren$", r".*", "Mid"),
        (r"^bugatti$", r".*", "Mid"),
        (r"^koenigsegg$", r".*", "Mid"),
        (r"^pagani$", r".*", "Mid"),
        # Corvette
        (r"^chevrolet$", r"corvette.*c8|corvette.*stingray.*202[0-9]|corvette.*z06.*202[0-9]", "Mid"),
        (r"^chevrolet$", r"corvette", "Front"),
        # Acura/Honda NSX
        (r"^(acura|honda)$", r"nsx", "Mid"),
        # Lotus
        (r"^lotus$", r"elise|exige|evora|emira|evija", "Mid"),
        (r"^lotus$", r"esprit", "Mid"),
        # Alpine
        (r"^alpine$", r"a110", "Mid"),
        # Audi R8
        (r"^audi$", r"r8", "Mid"),
        # Ford GT
        (r"^ford$", r"^gt$|gt40", "Mid"),
        # De Tomaso
        (r"^de tomaso$", r"pantera|mangusta", "Mid"),
        # TVR
        (r"^tvr$", r".*", "Front"),
        # Alfa Romeo
        (r"^alfa romeo$", r"4c|8c", "Mid"),
        # Smart (rear engine)
        (r"^smart$", r"fortwo|eq fortwo", "Rear"),
        # Default: most cars are front-engine
    ]

    # Aspiration patterns from engine description
    ASPIRATION_PATTERNS = [
        (r"twin.?turbo|bi.?turbo|tt\b", "TC"),
        (r"turbo(?:charged)?|t\d+\b|tsi\b|tfsi\b|tdi\b", "TC"),
        (r"super.?charged?|kompressor|blown", "SC"),
        (r"naturally.?aspirated|na\b|n/a\b|atmospheric", "NA"),
    ]

    # Body style to doors mapping
    BODY_STYLE_DOORS = {
        "Coupe": 2,
        "Convertible": 2,
        "Roadster": 2,
        "Targa": 2,
        "Sedan": 4,
        "Wagon": 4,  # Can be 5, but 4 is more common for luxury wagons
        "Hatchback": 4,  # Can be 3 or 5, but 4 is common for hot hatches
        "SUV": 4,
        "Crossover": 4,
        "Truck": 4,  # Most modern trucks are 4-door
        "Van": 4,
    }

    # Body style to seats mapping (typical values)
    BODY_STYLE_SEATS = {
        "Coupe": 4,  # Most coupes have 2+2 seating
        "Convertible": 4,
        "Roadster": 2,
        "Targa": 2,
        "Sedan": 5,
        "Wagon": 5,
        "Hatchback": 5,
        "SUV": 5,
        "Crossover": 5,
        "Truck": 5,
        "Van": 7,
    }

    # Sports car models that typically have 2 seats
    TWO_SEATER_PATTERNS = [
        r"roadster|spider|spyder",
        r"viper|corvette|miata|mx-5|z4|boxster|cayman|elise|exige",
        r"f430|458|488|f8|296|sf90",
        r"huracan|gallardo|aventador|murcielago",
        r"gt-r|gtr|nsx|s2000",
        r"mclaren|pagani|koenigsegg|bugatti",
        r"^(?:sls|amg gt)",
        r"r8 (?!sedan)",
    ]

    def __init__(self, verbose: bool = False):
        """Initialize the enricher.

        Args:
            verbose: If True, print enrichment statistics
        """
        self.verbose = verbose
        self.stats = {
            "speed_conversions": 0,
            "power_conversions": 0,
            "accel_conversions": 0,
            "engine_placement_inferred": 0,
            "aspiration_inferred": 0,
            "doors_inferred": 0,
            "seats_inferred": 0,
        }

    def enrich(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Enrich all records with derived and inferred values.

        Args:
            records: List of car data dictionaries

        Returns:
            Enriched list of car data dictionaries
        """
        for record in records:
            self._enrich_record(record)

        if self.verbose:
            self._print_stats()

        return records

    def _enrich_record(self, record: dict[str, Any]) -> None:
        """Enrich a single record with derived and inferred values.

        Args:
            record: Car data dictionary (modified in place)
        """
        # Cross-field derivations
        self._derive_speed_conversions(record)
        self._derive_power_conversions(record)
        self._derive_acceleration_conversions(record)

        # Pattern-based inference
        self._infer_engine_placement(record)
        self._infer_aspiration(record)
        self._infer_doors(record)
        self._infer_seats(record)

    def _derive_speed_conversions(self, record: dict[str, Any]) -> None:
        """Derive missing speed values from available ones.

        Args:
            record: Car data dictionary (modified in place)
        """
        top_speed_mph = self._parse_float(record.get("top_speed_mph"))
        top_speed_kmh = self._parse_float(record.get("top_speed_kmh"))

        if top_speed_mph and not top_speed_kmh:
            record["top_speed_kmh"] = str(round(top_speed_mph * self.MPH_TO_KMH, 1))
            self.stats["speed_conversions"] += 1
        elif top_speed_kmh and not top_speed_mph:
            record["top_speed_mph"] = str(round(top_speed_kmh * self.KMH_TO_MPH, 1))
            self.stats["speed_conversions"] += 1

    def _derive_power_conversions(self, record: dict[str, Any]) -> None:
        """Derive missing power values from available ones.

        Args:
            record: Car data dictionary (modified in place)
        """
        power_hp = self._parse_float(record.get("power_hp"))
        power_kw = self._parse_float(record.get("power_kw"))

        if power_hp and not power_kw:
            record["power_kw"] = str(round(power_hp * self.HP_TO_KW, 1))
            self.stats["power_conversions"] += 1
        elif power_kw and not power_hp:
            record["power_hp"] = str(round(power_kw * self.KW_TO_HP, 1))
            self.stats["power_conversions"] += 1

    def _derive_acceleration_conversions(self, record: dict[str, Any]) -> None:
        """Derive missing acceleration times from available ones.

        Uses the approximation: 0-100 km/h ≈ 0-60 mph × 1.036

        Args:
            record: Car data dictionary (modified in place)
        """
        accel_060 = self._parse_float(record.get("0_60_mph_sec"))
        accel_0100 = self._parse_float(record.get("0_100_kmh_sec"))

        if accel_060 and not accel_0100:
            # 0-100 km/h is slightly longer than 0-60 mph
            record["0_100_kmh_sec"] = str(round(accel_060 * self.ACCEL_060_TO_0100, 2))
            self.stats["accel_conversions"] += 1
        elif accel_0100 and not accel_060:
            # 0-60 mph is slightly shorter than 0-100 km/h
            record["0_60_mph_sec"] = str(round(accel_0100 / self.ACCEL_060_TO_0100, 2))
            self.stats["accel_conversions"] += 1

    def _infer_engine_placement(self, record: dict[str, Any]) -> None:
        """Infer engine placement from manufacturer and model.

        Args:
            record: Car data dictionary (modified in place)
        """
        if record.get("engine_placement"):
            return

        manufacturer = (record.get("manufacturer") or "").lower().strip()
        model = (record.get("model") or "").lower().strip()

        for mfr_pattern, model_pattern, placement in self.ENGINE_PLACEMENT_PATTERNS:
            if re.match(mfr_pattern, manufacturer, re.IGNORECASE):
                if re.search(model_pattern, model, re.IGNORECASE):
                    record["engine_placement"] = placement
                    self.stats["engine_placement_inferred"] += 1
                    return

        # Default: most vehicles are front-engine
        # Only set if we have some engine info (not electric without motor position)
        engine_type = record.get("engine_type") or ""
        propulsion = record.get("propulsion") or ""
        if engine_type and propulsion != "Electric":
            record["engine_placement"] = "Front"
            self.stats["engine_placement_inferred"] += 1

    def _infer_aspiration(self, record: dict[str, Any]) -> None:
        """Infer engine aspiration from engine description or model name.

        Args:
            record: Car data dictionary (modified in place)
        """
        if record.get("engine_aspiration"):
            return

        # Skip electric vehicles
        propulsion = record.get("propulsion") or ""
        if propulsion == "Electric":
            return

        # Check engine field, engine_type, and model name
        engine = (record.get("engine") or "").lower()
        engine_type = (record.get("engine_type") or "").lower()
        model = (record.get("model") or "").lower()

        combined = f"{engine} {engine_type} {model}"

        for pattern, aspiration in self.ASPIRATION_PATTERNS:
            if re.search(pattern, combined, re.IGNORECASE):
                record["engine_aspiration"] = aspiration
                self.stats["aspiration_inferred"] += 1
                return

        # If we have engine info but no aspiration indicator, assume NA
        if engine_type and not re.search(r"electric|motor", engine_type, re.IGNORECASE):
            record["engine_aspiration"] = "NA"
            self.stats["aspiration_inferred"] += 1

    def _infer_doors(self, record: dict[str, Any]) -> None:
        """Infer door count from body style.

        Args:
            record: Car data dictionary (modified in place)
        """
        if record.get("doors"):
            return

        body_style = record.get("body_style") or ""
        if body_style in self.BODY_STYLE_DOORS:
            record["doors"] = str(self.BODY_STYLE_DOORS[body_style])
            self.stats["doors_inferred"] += 1

    def _infer_seats(self, record: dict[str, Any]) -> None:
        """Infer seat count from body style and model.

        Args:
            record: Car data dictionary (modified in place)
        """
        if record.get("seats"):
            return

        model = (record.get("model") or "").lower()
        body_style = record.get("body_style") or ""

        # Check for known 2-seater models first
        for pattern in self.TWO_SEATER_PATTERNS:
            if re.search(pattern, model, re.IGNORECASE):
                record["seats"] = "2"
                self.stats["seats_inferred"] += 1
                return

        # Fall back to body style defaults
        if body_style in self.BODY_STYLE_SEATS:
            record["seats"] = str(self.BODY_STYLE_SEATS[body_style])
            self.stats["seats_inferred"] += 1

    def _parse_float(self, value: Any) -> Optional[float]:
        """Parse a value as float, handling various formats.

        Args:
            value: Value to parse

        Returns:
            Float value or None
        """
        if value is None or value == "":
            return None
        try:
            # Handle string values
            if isinstance(value, str):
                # Remove units and extra text
                value = re.sub(r"[^\d.-]", "", value.split()[0] if " " in value else value)
            return float(value) if value else None
        except (ValueError, TypeError):
            return None

    def _print_stats(self) -> None:
        """Print enrichment statistics."""
        print("\nData Enrichment Statistics:")
        print(f"  Speed conversions (mph/kmh): {self.stats['speed_conversions']:,}")
        print(f"  Power conversions (hp/kW): {self.stats['power_conversions']:,}")
        print(f"  Acceleration conversions (0-60/0-100): {self.stats['accel_conversions']:,}")
        print(f"  Engine placement inferred: {self.stats['engine_placement_inferred']:,}")
        print(f"  Aspiration inferred: {self.stats['aspiration_inferred']:,}")
        print(f"  Doors inferred: {self.stats['doors_inferred']:,}")
        print(f"  Seats inferred: {self.stats['seats_inferred']:,}")

    def get_stats(self) -> dict[str, int]:
        """Get enrichment statistics.

        Returns:
            Dictionary of enrichment counts
        """
        return self.stats.copy()
