#!/usr/bin/env python3
"""
Value conversion and parsing utilities.

This module provides unified parsing for:
- Time values (mm:ss.s format and seconds)
- Speed values (mph, km/h)
- Power values (hp, kW, PS)
- Numeric values with various formats
- Year extraction
- Text cleaning (Wikipedia footnotes, etc.)
"""

import re
from typing import Optional


class ValueConverter:
    """Unified value conversion and parsing utilities."""

    # Unit conversion factors
    MPH_TO_KMH = 1.60934
    KMH_TO_MPH = 0.621371
    HP_TO_KW = 0.7457
    KW_TO_HP = 1.341
    PS_TO_HP = 0.9863
    HP_TO_PS = 1.0139

    def __init__(self):
        """Initialize the converter."""
        # Compile regex patterns for performance
        self._time_pattern = re.compile(
            r"(\d+):(\d{1,2})(?:\.(\d+))?", re.IGNORECASE
        )
        self._seconds_pattern = re.compile(
            r"(\d+(?:\.\d+)?)\s*(?:s|sec|seconds?)?", re.IGNORECASE
        )
        self._speed_pattern = re.compile(
            r"(\d+(?:\.\d+)?)\s*(mph|km/?h|kph)?", re.IGNORECASE
        )
        self._power_pattern = re.compile(
            r"(\d[\d,]*(?:\.\d+)?)\s*(hp|kw|ps|bhp)?", re.IGNORECASE
        )
        self._year_pattern = re.compile(r"\b(19\d{2}|20\d{2})\b")
        self._footnote_pattern = re.compile(
            r"\s*\[[^\]]*\]|\s*\([^)]*citation[^)]*\)|—?N/?[Aa]|\best\.?\b|\bEST\.?\b|\bclaim(?:ed)?\b",
            re.IGNORECASE,
        )

    def parse_time(self, value: str) -> Optional[float]:
        """Parse time value to seconds.

        Handles formats:
        - "6:45.123" -> 405.123
        - "6:45" -> 405.0
        - "45.5" -> 45.5
        - "45.5s" -> 45.5
        - "45.5 sec" -> 45.5

        Args:
            value: Time string

        Returns:
            Time in seconds, or None if parsing fails
        """
        if not value:
            return None

        value = self.clean_text(value)

        # Try mm:ss.sss format first
        match = self._time_pattern.search(value)
        if match:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            fraction = match.group(3)

            total = minutes * 60 + seconds
            if fraction:
                # Handle fractional seconds
                total += float(f"0.{fraction}")

            return round(total, 3)

        # Try plain seconds
        match = self._seconds_pattern.search(value)
        if match:
            try:
                return round(float(match.group(1)), 3)
            except ValueError:
                return None

        return None

    def parse_speed(self, value: str) -> tuple[Optional[float], Optional[float]]:
        """Parse speed value to (mph, km/h).

        Handles formats:
        - "200 mph" -> (200, 321.9)
        - "320 km/h" -> (198.8, 320)
        - "200 mph (321.9 km/h)" -> (200, 321.9)
        - "200" -> (200, 321.9) # Assumes mph

        Args:
            value: Speed string

        Returns:
            Tuple of (mph, kmh), either may be None if parsing fails
        """
        if not value:
            return None, None

        value = self.clean_text(value)

        # Look for both mph and km/h values
        mph_match = re.search(r"(\d+(?:\.\d+)?)\s*mph", value, re.IGNORECASE)
        kmh_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:km/?h|kph)", value, re.IGNORECASE)

        mph = None
        kmh = None

        if mph_match:
            mph = float(mph_match.group(1))
        if kmh_match:
            kmh = float(kmh_match.group(1))

        # If we have one, calculate the other
        if mph is not None and kmh is None:
            kmh = round(mph * self.MPH_TO_KMH, 1)
        elif kmh is not None and mph is None:
            mph = round(kmh * self.KMH_TO_MPH, 1)

        # If neither matched but there's a number, assume mph
        if mph is None and kmh is None:
            match = self._speed_pattern.search(value)
            if match:
                num = float(match.group(1))
                unit = (match.group(2) or "").lower()
                if unit in ("km/h", "kmh", "kph"):
                    kmh = num
                    mph = round(num * self.KMH_TO_MPH, 1)
                else:
                    mph = num
                    kmh = round(num * self.MPH_TO_KMH, 1)

        return mph, kmh

    def parse_power(self, value: str) -> tuple[Optional[float], Optional[float]]:
        """Parse power value to (hp, kW).

        Handles formats:
        - "500 hp" -> (500, 373)
        - "373 kW" -> (500, 373)
        - "507 PS" -> (500, 373)
        - "1,550 kW (2,079 hp; 2,107 PS)" -> (2079, 1550)
        - "500" -> (500, 373) # Assumes hp

        Args:
            value: Power string

        Returns:
            Tuple of (hp, kw), either may be None if parsing fails
        """
        if not value:
            return None, None

        value = self.clean_text(value)

        # Look for explicit units
        hp_match = re.search(r"(\d[\d,]*(?:\.\d+)?)\s*(?:hp|bhp)", value, re.IGNORECASE)
        kw_match = re.search(r"(\d[\d,]*(?:\.\d+)?)\s*kw", value, re.IGNORECASE)
        ps_match = re.search(r"(\d[\d,]*(?:\.\d+)?)\s*ps", value, re.IGNORECASE)

        hp = None
        kw = None

        if hp_match:
            hp = float(hp_match.group(1).replace(",", ""))
        if kw_match:
            kw = float(kw_match.group(1).replace(",", ""))
        if ps_match and hp is None:
            ps = float(ps_match.group(1).replace(",", ""))
            hp = round(ps * self.PS_TO_HP, 1)

        # Calculate missing value
        if hp is not None and kw is None:
            kw = round(hp * self.HP_TO_KW, 1)
        elif kw is not None and hp is None:
            hp = round(kw * self.KW_TO_HP, 1)

        # If no unit found but there's a number, assume hp
        if hp is None and kw is None:
            match = self._power_pattern.search(value)
            if match:
                num = float(match.group(1).replace(",", ""))
                unit = (match.group(2) or "").lower()
                if unit == "kw":
                    kw = num
                    hp = round(num * self.KW_TO_HP, 1)
                elif unit == "ps":
                    hp = round(num * self.PS_TO_HP, 1)
                    kw = round(hp * self.HP_TO_KW, 1)
                else:
                    hp = num
                    kw = round(num * self.HP_TO_KW, 1)

        return hp, kw

    def parse_float(self, value: str) -> Optional[float]:
        """Parse float value from string.

        Handles:
        - "1,234.56" -> 1234.56
        - "1234" -> 1234.0
        - "N/A" -> None
        - "" -> None

        Args:
            value: Numeric string

        Returns:
            Float value, or None if parsing fails
        """
        if not value or value.strip().lower() in ("", "n/a", "-", "—", "n/a"):
            return None

        value = self.clean_text(value)

        # Remove commas and common suffixes
        value = value.replace(",", "")
        value = re.sub(r"\s*(sec|s|mph|km/?h|hp|kw|ft|lb|g)s?\.?$", "", value, flags=re.IGNORECASE)

        try:
            return float(value)
        except ValueError:
            # Try to extract first number
            match = re.search(r"(\d+(?:\.\d+)?)", value)
            if match:
                return float(match.group(1))
            return None

    def parse_year(self, value: str) -> Optional[str]:
        """Extract 4-digit year from string.

        Args:
            value: String containing year

        Returns:
            4-digit year string, or None if not found
        """
        if not value:
            return None

        match = self._year_pattern.search(str(value))
        if match:
            return match.group(1)

        return None

    def clean_text(self, text: str) -> str:
        """Clean text by removing footnotes and extra whitespace.

        Removes:
        - Wikipedia footnotes: [1], [a], [iv], [citation needed]
        - N/A placeholders
        - "est." and "claimed" markers
        - Extra whitespace

        Args:
            text: Input text

        Returns:
            Cleaned text
        """
        if not text:
            return ""

        # Remove footnotes and markers
        text = self._footnote_pattern.sub("", text)

        # Normalize whitespace
        text = " ".join(text.split()).strip()

        return text

    def detect_propulsion(self, engine_type: str, model_name: str = "", fuel_type: str = "") -> str:
        """Detect propulsion type from engine description, model name, or fuel type.

        Args:
            engine_type: Engine type description (e.g., "twin-turbocharged V8")
            model_name: Model name which may contain hints (e.g., "Model S Plaid")
            fuel_type: Fuel type (e.g., "diesel", "gasoline", "petrol")

        Returns:
            One of: "Electric", "Electric/Petrol", "Electric/Diesel", "Petrol", "Diesel", or ""
        """
        combined = f"{engine_type} {model_name} {fuel_type}".lower()

        # Check for diesel indicators
        is_diesel = re.search(r"\bdiesel\b|\btdi\b|\bcdi\b|\bhdi\b|\bjtd\b|\bdci\b", combined) is not None

        # Check for electric indicators
        electric_patterns = [
            r"\belectric\b",
            r"\bbev\b",
            r"\bev\b",
            r"\bbattery\b",
            r"\bpermanent.?magnet\b",
            r"\bac.?motor\b",
            r"\bdc.?motor\b",
            r"\binduction.?motor\b",
        ]
        is_electric = any(re.search(pattern, combined) for pattern in electric_patterns)

        # Check for hybrid indicators
        is_hybrid = re.search(r"\bhybrid\b|\bphev\b|\bplug.?in\b", combined) is not None
        has_ice_components = re.search(r"\bengine\b|\bcylinder\b|\bturbo\b|\bv\d+\b|\binline\b", combined) is not None

        if is_electric:
            if is_hybrid or has_ice_components:
                # Hybrid with electric
                return "Electric/Diesel" if is_diesel else "Electric/Petrol"
            return "Electric"

        # Check for hybrid indicators (without explicit electric mention)
        if is_hybrid:
            return "Electric/Diesel" if is_diesel else "Electric/Petrol"

        # If engine type mentions cylinders, displacement, or turbo, determine fuel type
        if re.search(
            r"\bcylinder\b|\bturbo\b|\bsupercharge\b|\bv\d+\b|\binline\b|\bflat\b|\brotary\b|\b\d+\.\d+\s*l\b",
            combined,
        ):
            return "Diesel" if is_diesel else "Petrol"

        # Default to empty (unknown)
        return ""

    def format_lap_time(self, seconds: float) -> str:
        """Format seconds as mm:ss.s lap time.

        Args:
            seconds: Time in seconds

        Returns:
            Formatted time string (e.g., "6:45.3")
        """
        if seconds is None:
            return ""

        minutes = int(seconds // 60)
        remaining = seconds % 60

        if minutes > 0:
            return f"{minutes}:{remaining:05.2f}"
        else:
            return f"{remaining:.2f}"

    def convert_mph_to_kmh(self, mph: float) -> float:
        """Convert mph to km/h."""
        return round(mph * self.MPH_TO_KMH, 1)

    def convert_kmh_to_mph(self, kmh: float) -> float:
        """Convert km/h to mph."""
        return round(kmh * self.KMH_TO_MPH, 1)

    def convert_hp_to_kw(self, hp: float) -> float:
        """Convert horsepower to kilowatts."""
        return round(hp * self.HP_TO_KW, 1)

    def convert_kw_to_hp(self, kw: float) -> float:
        """Convert kilowatts to horsepower."""
        return round(kw * self.KW_TO_HP, 1)
