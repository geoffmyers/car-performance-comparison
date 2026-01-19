#!/usr/bin/env python3
"""
Range validator for numeric fields.

This module provides:
- Validation of numeric values against schema-defined ranges
- Warning on outliers
- Error on invalid values
"""

from typing import Any

from etl.core.schema import Schema
from etl.validators.base import BaseValidator, ValidationResult, ValidationIssue, Severity


class RangeValidator(BaseValidator):
    """Validates numeric fields are within expected ranges."""

    def __init__(self, schema: Schema):
        """Initialize the range validator.

        Args:
            schema: Schema instance with field range definitions
        """
        super().__init__("RangeValidator")
        self.schema = schema

    def validate(self, data: list[dict[str, Any]]) -> ValidationResult:
        """Validate all records for range compliance.

        Args:
            data: List of car data dictionaries

        Returns:
            ValidationResult with any range violations
        """
        result = ValidationResult(validator_name=self.name)

        for row_index, record in enumerate(data, start=1):
            issues = self.validate_record(record, row_index)
            result.issues.extend(issues)

        result.records_validated = len(data)
        return result

    def validate_record(
        self, record: dict[str, Any], row_index: int
    ) -> list[ValidationIssue]:
        """Validate a single record for range compliance.

        Args:
            record: Single car data dictionary
            row_index: Row index for error reporting

        Returns:
            List of validation issues
        """
        issues = []

        for field_name in self.schema.get_numeric_fields():
            value = record.get(field_name)

            if value is None or value == "":
                continue

            try:
                num_value = float(value)
            except (ValueError, TypeError):
                issues.append(
                    ValidationIssue(
                        severity=Severity.ERROR,
                        field=field_name,
                        message=f"Cannot parse as numeric: '{value}'",
                        value=value,
                        row_index=row_index,
                    )
                )
                continue

            # Check range
            min_val, max_val = self.schema.get_field_range(field_name)

            if min_val is not None and num_value < min_val:
                # Determine severity based on how far out of range
                if num_value < min_val * 0.5:
                    severity = Severity.ERROR
                else:
                    severity = Severity.WARNING

                car_id = self._get_car_id(record)
                issues.append(
                    ValidationIssue(
                        severity=severity,
                        field=field_name,
                        message=f"Value {num_value} below minimum {min_val}",
                        value=num_value,
                        row_index=row_index,
                        suggestion=f"Check {car_id} - value may be incorrect or use different units",
                    )
                )

            if max_val is not None and num_value > max_val:
                # Determine severity based on how far out of range
                if num_value > max_val * 1.5:
                    severity = Severity.ERROR
                else:
                    severity = Severity.WARNING

                car_id = self._get_car_id(record)
                issues.append(
                    ValidationIssue(
                        severity=severity,
                        field=field_name,
                        message=f"Value {num_value} above maximum {max_val}",
                        value=num_value,
                        row_index=row_index,
                        suggestion=f"Check {car_id} - value may be incorrect or exceptional",
                    )
                )

        return issues

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

    def get_field_statistics(
        self, data: list[dict[str, Any]], field_name: str
    ) -> dict[str, Any]:
        """Get statistics for a numeric field.

        Args:
            data: List of car data dictionaries
            field_name: Name of the field to analyze

        Returns:
            Dictionary with min, max, mean, count statistics
        """
        values = []

        for record in data:
            value = record.get(field_name)
            if value is None or value == "":
                continue
            try:
                values.append(float(value))
            except (ValueError, TypeError):
                continue

        if not values:
            return {
                "count": 0,
                "min": None,
                "max": None,
                "mean": None,
                "schema_min": self.schema.get_field_range(field_name)[0],
                "schema_max": self.schema.get_field_range(field_name)[1],
            }

        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": sum(values) / len(values),
            "schema_min": self.schema.get_field_range(field_name)[0],
            "schema_max": self.schema.get_field_range(field_name)[1],
        }
