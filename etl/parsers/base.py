#!/usr/bin/env python3
"""
Base parser class for all data source parsers.

This module provides:
- CarRecord dataclass for representing parsed car data
- ParseResult dataclass for parser output
- BaseParser abstract class that all parsers inherit from
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Optional
import hashlib


@dataclass
class CarRecord:
    """Represents a single car data record with provenance."""

    manufacturer: str
    model: str
    year: Optional[str] = None
    country: Optional[str] = None
    propulsion: Optional[str] = None

    # Performance metrics and other data (all optional)
    data: dict[str, Any] = field(default_factory=dict)

    # Provenance tracking
    source: str = ""
    source_file: str = ""
    source_row: int = 0
    source_url: str = ""

    def get_key(self, include_year: bool = True) -> tuple:
        """Generate unique key for deduplication.

        Args:
            include_year: Whether to include year in the key

        Returns:
            Tuple key for comparison
        """
        manufacturer = self.manufacturer.lower().strip()
        model = self._normalize_model(self.model)

        if include_year and self.year:
            return (self.year, manufacturer, model)
        return (manufacturer, model)

    def _normalize_model(self, model: str) -> str:
        """Normalize model name for key matching.

        Args:
            model: Model name

        Returns:
            Normalized model name
        """
        import re

        model = model.lower().strip()
        # Remove year from model if present in parentheses
        model = re.sub(r"\s*\(\d{4}\)\s*", " ", model).strip()
        # Remove extra specifications in parentheses for basic matching
        base_model = re.sub(r"\s*\([^)]+\)\s*", " ", model).strip()
        base_model = re.sub(r"\s+", " ", base_model)
        return base_model

    def to_dict(self) -> dict[str, Any]:
        """Convert to flat dictionary for CSV output.

        Returns:
            Dictionary with all fields
        """
        result = {
            "manufacturer": self.manufacturer,
            "country": self.country or "",
            "model": self.model,
            "year": self.year or "",
            "propulsion": self.propulsion or "",
        }
        result.update(self.data)
        return result

    def has_performance_data(self) -> bool:
        """Check if record has any performance data.

        Returns:
            True if any performance metric is present
        """
        performance_fields = [
            "0_60_mph_sec",
            "0_100_kmh_sec",
            "0_100_mph_sec",
            "0_200_kmh_sec",
            "quarter_mile_sec",
            "top_speed_mph",
            "top_speed_kmh",
            "nurburgring_lap_sec",
            "top_gear_lap_sec",
            "lightning_lap_sec",
            "power_hp",
            "power_kw",
        ]
        return any(self.data.get(f) for f in performance_fields)


@dataclass
class ParseResult:
    """Result from parsing a source file."""

    records: list[CarRecord]
    source_name: str
    source_file: str
    file_hash: str
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        """Check if parsing was successful (no errors)."""
        return len(self.errors) == 0

    @property
    def record_count(self) -> int:
        """Get number of records parsed."""
        return len(self.records)

    def summary(self) -> str:
        """Get a summary of the parse result.

        Returns:
            Human-readable summary string
        """
        lines = [
            f"Source: {self.source_name}",
            f"File: {self.source_file}",
            f"Records: {self.record_count}",
        ]
        if self.warnings:
            lines.append(f"Warnings: {len(self.warnings)}")
        if self.errors:
            lines.append(f"Errors: {len(self.errors)}")
        return "\n".join(lines)


class BaseParser(ABC):
    """Abstract base class for all data source parsers."""

    # Class-level configuration (override in subclasses)
    SOURCE_NAME: str = ""
    SUPPORTED_FORMATS: list[str] = ["csv"]

    def __init__(
        self,
        manufacturer_normalizer,
        converter,
        schema,
    ):
        """Initialize the parser.

        Args:
            manufacturer_normalizer: ManufacturerNormalizer instance
            converter: ValueConverter instance
            schema: Schema instance
        """
        self.normalizer = manufacturer_normalizer
        self.converter = converter
        self.schema = schema
        self._warnings: list[str] = []
        self._errors: list[str] = []

    @abstractmethod
    def parse_file(self, file_path: Path) -> ParseResult:
        """Parse a single source file and return records.

        Args:
            file_path: Path to the file to parse

        Returns:
            ParseResult with list of CarRecord objects
        """
        pass

    @abstractmethod
    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the given file.

        Args:
            file_path: Path to check

        Returns:
            True if this parser can handle the file
        """
        pass

    def parse_directory(
        self, directory: Path, pattern: str = "*.csv"
    ) -> Iterator[ParseResult]:
        """Parse all matching files in a directory.

        Args:
            directory: Directory to scan
            pattern: Glob pattern for files

        Yields:
            ParseResult for each parsed file
        """
        for file_path in sorted(directory.glob(pattern)):
            if self.can_parse(file_path):
                yield self.parse_file(file_path)

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of file for change detection.

        Args:
            file_path: Path to file

        Returns:
            Hex string of SHA-256 hash
        """
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _reset_messages(self):
        """Reset warnings and errors for a new parse operation."""
        self._warnings = []
        self._errors = []

    def _warn(
        self, message: str, file_path: Optional[Path] = None, row: Optional[int] = None
    ):
        """Record a parsing warning.

        Args:
            message: Warning message
            file_path: Source file (optional)
            row: Row number (optional)
        """
        location = ""
        if file_path:
            location = f"[{file_path.name}"
            if row is not None:
                location += f":{row}"
            location += "] "
        self._warnings.append(f"{location}{message}")

    def _error(
        self, message: str, file_path: Optional[Path] = None, row: Optional[int] = None
    ):
        """Record a parsing error.

        Args:
            message: Error message
            file_path: Source file (optional)
            row: Row number (optional)
        """
        location = ""
        if file_path:
            location = f"[{file_path.name}"
            if row is not None:
                location += f":{row}"
            location += "] "
        self._errors.append(f"{location}{message}")

    # Convenience methods that delegate to the normalizer and converter

    def _parse_car_name(self, text: str) -> tuple[str, str]:
        """Parse car name into (manufacturer, model)."""
        return self.normalizer.parse_car_name(text)

    def _normalize_manufacturer(self, manufacturer: str) -> str:
        """Normalize manufacturer name."""
        return self.normalizer.normalize(manufacturer)

    def _extract_manufacturer_from_make(self, make_str: str) -> tuple[str, str]:
        """Extract manufacturer from make string that may include model."""
        return self.normalizer.extract_manufacturer_from_make(make_str)

    def _get_country(self, manufacturer: str) -> str:
        """Get country code for manufacturer."""
        return self.normalizer.get_country(manufacturer)

    def _parse_time(self, value: str) -> Optional[float]:
        """Parse time value (mm:ss.s or seconds)."""
        return self.converter.parse_time(value)

    def _parse_speed(self, value: str) -> tuple[Optional[float], Optional[float]]:
        """Parse speed value to (mph, km/h)."""
        return self.converter.parse_speed(value)

    def _parse_power(self, value: str) -> tuple[Optional[float], Optional[float]]:
        """Parse power value to (hp, kW)."""
        return self.converter.parse_power(value)

    def _parse_float(self, value: str) -> Optional[float]:
        """Parse float value."""
        return self.converter.parse_float(value)

    def _parse_year(self, value: str) -> Optional[str]:
        """Parse year from string."""
        return self.converter.parse_year(value)

    def _clean_text(self, text: str) -> str:
        """Clean text by removing footnotes and extra whitespace."""
        return self.converter.clean_text(text)

    def _detect_propulsion(self, engine_type: str, model_name: str = "") -> str:
        """Detect propulsion type from engine description."""
        return self.converter.detect_propulsion(engine_type, model_name)

    def _clean_model_name(self, model: str, manufacturer: str = "") -> str:
        """Clean model name by removing test suffixes and article artifacts.

        Args:
            model: Raw model name
            manufacturer: Manufacturer (for context)

        Returns:
            Cleaned model name
        """
        import re
        import html

        if not model:
            return ""

        # Decode HTML entities (e.g., &#8211; -> –)
        model = html.unescape(model)

        model = self._clean_text(model)

        # Remove trailing pipes and dashes (often from truncated titles)
        model = re.sub(r"\s*[\|–—-]\s*$", "", model)

        # Remove common test/review suffixes (with optional trailing pipe/dash)
        # Order matters - more specific patterns first
        # Note: [\|–—-] matches pipe, en-dash, em-dash, and hyphen
        suffixes_to_remove = [
            # Multi-word patterns (most specific first)
            r"\s+first\s+drive\s+reviews?\s*\d*\s*[\|–—-]?\s*$",  # First Drive Review(s) with optional number
            r"\s+instrumented\s+test\s*[\|–—-]?\s*$",
            r"\s+first\s+drive\s*[\|–—-]?\s*$",
            r"\s+first\s+ride\s*[\|–—-]?\s*$",
            r"\s+prototype\s+ride\s*[\|–—-]?\s*$",
            r"\s+prototype\s+drive\s*[\|–—-]?\s*$",
            r"\s+full\s+test\s*[\|–—-]?\s*$",
            r"\s+by\s+the\s+numbers\s*[\|–—-]?\s*$",
            r"\s+long-?\s*term\s+(test\s+)?(wrap-?\s*(up)?|update|verdict).*$",
            r"\s+long-?\s*term\s+(test|update|verdict)\s*[\|–—-]?\s*$",
            # Single-word patterns
            r"\s+test\s*[\|–—-]?\s*$",
            r"\s+tested\s*[\|–—-]?\s*$",
            r"\s+review\s*[\|–—-]?\s*$",
            r"\s+reviews\s*[\|–—-]?\s*$",
            r"\s+prototype\s*[\|–—-]?\s*$",
            r"\s+instrumented\s*[\|–—-]?\s*$",
            r"\s+long\s+term\s*[\|–—-]?\s*$",
            # Truncated patterns (e.g., "Full T" from "Full Test", "Ted" from "Tested")
            r"\s+full\s+t\s*[\|–—-]?\s*$",
            r"\s+ted\s*[\|–—-]?\s*$",  # Truncated "Tested"
            r"\s+t\s*[\|–—-]?\s*$",  # Single T at end (truncated "Test")
        ]

        for pattern in suffixes_to_remove:
            model = re.sub(pattern, "", model, flags=re.IGNORECASE)

        # Handle case where entire model is just a test suffix (e.g., "First Drive")
        # These should return empty to let the parser use manufacturer-derived model
        full_suffix_patterns = [
            r"^first\s+drive\s*\|?\s*$",
            r"^first\s+ride\s*\|?\s*$",
            r"^prototype\s+ride\s*\|?\s*$",
            r"^instrumented\s+test\s*\|?\s*$",
            r"^test\s*\|?\s*$",
            r"^review\s*\|?\s*$",
        ]
        for pattern in full_suffix_patterns:
            if re.match(pattern, model, flags=re.IGNORECASE):
                return ""

        # Clean up any remaining trailing pipes/dashes after suffix removal
        model = re.sub(r"\s*[\|–—-]\s*$", "", model)

        return model.strip()
