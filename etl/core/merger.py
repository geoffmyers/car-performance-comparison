#!/usr/bin/env python3
"""
Data merging logic for combining records from multiple sources.

This module provides:
- Merging records by year + manufacturer + model key
- Field-level merge (don't overwrite existing values)
- Source tracking for provenance
"""

import csv
from pathlib import Path
from typing import Any, Optional

from etl.parsers.base import CarRecord
from etl.core.manufacturers import ManufacturerNormalizer
from etl.core.schema import Schema


class DataMerger:
    """Merges car records from multiple sources."""

    def __init__(
        self,
        normalizer: ManufacturerNormalizer,
        schema: Schema,
    ):
        """Initialize the merger.

        Args:
            normalizer: ManufacturerNormalizer instance
            schema: Schema instance
        """
        self.normalizer = normalizer
        self.schema = schema

    def load_existing_csv(self, csv_path: Path) -> list[dict[str, Any]]:
        """Load existing car performance data from CSV.

        Also normalizes manufacturer names and updates country codes.

        Args:
            csv_path: Path to CSV file

        Returns:
            List of car data dictionaries
        """
        if not csv_path.exists():
            return []

        cars = []
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Normalize manufacturer name and update country if needed
                manufacturer = row.get("manufacturer", "")
                normalized = self.normalizer.normalize(manufacturer)
                if normalized != manufacturer:
                    row["manufacturer"] = normalized
                # Update country code if empty or manufacturer was normalized
                if not row.get("country") or normalized != manufacturer:
                    row["country"] = self.normalizer.get_country(normalized)
                cars.append(row)
        return cars

    def merge(
        self,
        existing_data: list[dict[str, Any]],
        new_records: list[CarRecord],
    ) -> list[dict[str, Any]]:
        """Merge new records into existing data.

        Uses a two-phase matching strategy:
        1. Exact match with year: (year, manufacturer, model)
        2. Model-only match: (manufacturer, model) for entries without year

        Args:
            existing_data: List of existing car data dicts
            new_records: List of new CarRecord objects

        Returns:
            Merged list of car data dicts
        """
        # Create lookups
        lookup_with_year: dict[tuple, dict] = {}  # (year, manufacturer, model) -> car
        lookup_no_year: dict[tuple, list[dict]] = {}  # (manufacturer, model) -> list of cars

        def add_to_lookups(car: dict):
            """Add car to lookup dictionaries."""
            key_with_year = self._create_key(car, include_year=True)
            key_no_year = self._create_key(car, include_year=False)

            if key_with_year not in lookup_with_year:
                lookup_with_year[key_with_year] = car
            else:
                self._merge_into(lookup_with_year[key_with_year], car)

            # Track all entries by model (for year-less matching)
            if key_no_year not in lookup_no_year:
                lookup_no_year[key_no_year] = []
            # Keep reference to the entry
            if lookup_with_year[key_with_year] not in lookup_no_year[key_no_year]:
                lookup_no_year[key_no_year].append(lookup_with_year[key_with_year])

        # Process existing data
        for car in existing_data:
            add_to_lookups(car.copy())

        # Merge new records
        for record in new_records:
            car_dict = record.to_dict()
            car_dict["source"] = record.source  # Temporary field for merge

            key_with_year = self._create_key(car_dict, include_year=True)
            key_no_year = self._create_key(car_dict, include_year=False)

            # First try exact match with year
            if key_with_year in lookup_with_year:
                self._merge_into(lookup_with_year[key_with_year], car_dict)
            # If new entry has a year, add as new entry
            elif record.year:
                new_car = car_dict.copy()
                source = new_car.pop("source", "")
                new_car["sources"] = source
                if not new_car.get("country"):
                    new_car["country"] = self.normalizer.get_country(
                        new_car.get("manufacturer", "")
                    )
                add_to_lookups(new_car)
            # No year in new entry - try to find matching entry without year
            elif key_no_year in lookup_no_year:
                # Merge into first matching entry
                existing = lookup_no_year[key_no_year][0]
                self._merge_into(existing, car_dict)
            else:
                # Add as new entry
                new_car = car_dict.copy()
                source = new_car.pop("source", "")
                new_car["sources"] = source
                if not new_car.get("country"):
                    new_car["country"] = self.normalizer.get_country(
                        new_car.get("manufacturer", "")
                    )
                add_to_lookups(new_car)

        # Convert back to list and sort
        result = list(lookup_with_year.values())
        result.sort(
            key=lambda x: (
                x.get("manufacturer", ""),
                x.get("model", ""),
                x.get("year") or "",
            )
        )

        return result

    def _create_key(
        self, car: dict[str, Any], include_year: bool = True
    ) -> tuple:
        """Create a unique key for a car.

        Args:
            car: Car data dictionary
            include_year: Whether to include year in key

        Returns:
            Tuple key for comparison
        """
        manufacturer = car.get("manufacturer", "").lower().strip()
        model = self._normalize_model(car.get("model", ""))

        if include_year:
            year = car.get("year") or ""
            return (year, manufacturer, model)
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

    def _merge_into(self, existing: dict[str, Any], new: dict[str, Any]):
        """Merge new car data into existing car data.

        Does NOT overwrite existing values - only fills in empty fields.
        Exception: propulsion is upgraded if new value is more specific.

        Args:
            existing: Existing car data (modified in place)
            new: New car data to merge
        """
        # Fields to merge (don't overwrite if existing has value)
        merge_fields = [
            "year",
            "0_60_mph_sec",
            "0_100_kmh_sec",
            "0_100_mph_sec",
            "0_200_kmh_sec",
            "quarter_mile_sec",
            "quarter_mile_speed_mph",
            "top_speed_mph",
            "top_speed_kmh",
            "power_hp",
            "power_kw",
            "torque",
            "engine",
            "braking_70_0_ft",
            "braking_100_0_ft",
            "skidpad_g",
            "curb_weight_lb",
            "nurburgring_lap_sec",
            "nurburgring_date",
            "nurburgring_driver",
            "top_gear_lap_sec",
            "top_gear_episode",
            "lightning_lap_sec",
            # Vehicle spec fields
            "body_style",
            "doors",
            "seats",
            "engine_type",
            "engine_displacement",
            "engine_aspiration",
            "engine_placement",
            "drivetrain",
        ]

        for field in merge_fields:
            new_val = new.get(field)
            if new_val and not existing.get(field):
                existing[field] = new_val

        # Handle propulsion specially - prefer more specific values
        new_propulsion = new.get("propulsion", "")
        existing_propulsion = existing.get("propulsion", "")
        if new_propulsion:
            if not existing_propulsion:
                existing["propulsion"] = new_propulsion
            elif self._is_more_specific_propulsion(new_propulsion, existing_propulsion):
                existing["propulsion"] = new_propulsion

        # Append source
        existing_sources = existing.get("sources", "")
        new_source = new.get("source", "") or new.get("sources", "")
        if new_source:
            existing_source_list = [
                s.strip() for s in existing_sources.split(",") if s.strip()
            ]
            new_source_list = [s.strip() for s in new_source.split(",") if s.strip()]
            for src in new_source_list:
                if src and src not in existing_source_list:
                    existing_source_list.append(src)
            existing["sources"] = ", ".join(existing_source_list)

    def _is_more_specific_propulsion(self, new: str, existing: str) -> bool:
        """Check if new propulsion value is more specific than existing.

        Specificity order (from least to most specific):
        - ICE < Petrol, Diesel
        - Hybrid < Electric/Petrol, Electric/Diesel
        - Plug-in Hybrid < Electric/Petrol, Electric/Diesel

        Args:
            new: New propulsion value
            existing: Existing propulsion value

        Returns:
            True if new is more specific than existing
        """
        # ICE is the least specific for combustion engines
        if existing == "ICE" and new in ("Petrol", "Diesel"):
            return True
        # Generic Hybrid -> specific Electric/Fuel combo
        if existing in ("Hybrid", "Plug-in Hybrid") and new in ("Electric/Petrol", "Electric/Diesel"):
            return True
        return False

    def deduplicate(
        self, records: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Remove duplicate records.

        Args:
            records: List of car data dicts

        Returns:
            Deduplicated list
        """
        seen = set()
        result = []

        for record in records:
            key = self._create_key(record, include_year=True)
            if key not in seen:
                seen.add(key)
                result.append(record)

        return result
