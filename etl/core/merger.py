#!/usr/bin/env python3
"""
Data merging logic for combining records from multiple sources.

This module provides:
- Merging records by year + manufacturer + model key
- Hash-based unique identifier (car_id) generation
- Field-level merge (don't overwrite existing values)
- Source tracking for provenance
"""

import csv
import hashlib
import re
from pathlib import Path
from typing import Any, Optional

from etl.parsers.base import CarRecord
from etl.core.manufacturers import ManufacturerNormalizer
from etl.core.schema import Schema


def generate_car_id(year: str, manufacturer: str, model: str) -> str:
    """Generate a unique car_id hash from year, manufacturer, and model.

    The hash is created by:
    1. Normalizing each component: lowercase, remove all non-alphanumeric chars
    2. Concatenating: year + manufacturer + model
    3. Computing SHA-256 hash and returning first 16 hex chars

    Args:
        year: Model year (e.g., "2024")
        manufacturer: Manufacturer name (e.g., "Porsche")
        model: Model name (e.g., "911 GT3 RS")

    Returns:
        16-character hex string unique identifier

    Examples:
        >>> generate_car_id("2024", "Porsche", "911 GT3 RS")
        'a1b2c3d4e5f67890'
        >>> generate_car_id("2024", "PORSCHE", "911-GT3-RS")
        'a1b2c3d4e5f67890'  # Same result after normalization
    """
    # Normalize: lowercase and remove all non-alphanumeric characters
    def normalize(s: str) -> str:
        if not s:
            return ""
        return re.sub(r"[^a-z0-9]", "", s.lower())

    normalized = normalize(year or "") + normalize(manufacturer) + normalize(model)

    # Generate SHA-256 hash and take first 16 chars
    hash_digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return hash_digest[:16]


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

        Also normalizes manufacturer names, cleans model names, and updates country codes.

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
                # Clean model name to remove test suffixes from historical data
                model = row.get("model", "")
                cleaned_model = self._clean_model_name(model)
                if cleaned_model != model:
                    row["model"] = cleaned_model
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

    def _generate_car_id(self, car: dict[str, Any]) -> str:
        """Generate the car_id hash for a record.

        Args:
            car: Car data dictionary

        Returns:
            16-character hex string unique identifier
        """
        year = str(car.get("year") or "")
        manufacturer = car.get("manufacturer", "")
        model = car.get("model", "")
        return generate_car_id(year, manufacturer, model)

    def add_car_ids(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Add car_id to all records.

        Args:
            records: List of car data dicts

        Returns:
            Same list with car_id added to each record
        """
        for record in records:
            if not record.get("car_id"):
                record["car_id"] = self._generate_car_id(record)
        return records

    def _normalize_model(self, model: str) -> str:
        """Normalize model name for key matching.

        Removes test/review suffixes, parenthetical content, and normalizes whitespace
        to ensure records like "Camaro ZL1 Test" and "Camaro ZL1" match.

        Args:
            model: Model name

        Returns:
            Normalized model name
        """
        import re

        model = model.lower().strip()

        # Remove trailing punctuation
        model = re.sub(r"[;:]+\s*$", "", model)

        # Remove common test/review suffixes (same patterns as BaseParser._clean_model_name)
        # Order matters - more specific patterns first
        suffixes_to_remove = [
            # Long-term road test patterns (most specific first)
            r"\s+long-?\s*term\s+road\s+test\s+wrap-?\s*up\s*[\|–—-]?\s*$",
            # Multi-word patterns (most specific first)
            r"\s+first\s+ride\s+reviews?\s*[\|–—-]?\s*$",
            r"\s+first\s+drive\s+reviews?\s*\d*\s*[\|–—-]?\s*$",
            r"\s+full\s+test\s+reviews?\s*[\|–—-]?\s*$",
            r"\s+test\s+reviews?\s*[\|–—-]?\s*$",
            r"\s+tested\s+reviews?\s*[\|–—-]?\s*$",
            r"\s+test\s+a\s*reviews?\s*[\|–—-]?\s*$",  # Test A Review (typo)
            r"\s+instrumented\s+test\s*[\|–—-]?\s*$",
            r"\s+first\s+drive\s*[\|–—-]?\s*$",
            r"\s+first\s+ride\s*[\|–—-]?\s*$",
            r"\s+prototype\s+ride\s*[\|–—-]?\s*$",
            r"\s+prototype\s+drive\s*[\|–—-]?\s*$",
            r"\s+full\s+test\s*[\|–—-]?\s*$",
            r"\s+by\s+the\s+numbers\s*[\|–—-]?\s*$",
            r"\s+long-?\s*term\s+(test\s+)?(wrap-?\s*(up)?|update|verdict).*$",
            r"\s+long-?\s*term\s+(test|update|verdict)\s*[\|–—-]?\s*$",
            r"\s+road\s+test\s*[\|–—-]?\s*$",  # Road Test
            r"\s+retest\s*[\|–—-]?\s*$",  # Retest
            # Single-word patterns
            r"\s+test\s*[\|–—-]?\s*$",
            r"\s+tested\s*[\|–—-]?\s*$",
            r"\s+review\s*[\|–—-]?\s*$",
            r"\s+reviews\s*[\|–—-]?\s*$",
            r"\s+prototype\s*[\|–—-]?\s*$",
            r"\s+instrumented\s*[\|–—-]?\s*$",
            r"\s+long\s+term\s*[\|–—-]?\s*$",
        ]

        for pattern in suffixes_to_remove:
            model = re.sub(pattern, "", model, flags=re.IGNORECASE)

        # Remove year from model if present in parentheses
        model = re.sub(r"\s*\(\d{4}\)\s*", " ", model).strip()
        # Remove extra specifications in parentheses for basic matching
        base_model = re.sub(r"\s*\([^)]+\)\s*", " ", model).strip()
        base_model = re.sub(r"\s+", " ", base_model)
        return base_model

    def _clean_model_name(self, model: str) -> str:
        """Clean model name by removing test suffixes and normalizing.

        This is used to clean model names when loading existing CSV data.
        Similar to BaseParser._clean_model_name but operates on already-stored data.

        Args:
            model: Raw model name

        Returns:
            Cleaned model name
        """
        import re

        if not model:
            return ""

        original = model

        # Remove trailing punctuation (semicolons, etc.)
        model = re.sub(r"[;:]+\s*$", "", model)

        # Remove "Tested ..." phrases anywhere in the string
        model = re.sub(r"\s+Tested\s+(on|with|using|today).*$", "", model, flags=re.IGNORECASE)
        model = re.sub(r"\s+Tested$", "", model, flags=re.IGNORECASE)

        # Remove common test/review suffixes
        suffixes_to_remove = [
            # Long-term road test patterns (most specific first)
            r"\s+long-?\s*term\s+road\s+test\s+wrap-?\s*up\s*[\|–—-]?\s*$",
            # Multi-word patterns
            r"\s+first\s+ride\s+reviews?\s*[\|–—-]?\s*$",
            r"\s+first\s+drive\s+reviews?\s*\d*\s*[\|–—-]?\s*$",
            r"\s+full\s+test\s+reviews?\s*[\|–—-]?\s*$",
            r"\s+test\s+reviews?\s*[\|–—-]?\s*$",
            r"\s+tested\s+reviews?\s*[\|–—-]?\s*$",
            r"\s+test\s+a\s*reviews?\s*[\|–—-]?\s*$",  # Test A Review (typo)
            r"\s+instrumented\s+test\s*[\|–—-]?\s*$",
            r"\s+first\s+drive\s*[\|–—-]?\s*$",
            r"\s+first\s+ride\s*[\|–—-]?\s*$",
            r"\s+prototype\s+ride\s*[\|–—-]?\s*$",
            r"\s+prototype\s+drive\s*[\|–—-]?\s*$",
            r"\s+full\s+test\s*[\|–—-]?\s*$",
            r"\s+by\s+the\s+numbers\s*[\|–—-]?\s*$",
            r"\s+long-?\s*term\s+(test\s+)?(wrap-?\s*(up)?|update|verdict).*$",
            r"\s+long-?\s*term\s+(test|update|verdict)\s*[\|–—-]?\s*$",
            r"\s+road\s+test\s*[\|–—-]?\s*$",
            r"\s+retest\s*[\|–—-]?\s*$",
            # Single-word patterns
            r"\s+test\s*[\|–—-]?\s*$",
            r"\s+tested\s*[\|–—-]?\s*$",
            r"\s+review\s*[\|–—-]?\s*$",
            r"\s+reviews\s*[\|–—-]?\s*$",
            r"\s+prototype\s*[\|–—-]?\s*$",
            r"\s+instrumented\s*[\|–—-]?\s*$",
            r"\s+long\s+term\s*[\|–—-]?\s*$",
        ]

        for pattern in suffixes_to_remove:
            model = re.sub(pattern, "", model, flags=re.IGNORECASE)

        # Apply model name corrections
        model = self._normalize_model_formatting(model.strip())

        return model

    def _normalize_model_formatting(self, model: str) -> str:
        """Normalize model name formatting, capitalization, and fix typos.

        Args:
            model: Model name after test suffix removal

        Returns:
            Normalized model name with correct formatting
        """
        import re

        if not model:
            return ""

        # Fix UTF-8 mojibake (e.g., "HuracÃ¡n" should be "Huracán")
        try:
            model = model.encode('latin-1').decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass  # Not mojibake, keep original

        # Fix common typos
        typo_fixes = {
            r'\bPamera\b': 'Panamera',  # Porsche Panamera typo
            r'\bLaferrari\b': 'LaFerrari',  # Ferrari LaFerrari
        }
        for pattern, replacement in typo_fixes.items():
            model = re.sub(pattern, replacement, model, flags=re.IGNORECASE)

        # Fix LP model numbers (LP610 4 -> LP610-4, LP 610-4 -> LP610-4)
        model = re.sub(r'\bLP\s*(\d+)\s+(\d+)\b', r'LP\1-\2', model, flags=re.IGNORECASE)
        model = re.sub(r'\bLP\s+(\d+-\d+)\b', r'LP\1', model, flags=re.IGNORECASE)

        # Fix McLaren model capitalization (675Lt -> 675LT, 570Gt -> 570GT)
        model = re.sub(r'\b(\d+)Lt\b', r'\1LT', model)
        model = re.sub(r'\b(\d+)Gt\b', r'\1GT', model)
        model = re.sub(r'\b(\d+)S\b', r'\1S', model)  # Ensure 570S stays correct

        # Fix "Gt R" -> "GT-R" and related patterns (Nissan)
        model = re.sub(r'\bGt R\b', 'GT-R', model)
        model = re.sub(r'\bGt-R\b', 'GT-R', model)
        model = re.sub(r'\bGT R\b', 'GT-R', model)
        model = re.sub(r'\bGTR\b', 'GT-R', model)

        # Fix "Gt Supercar" -> "GT Supercar" (Ford GT context)
        model = re.sub(r'\bGt Supercar\b', 'GT Supercar', model)

        # Fix Porsche 911 GTS capitalization (911 Gts -> 911 GTS)
        model = re.sub(r'\b911\s+Gts\b', '911 GTS', model)
        model = re.sub(r'\bGts\b', 'GTS', model)  # General GTS fix

        # Fix NSX capitalization (Nsx -> NSX)
        model = re.sub(r'\bNsx\b', 'NSX', model)

        # Fix RS model capitalization (Rs7 -> RS7, Rs6 -> RS6, etc.)
        model = re.sub(r'\bRs(\d+)\b', r'RS\1', model)

        # Fix AMG capitalization
        model = re.sub(r'\bAmg\b', 'AMG', model)

        # Fix PDK transmission capitalization
        model = re.sub(r'\bPdk\b', 'PDK', model)

        # Fix common performance suffix capitalization
        model = re.sub(r'\bNismo\b', 'NISMO', model, flags=re.IGNORECASE)

        return model

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
        """Remove duplicate records by merging them together.

        Uses car_id (hash of normalized year+manufacturer+model) as the
        authoritative key for detecting duplicates. When duplicates are found,
        their data is merged together, preferring non-empty values and
        keeping the cleanest model name.

        Args:
            records: List of car data dicts

        Returns:
            Deduplicated list with car_id set on all records
        """
        # First, ensure all records have car_id
        for record in records:
            if not record.get("car_id"):
                record["car_id"] = self._generate_car_id(record)

        # Group records by car_id (authoritative deduplication key)
        grouped: dict[str, list[dict[str, Any]]] = {}

        for record in records:
            car_id = record["car_id"]
            if car_id not in grouped:
                grouped[car_id] = []
            grouped[car_id].append(record)

        # Merge each group
        result = []
        for car_id, group in grouped.items():
            if len(group) == 1:
                result.append(group[0])
            else:
                # Merge all records in the group
                merged = self._merge_duplicates(group)
                # Ensure car_id is preserved
                merged["car_id"] = car_id
                result.append(merged)

        # Sort by manufacturer, model, year
        result.sort(
            key=lambda x: (
                x.get("manufacturer", ""),
                x.get("model", ""),
                x.get("year") or "",
            )
        )

        return result

    def _merge_duplicates(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        """Merge a list of duplicate records into one.

        Prefers:
        - Shorter (cleaner) model names
        - Non-empty field values
        - Combined source lists

        Args:
            records: List of duplicate records to merge

        Returns:
            Single merged record
        """
        # Start with the record that has the cleanest (shortest) model name
        records_sorted = sorted(records, key=lambda r: len(r.get("model", "")))
        base = records_sorted[0].copy()

        # Merge in data from other records
        for other in records_sorted[1:]:
            self._merge_into(base, other)

        return base
