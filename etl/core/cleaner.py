#!/usr/bin/env python3
"""
Data cleaner for fixing implausible or incorrect values.

This module provides:
- Cleaning implausible acceleration values based on cross-field correlation
- Nullifying values that fail logical consistency checks
"""

from typing import Any


class DataCleaner:
    """Cleans and fixes implausible data values."""

    def __init__(self, verbose: bool = False):
        """Initialize the data cleaner.

        Args:
            verbose: If True, print details about cleaned values
        """
        self.verbose = verbose
        self.stats = {
            "implausible_0_60_cleared": 0,
            "implausible_quarter_mile_cleared": 0,
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

    def _print_stats(self) -> None:
        """Print cleaning statistics."""
        total = sum(self.stats.values())
        if total > 0:
            print(f"\nData cleaning summary:")
            print(f"  Implausible 0-60 values cleared: {self.stats['implausible_0_60_cleared']}")
