#!/usr/bin/env python3
"""
Data cleaner for fixing implausible or incorrect values.

This module provides:
- Cleaning implausible acceleration values based on cross-field correlation
- Nullifying values that fail logical consistency checks
- Normalizing source names to short, consistent format
"""

import re
from typing import Any


class DataCleaner:
    """Cleans and fixes implausible data values."""

    # Source name normalization mappings
    # Maps verbose source names to their short canonical form
    SOURCE_NAME_PATTERNS = [
        # Wikipedia patterns - consolidate all Wikipedia sources
        (r"Wikipedia\s*-\s*.*", "Wikipedia"),
        # Car & Driver patterns
        (r"Car & Driver\s*-\s*Lightning\s*Lap", "Car & Driver"),
        (r"Car\s*&\s*Driver\s*-\s*.*", "Car & Driver"),
        # EPA/Fuel Economy patterns
        (r"EPA\s*-\s*Fuel\s*Economy", "EPA"),
        (r"EPA\s*-\s*.*", "EPA"),
        # Kaggle patterns
        (r"Kaggle\s*-\s*Car\s*Specifications", "Kaggle"),
        (r"Kaggle\s*-\s*.*", "Kaggle"),
    ]

    def __init__(self, verbose: bool = False):
        """Initialize the data cleaner.

        Args:
            verbose: If True, print details about cleaned values
        """
        self.verbose = verbose
        self.stats = {
            "implausible_0_60_cleared": 0,
            "implausible_quarter_mile_cleared": 0,
            "sources_normalized": 0,
        }

    def clean(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Clean all records, fixing implausible values.

        Args:
            data: List of car data dictionaries

        Returns:
            Cleaned data with implausible values nullified
        """
        for record in data:
            self._clean_acceleration_values(record)
            self._normalize_sources(record)

        if self.verbose:
            self._print_stats()

        return data

    def _clean_acceleration_values(self, record: dict[str, Any]) -> None:
        """Clean implausible acceleration values based on correlation.

        If 0-60 and quarter mile times don't correlate logically,
        clear the 0-60 value as it's more likely to be incorrectly parsed.

        Args:
            record: Single car data dictionary (modified in place)
        """
        zero_60 = self._get_float(record, "0_60_mph_sec")
        quarter_mile = self._get_float(record, "quarter_mile_sec")

        if zero_60 is None or quarter_mile is None:
            return

        # Quarter mile should always be greater than 0-60
        if quarter_mile <= zero_60:
            self._clear_value(record, "0_60_mph_sec", zero_60, quarter_mile, "0-60 >= quarter mile")
            return

        # Sub-2 second 0-60 requires sub-10 second quarter mile (hypercars only)
        if zero_60 < 2.0 and quarter_mile > 10.0:
            self._clear_value(record, "0_60_mph_sec", zero_60, quarter_mile, "sub-2s 0-60 but quarter mile > 10s")
            return

        # Sub-4 second 0-60 should not have quarter mile > 14s
        if zero_60 < 4.0 and quarter_mile > 14.0:
            self._clear_value(record, "0_60_mph_sec", zero_60, quarter_mile, "sub-4s 0-60 but quarter mile > 14s")
            return

        # Very slow quarter mile (> 18s) should not have fast 0-60 (< 6s)
        if zero_60 < 6.0 and quarter_mile > 18.0:
            self._clear_value(record, "0_60_mph_sec", zero_60, quarter_mile, "sub-6s 0-60 but quarter mile > 18s")
            return

    def _clear_value(
        self,
        record: dict[str, Any],
        field: str,
        zero_60: float,
        quarter_mile: float,
        reason: str,
    ) -> None:
        """Clear a field value and log the action.

        Args:
            record: Car data dictionary
            field: Field name to clear
            zero_60: The 0-60 value being cleared
            quarter_mile: The quarter mile value for context
            reason: Human-readable reason for clearing
        """
        car_id = self._get_car_id(record)

        if self.verbose:
            print(f"  Clearing {field} for {car_id}: {zero_60}s (quarter mile: {quarter_mile}s) - {reason}")

        record[field] = None
        self.stats["implausible_0_60_cleared"] += 1

    def _get_float(self, record: dict[str, Any], field: str) -> float | None:
        """Safely get a float value from a record."""
        value = record.get(field)
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _get_car_id(self, record: dict[str, Any]) -> str:
        """Get a human-readable identifier for a car record."""
        parts = []
        if record.get("year"):
            parts.append(str(record["year"]))
        if record.get("manufacturer"):
            parts.append(record["manufacturer"])
        if record.get("model"):
            parts.append(record["model"])
        return " ".join(parts) if parts else "Unknown car"

    def _normalize_sources(self, record: dict[str, Any]) -> None:
        """Normalize source names to short, consistent format.

        Converts verbose source names like "Wikipedia - List of Nürburgring Nordschleife lap times"
        to just "Wikipedia", and deduplicates the resulting list.

        Args:
            record: Single car data dictionary (modified in place)
        """
        sources = record.get("sources", "")
        if not sources:
            return

        # Split comma-separated sources
        source_list = [s.strip() for s in sources.split(",")]

        # Normalize each source
        normalized = []
        for source in source_list:
            norm_source = self._normalize_source_name(source)
            if norm_source and norm_source not in normalized:
                normalized.append(norm_source)

        # Update record if sources changed
        new_sources = ", ".join(normalized)
        if new_sources != sources:
            record["sources"] = new_sources
            self.stats["sources_normalized"] += 1

    def _normalize_source_name(self, source: str) -> str:
        """Normalize a single source name.

        Args:
            source: Source name to normalize

        Returns:
            Normalized source name
        """
        source = source.strip()
        if not source:
            return ""

        # Try pattern-based normalization
        for pattern, replacement in self.SOURCE_NAME_PATTERNS:
            if re.match(pattern, source, re.IGNORECASE):
                return replacement

        # Return as-is if no pattern matched
        return source

    def _print_stats(self) -> None:
        """Print cleaning statistics."""
        total = sum(self.stats.values())
        if total > 0:
            print(f"\nData cleaning summary:")
            print(f"  Implausible 0-60 values cleared: {self.stats['implausible_0_60_cleared']}")
            print(f"  Source names normalized: {self.stats['sources_normalized']}")
