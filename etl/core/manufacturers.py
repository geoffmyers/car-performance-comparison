#!/usr/bin/env python3
"""
Manufacturer name normalization and country lookup.

This module provides a unified interface for:
- Normalizing manufacturer names to canonical forms
- Looking up country codes for manufacturers
- Parsing car names into (manufacturer, model) tuples
"""

import re
from pathlib import Path
from typing import Optional

import yaml


class ManufacturerNormalizer:
    """Handles manufacturer name normalization and country lookup."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the normalizer with configuration.

        Args:
            config_path: Path to manufacturers.yaml config file.
                        Defaults to etl/config/manufacturers.yaml
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "manufacturers.yaml"

        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        self._manufacturers = config.get("manufacturers", {})
        self._aliases = config.get("aliases", {})
        self._multi_word = config.get("multi_word_manufacturers", [])
        self._country_names = config.get("country_names", {})

        # Build sorted list of manufacturers (longest first for matching)
        self._sorted_manufacturers = sorted(
            self._manufacturers.keys(), key=len, reverse=True
        )

        # Build sorted list of multi-word manufacturers (longest first)
        self._sorted_multi_word = sorted(self._multi_word, key=len, reverse=True)

    def normalize(self, manufacturer: str) -> str:
        """Normalize manufacturer name to canonical form.

        Args:
            manufacturer: Raw manufacturer name

        Returns:
            Normalized canonical manufacturer name
        """
        if not manufacturer:
            return ""

        manufacturer = self._clean_text(manufacturer)

        # Check aliases first (exact match)
        if manufacturer in self._aliases:
            return self._aliases[manufacturer]

        # Try title case version
        title_case = manufacturer.title() if manufacturer.islower() else manufacturer
        if title_case in self._aliases:
            return self._aliases[title_case]

        # Check if already canonical
        if manufacturer in self._manufacturers:
            return manufacturer
        if title_case in self._manufacturers:
            return title_case

        return title_case

    def get_country(self, manufacturer: str) -> str:
        """Get ISO country code for manufacturer.

        Args:
            manufacturer: Manufacturer name (will be normalized)

        Returns:
            ISO 3166-1 alpha-2 country code, or empty string if unknown
        """
        normalized = self.normalize(manufacturer)
        mfr_data = self._manufacturers.get(normalized, {})
        if isinstance(mfr_data, dict):
            return mfr_data.get("country", "")
        return ""

    @property
    def country_names(self) -> dict[str, str]:
        """Get the country code to name mapping."""
        return self._country_names.copy()

    @property
    def multi_word(self) -> list[str]:
        """Get the list of multi-word manufacturers."""
        return self._sorted_multi_word.copy()

    def get_country_name(self, country_code: str) -> str:
        """Get country name from ISO code.

        Args:
            country_code: ISO 3166-1 alpha-2 code

        Returns:
            Country name, or empty string if unknown
        """
        return self._country_names.get(country_code, "")

    def is_known(self, manufacturer: str) -> bool:
        """Check if manufacturer is in our database.

        Args:
            manufacturer: Manufacturer name (will be normalized)

        Returns:
            True if manufacturer is known
        """
        normalized = self.normalize(manufacturer)
        return normalized in self._manufacturers

    def parse_car_name(self, text: str) -> tuple[str, str]:
        """Parse car name into (manufacturer, model).

        Handles various formats:
        - "Porsche 911" -> ("Porsche", "911")
        - "Mercedes-AMG GT" -> ("Mercedes-AMG", "GT")
        - "80 Napier" -> ("Napier", "80")  # Model prefix + manufacturer
        - "Alfa Romeo Giulia" -> ("Alfa Romeo", "Giulia")

        Args:
            text: Car name string

        Returns:
            Tuple of (manufacturer, model)
        """
        text = self._clean_text(text)

        if not text:
            return "", ""

        # Try to match multi-word manufacturers first (longest first)
        for manufacturer in self._sorted_multi_word:
            mfr_lower = manufacturer.lower()
            text_lower = text.lower()

            # Check if starts with multi-word manufacturer
            if text_lower.startswith(mfr_lower):
                remaining = text[len(manufacturer) :].strip()
                # Remove leading separators
                remaining = re.sub(r"^[\s\-/]+", "", remaining)
                return self.normalize(manufacturer), remaining

        # Try to match known manufacturers (longest first)
        for manufacturer in self._sorted_manufacturers:
            mfr_lower = manufacturer.lower()
            text_lower = text.lower()

            # Check if starts with manufacturer
            if text_lower.startswith(mfr_lower):
                remaining = text[len(manufacturer) :].strip()
                # Remove leading separators
                remaining = re.sub(r"^[\s\-/]+", "", remaining)
                return self.normalize(manufacturer), remaining

            # Check for manufacturer after leading number/model
            # (e.g., "80 Napier" where 80 is the model)
            match = re.match(
                rf"^([\d\w\-\.]+)\s+({re.escape(manufacturer)})(?:\s+(.*))?$",
                text,
                re.IGNORECASE,
            )
            if match:
                prefix = match.group(1)
                suffix = match.group(3) or ""
                model = f"{prefix} {suffix}".strip() if suffix else prefix
                return self.normalize(manufacturer), model

        # Fallback: split on first space
        parts = text.split(" ", 1)
        if len(parts) == 2:
            # If first part is purely numeric, it's likely a model not manufacturer
            if parts[0].isdigit():
                return "", text  # Unknown manufacturer

            # Check if first part normalizes to a known manufacturer
            normalized_first = self.normalize(parts[0])
            if normalized_first in self._manufacturers:
                return normalized_first, parts[1]

            return normalized_first, parts[1]

        # Single word - treat as manufacturer with no model
        return self.normalize(text), ""

    def extract_manufacturer_from_make(self, make_str: str) -> tuple[str, str]:
        """Extract manufacturer from make string that may include model info.

        This is specifically for Car and Driver data where the "make" field
        sometimes includes model information (e.g., "Toyota Prius" in make column).

        Args:
            make_str: Raw make field value

        Returns:
            Tuple of (manufacturer, model_prefix) where model_prefix may be empty
        """
        if not make_str:
            return "", ""

        make_str = self._clean_text(make_str)

        # First check if the whole string is a known manufacturer
        normalized = self.normalize(make_str)
        if normalized in self._manufacturers:
            return normalized, ""

        # Check for known multi-word manufacturers
        for mfr in self._sorted_multi_word:
            mfr_lower = mfr.lower()
            make_lower = make_str.lower()

            if make_lower.startswith(mfr_lower):
                remaining = make_str[len(mfr) :].strip()
                return self.normalize(mfr), remaining

            # Also check with spaces normalized
            if make_lower.replace(" ", "-") == mfr_lower.replace(" ", "-"):
                return self.normalize(mfr), ""

        # Try to split on first space and check if first word is a manufacturer
        parts = make_str.split(" ", 1)
        if len(parts) >= 1:
            first_normalized = self.normalize(parts[0])
            if first_normalized in self._manufacturers:
                return first_normalized, parts[1] if len(parts) > 1 else ""

        # Return as-is if no match
        return self.normalize(make_str), ""

    def list_manufacturers(self) -> list[str]:
        """Get list of all known manufacturer names.

        Returns:
            Sorted list of canonical manufacturer names
        """
        return sorted(self._manufacturers.keys())

    def list_countries(self) -> list[str]:
        """Get list of all country codes used.

        Returns:
            Sorted list of unique country codes
        """
        countries = set()
        for mfr_data in self._manufacturers.values():
            if isinstance(mfr_data, dict) and "country" in mfr_data:
                countries.add(mfr_data["country"])
        return sorted(countries)

    def _clean_text(self, text: str) -> str:
        """Clean text by removing extra whitespace.

        Args:
            text: Input text

        Returns:
            Cleaned text
        """
        if not text:
            return ""
        return " ".join(text.split()).strip()
