#!/usr/bin/env python3
"""
Data cleaner for fixing implausible or incorrect values.

This module provides:
- Cleaning implausible acceleration values based on cross-field correlation
- Nullifying values that fail logical consistency checks
- Normalizing source names to short, consistent format
- Extracting years from model names and manufacturers
- Normalizing manufacturer name casing
- Inferring body style from model name keywords
"""

import re
from typing import Any


class DataCleaner:
    """Cleans and fixes implausible data values."""

    # Body style keywords to detect in model names
    # Order matters - check more specific terms first
    BODY_STYLE_KEYWORDS = {
        "Convertible": ["convertible", "cabriolet", "cabrio", "roadster", "spyder", "spider"],
        "Coupe": ["coupe", "coupé"],
        "Wagon": ["wagon", "estate", "avant", "touring", "sportwagen", "allroad", "outback"],
        "Hatchback": ["hatchback", "hatch", "sportback", "liftback"],
        "SUV": ["suv"],
        "Crossover": ["crossover"],
        "Truck": ["truck", "pickup"],
        "Van": ["van", "minivan"],
        "Targa": ["targa"],
        "Sedan": ["sedan", "saloon"],
    }

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
            "year_extracted_from_model": 0,
            "year_extracted_from_manufacturer": 0,
            "year_range_cleaned": 0,
            "manufacturer_case_normalized": 0,
            "model_extracted_from_manufacturer": 0,
            "body_style_inferred": 0,
            "body_style_corrected": 0,
        }

    def clean(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Clean all records, fixing implausible values.

        Args:
            data: List of car data dictionaries

        Returns:
            Cleaned data with implausible values nullified
        """
        for record in data:
            # Fix year-related issues first (may affect other fields)
            self._fix_year_in_manufacturer(record)
            self._fix_year_in_model(record)
            self._fix_year_range_in_model(record)

            # Fix cases where model info is in manufacturer and model is just year range
            self._extract_model_from_manufacturer(record)

            # Normalize manufacturer name casing
            self._normalize_manufacturer_case(record)

            # Infer or correct body style from model name
            self._fix_body_style(record)

            # Clean acceleration values
            self._clean_acceleration_values(record)

            # Normalize source names
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

    def _fix_year_in_manufacturer(self, record: dict[str, Any]) -> None:
        """Extract year from manufacturer name if present.

        Handles patterns like:
        - "2010Ford" -> year="2010", manufacturer="Ford"
        - "2024 Mercedes-AMG" -> year="2024", manufacturer="Mercedes-AMG"

        Args:
            record: Single car data dictionary (modified in place)
        """
        manufacturer = record.get("manufacturer", "")
        if not manufacturer:
            return

        # Pattern: year directly concatenated or with space at start
        # Matches "2010Ford", "2024 Mercedes-AMG", "2011Toyota"
        match = re.match(r"^((?:19|20)\d{2})\s*(.+)$", manufacturer)
        if match:
            extracted_year = match.group(1)
            clean_manufacturer = match.group(2).strip()

            # Only extract if we don't already have a year, or they match
            existing_year = record.get("year", "")
            if not existing_year or existing_year == extracted_year:
                if self.verbose:
                    print(f"  Extracting year from manufacturer: '{manufacturer}' -> year={extracted_year}, manufacturer='{clean_manufacturer}'")

                record["year"] = extracted_year
                record["manufacturer"] = clean_manufacturer
                self.stats["year_extracted_from_manufacturer"] += 1

    def _fix_year_in_model(self, record: dict[str, Any]) -> None:
        """Extract year from model name if present at the start.

        Handles patterns like:
        - "2001 MDX" -> year="2001", model="MDX"
        - "2024 Integra Type S" -> year="2024", model="Integra Type S"

        Args:
            record: Single car data dictionary (modified in place)
        """
        model = record.get("model", "")
        if not model:
            return

        # Pattern: year at start of model name
        match = re.match(r"^((?:19|20)\d{2})\s+(.+)$", model)
        if match:
            extracted_year = match.group(1)
            clean_model = match.group(2).strip()

            # Only extract if we don't already have a year, or they match
            existing_year = record.get("year", "")
            if not existing_year or existing_year == extracted_year:
                if self.verbose:
                    print(f"  Extracting year from model: '{model}' -> year={extracted_year}, model='{clean_model}'")

                record["year"] = extracted_year
                record["model"] = clean_model
                self.stats["year_extracted_from_model"] += 1

    def _fix_year_range_in_model(self, record: dict[str, Any]) -> None:
        """Remove year ranges from model names.

        Handles patterns like:
        - "Giulia 2018-Present" -> model="Giulia", year="2018" (if no year)
        - "Model S 2016-2020" -> model="Model S", year="2016" (if no year)

        Args:
            record: Single car data dictionary (modified in place)
        """
        model = record.get("model", "")
        if not model:
            return

        # Pattern: year range at end of model name
        match = re.search(r"\s+((?:19|20)\d{2})[-–]((?:19|20)\d{2}|Present)$", model, re.IGNORECASE)
        if match:
            start_year = match.group(1)
            clean_model = model[:match.start()].strip()

            # Use start year if no year exists
            existing_year = record.get("year", "")
            if not existing_year:
                record["year"] = start_year

            if self.verbose:
                print(f"  Removing year range from model: '{model}' -> model='{clean_model}'")

            record["model"] = clean_model
            self.stats["year_range_cleaned"] += 1

    def _extract_model_from_manufacturer(self, record: dict[str, Any]) -> None:
        """Extract model name from manufacturer when model is just a year range.

        Handles patterns like:
        - manufacturer="ASTON MARTIN V12 Vantage Roadster", model="2022-Present"
          -> manufacturer="Aston Martin", model="V12 Vantage Roadster", year="2022"

        Args:
            record: Single car data dictionary (modified in place)
        """
        manufacturer = record.get("manufacturer", "")
        model = record.get("model", "")

        if not manufacturer or not model:
            return

        # Only apply when model is a year range pattern
        year_range_match = re.match(r"^((?:19|20)\d{2})[-–]((?:19|20)\d{2}|Present)$", model, re.IGNORECASE)
        if not year_range_match:
            return

        # Known manufacturers (must be ALL CAPS to match source pattern)
        KNOWN_MANUFACTURERS = {
            "ASTON MARTIN": "Aston Martin",
            "ALFA ROMEO": "Alfa Romeo",
            "AUDI": "Audi",
            "BENTLEY": "Bentley",
            "BMW": "BMW",
            "BUGATTI": "Bugatti",
            "CADILLAC": "Cadillac",
            "CHEVROLET": "Chevrolet",
            "CHRYSLER": "Chrysler",
            "DODGE": "Dodge",
            "FERRARI": "Ferrari",
            "FIAT": "Fiat",
            "FORD": "Ford",
            "GMC": "GMC",
            "HONDA": "Honda",
            "HYUNDAI": "Hyundai",
            "INFINITI": "Infiniti",
            "JAGUAR": "Jaguar",
            "JEEP": "Jeep",
            "KIA": "Kia",
            "LAMBORGHINI": "Lamborghini",
            "LAND ROVER": "Land Rover",
            "LEXUS": "Lexus",
            "LINCOLN": "Lincoln",
            "LOTUS": "Lotus",
            "MASERATI": "Maserati",
            "MAZDA": "Mazda",
            "MCLAREN": "McLaren",
            "MERCEDES": "Mercedes-Benz",
            "MERCEDES BENZ": "Mercedes-Benz",
            "MERCEDES-BENZ": "Mercedes-Benz",
            "MINI": "Mini",
            "MITSUBISHI": "Mitsubishi",
            "NISSAN": "Nissan",
            "OPEL": "Opel",
            "PEUGEOT": "Peugeot",
            "PORSCHE": "Porsche",
            "RAM": "Ram",
            "RENAULT": "Renault",
            "ROLLS ROYCE": "Rolls-Royce",
            "ROLLS-ROYCE": "Rolls-Royce",
            "SUBARU": "Subaru",
            "SUZUKI": "Suzuki",
            "TOYOTA": "Toyota",
            "VAUXHALL": "Vauxhall",
            "VOLKSWAGEN": "Volkswagen",
            "VOLVO": "Volvo",
        }

        # Try to match a known manufacturer prefix
        manufacturer_upper = manufacturer.upper()
        for caps_name, proper_name in sorted(KNOWN_MANUFACTURERS.items(), key=lambda x: -len(x[0])):
            if manufacturer_upper.startswith(caps_name + " "):
                # Extract model from the rest of the string
                model_part = manufacturer[len(caps_name):].strip()

                if model_part:
                    # Extract year from the year range
                    start_year = year_range_match.group(1)

                    if self.verbose:
                        print(f"  Extracting model from manufacturer: '{manufacturer}' -> manufacturer='{proper_name}', model='{model_part}', year='{start_year}'")

                    record["manufacturer"] = proper_name
                    record["model"] = model_part
                    if not record.get("year"):
                        record["year"] = start_year

                    self.stats["model_extracted_from_manufacturer"] += 1
                    return

    def _normalize_manufacturer_case(self, record: dict[str, Any]) -> None:
        """Normalize ALL CAPS manufacturer names to proper case.

        Handles patterns like:
        - "MERCEDES" -> "Mercedes"
        - "AUDI" -> "Audi"
        - "BMW" -> "BMW" (kept as-is, common acronym)
        - "ASTON MARTIN V12 Vantage Roadster" -> "Aston Martin" (strip model info)

        Args:
            record: Single car data dictionary (modified in place)
        """
        manufacturer = record.get("manufacturer", "")
        if not manufacturer:
            return

        # Skip if not all caps (allowing hyphens and spaces)
        if not re.match(r"^[A-Z0-9\s\-]+$", manufacturer):
            return

        # Common acronyms to keep as-is
        KEEP_UPPERCASE = {"BMW", "AMG", "GMC", "MG", "TVR", "AC"}

        if manufacturer in KEEP_UPPERCASE:
            return

        # Check if manufacturer contains model info (more than 2-3 words suggests model included)
        words = manufacturer.split()
        if len(words) > 3:
            # Likely has model info - try to extract just manufacturer
            # Known multi-word manufacturers
            MULTI_WORD_MANUFACTURERS = {
                "ASTON MARTIN": "Aston Martin",
                "ALFA ROMEO": "Alfa Romeo",
                "LAND ROVER": "Land Rover",
                "MERCEDES BENZ": "Mercedes-Benz",
                "MERCEDES-BENZ": "Mercedes-Benz",
                "ROLLS ROYCE": "Rolls-Royce",
                "ROLLS-ROYCE": "Rolls-Royce",
            }

            # Try to find a known manufacturer prefix
            for caps_name, proper_name in MULTI_WORD_MANUFACTURERS.items():
                if manufacturer.upper().startswith(caps_name):
                    if self.verbose:
                        print(f"  Normalizing manufacturer: '{manufacturer}' -> '{proper_name}'")
                    record["manufacturer"] = proper_name
                    self.stats["manufacturer_case_normalized"] += 1
                    return

        # Convert to title case
        proper_case = manufacturer.title()

        # Fix common patterns that title() gets wrong
        proper_case = proper_case.replace("-", " ").title().replace(" ", "-") if "-" in manufacturer else proper_case

        if proper_case != manufacturer:
            if self.verbose:
                print(f"  Normalizing manufacturer case: '{manufacturer}' -> '{proper_case}'")
            record["manufacturer"] = proper_case
            self.stats["manufacturer_case_normalized"] += 1

    def _fix_body_style(self, record: dict[str, Any]) -> None:
        """Infer or correct body style from model name keywords.

        - If body_style is missing, try to infer from model name
        - If body_style exists but contradicts model name, correct it

        Args:
            record: Single car data dictionary (modified in place)
        """
        model = record.get("model", "")
        if not model:
            return

        model_lower = model.lower()

        # Detect body style from model name
        detected_style = None
        for style, keywords in self.BODY_STYLE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in model_lower:
                    detected_style = style
                    break
            if detected_style:
                break

        if not detected_style:
            return

        existing_style = record.get("body_style", "")

        if not existing_style:
            # No body style - infer from model name
            if self.verbose:
                print(f"  Inferring body style for '{model}': {detected_style}")
            record["body_style"] = detected_style
            self.stats["body_style_inferred"] += 1
        elif existing_style != detected_style:
            # Body style exists but conflicts with model name
            # Model name is more reliable (e.g., "A5 Coupe" marked as "Sedan")
            if self.verbose:
                print(f"  Correcting body style for '{model}': {existing_style} -> {detected_style}")
            record["body_style"] = detected_style
            self.stats["body_style_corrected"] += 1

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
            print(f"  Year extracted from model: {self.stats['year_extracted_from_model']}")
            print(f"  Year extracted from manufacturer: {self.stats['year_extracted_from_manufacturer']}")
            print(f"  Year ranges cleaned from model: {self.stats['year_range_cleaned']}")
            print(f"  Model extracted from manufacturer: {self.stats['model_extracted_from_manufacturer']}")
            print(f"  Manufacturer names case normalized: {self.stats['manufacturer_case_normalized']}")
            print(f"  Body styles inferred from model: {self.stats['body_style_inferred']}")
            print(f"  Body styles corrected from model: {self.stats['body_style_corrected']}")
            print(f"  Implausible 0-60 values cleared: {self.stats['implausible_0_60_cleared']}")
            print(f"  Source names normalized: {self.stats['sources_normalized']}")
