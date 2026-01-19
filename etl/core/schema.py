#!/usr/bin/env python3
"""
Schema definition and validation.

This module provides:
- Loading schema from YAML configuration
- Field type validation
- Column ordering for output
- Schema metadata access
"""

import re
from pathlib import Path
from typing import Any, Optional

import yaml


class Schema:
    """Data schema definition and validation."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the schema from configuration.

        Args:
            config_path: Path to schema.yaml config file.
                        Defaults to etl/config/schema.yaml
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "schema.yaml"

        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        self._columns = self.config.get("columns", {})
        self._column_order = self.config.get("column_order", [])
        self._categories = self.config.get("categories", [])
        self._conversions = self.config.get("conversions", {})
        self._default_visible = self.config.get("default_visible", [])

    @property
    def version(self) -> str:
        """Get schema version."""
        return self.config.get("version", "1.0.0")

    @property
    def column_order(self) -> list[str]:
        """Get ordered list of column names for output."""
        return self._column_order.copy()

    @property
    def column_names(self) -> list[str]:
        """Get all column names (same as column_order)."""
        return self._column_order.copy()

    @property
    def categories(self) -> list[str]:
        """Get list of column categories."""
        return self._categories.copy()

    @property
    def default_visible_columns(self) -> list[str]:
        """Get list of columns visible by default in UI."""
        return self._default_visible.copy()

    def get_field(self, field_name: str) -> Optional[dict]:
        """Get configuration for a specific field.

        Args:
            field_name: Name of the field

        Returns:
            Field configuration dict, or None if not found
        """
        return self._columns.get(field_name)

    def get_field_type(self, field_name: str) -> str:
        """Get the type of a field.

        Args:
            field_name: Name of the field

        Returns:
            Field type ("string", "numeric"), defaults to "string"
        """
        field = self._columns.get(field_name, {})
        return field.get("type", "string")

    def is_numeric_field(self, field_name: str) -> bool:
        """Check if a field is numeric.

        Args:
            field_name: Name of the field

        Returns:
            True if field is numeric type
        """
        return self.get_field_type(field_name) == "numeric"

    def get_field_unit(self, field_name: str) -> Optional[str]:
        """Get the unit for a field.

        Args:
            field_name: Name of the field

        Returns:
            Unit string (e.g., "seconds", "mph"), or None
        """
        field = self._columns.get(field_name, {})
        return field.get("unit")

    def get_field_range(self, field_name: str) -> tuple[Optional[float], Optional[float]]:
        """Get the valid range for a numeric field.

        Args:
            field_name: Name of the field

        Returns:
            Tuple of (min, max), either may be None
        """
        field = self._columns.get(field_name, {})
        return field.get("min"), field.get("max")

    def get_field_header(self, field_name: str) -> str:
        """Get the display header for a field.

        Args:
            field_name: Name of the field

        Returns:
            Display header, defaults to field name
        """
        field = self._columns.get(field_name, {})
        return field.get("header", field_name)

    def get_field_category(self, field_name: str) -> str:
        """Get the category for a field.

        Args:
            field_name: Name of the field

        Returns:
            Category name, defaults to "General"
        """
        field = self._columns.get(field_name, {})
        return field.get("category", "General")

    def get_fields_by_category(self, category: str) -> list[str]:
        """Get all fields in a category.

        Args:
            category: Category name

        Returns:
            List of field names in the category
        """
        return [
            name
            for name in self._column_order
            if self.get_field_category(name) == category
        ]

    def get_numeric_fields(self) -> list[str]:
        """Get all numeric fields.

        Returns:
            List of numeric field names
        """
        return [name for name in self._column_order if self.is_numeric_field(name)]

    def validate_value(self, field_name: str, value: Any) -> tuple[bool, Optional[str]]:
        """Validate a value against field constraints.

        Args:
            field_name: Name of the field
            value: Value to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        field = self._columns.get(field_name)
        if field is None:
            return True, None  # Unknown fields are allowed

        # Empty values are always valid (fields are optional)
        if value is None or value == "":
            return True, None

        # Check type
        field_type = field.get("type", "string")
        if field_type == "numeric":
            try:
                num_val = float(value)

                # Check range
                min_val = field.get("min")
                max_val = field.get("max")

                if min_val is not None and num_val < min_val:
                    return False, f"Value {num_val} below minimum {min_val}"

                if max_val is not None and num_val > max_val:
                    return False, f"Value {num_val} above maximum {max_val}"

            except (ValueError, TypeError):
                return False, f"Cannot parse numeric value: {value}"

        # Check enum
        enum_values = field.get("enum")
        if enum_values is not None and value not in enum_values:
            return False, f"Value '{value}' not in allowed values: {enum_values}"

        # Check pattern
        pattern = field.get("pattern")
        if pattern is not None:
            if not re.match(pattern, str(value)):
                return False, f"Value '{value}' does not match pattern: {pattern}"

        return True, None

    def validate_record(self, record: dict) -> list[tuple[str, str]]:
        """Validate all fields in a record.

        Args:
            record: Dictionary of field values

        Returns:
            List of (field_name, error_message) for invalid fields
        """
        errors = []

        for field_name, value in record.items():
            is_valid, error = self.validate_value(field_name, value)
            if not is_valid:
                errors.append((field_name, error))

        # Check required fields
        for field_name, config in self._columns.items():
            if config.get("required") and not record.get(field_name):
                errors.append((field_name, "Required field is missing"))

        return errors

    def get_conversion_factor(self, conversion_name: str) -> Optional[float]:
        """Get a unit conversion factor.

        Args:
            conversion_name: Name of conversion (e.g., "mph_to_kmh")

        Returns:
            Conversion factor, or None if not found
        """
        return self._conversions.get(conversion_name)

    def to_dict(self) -> dict:
        """Convert schema to dictionary representation.

        Returns:
            Dictionary representation of schema
        """
        return {
            "version": self.version,
            "columns": self._columns,
            "column_order": self._column_order,
            "categories": self._categories,
        }
