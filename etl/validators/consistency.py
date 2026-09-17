#!/usr/bin/env python3
"""
Consistency validator for cross-field validation.

This module provides:
- Cross-field consistency checks (e.g., mph vs km/h values match)
- Required field validation
- Duplicate detection
- Propulsion type validation
"""

from typing import Any

from etl.core.manufacturers import ManufacturerNormalizer
from etl.validators.base import BaseValidator, ValidationResult, ValidationIssue, Severity


class ConsistencyValidator(BaseValidator):
    """Validates cross-field consistency and data integrity."""

    # Conversion tolerances for unit comparisons
    MPH_TO_KMH = 1.60934
    HP_TO_KW = 0.7457
    TOLERANCE = 0.05  # 5% tolerance for unit conversions

    def __init__(self, normalizer: ManufacturerNormalizer | None = None):
        """Initialize the consistency validator.

        Args:
            normalizer: ManufacturerNormalizer for manufacturer validation
        """
        super().__init__("ConsistencyValidator")
        self.normalizer = normalizer or ManufacturerNormalizer()

    def validate(self, data: list[dict[str, Any]]) -> ValidationResult:
        """Validate all records for consistency.

        Args:
            data: List of car data dictionaries

        Returns:
            ValidationResult with any consistency violations
        """
        result = ValidationResult(validator_name=self.name)

        # Per-record validation
        for row_index, record in enumerate(data, start=1):
            issues = self.validate_record(record, row_index)
            result.issues.extend(issues)

        # Cross-record validation
        duplicates = self._find_duplicates(data)
        result.issues.extend(duplicates)

        result.records_validated = len(data)
        return result

    def validate_record(
        self, record: dict[str, Any], row_index: int
    ) -> list[ValidationIssue]:
        """Validate a single record for consistency.

        Args:
            record: Single car data dictionary
            row_index: Row index for error reporting

        Returns:
            List of validation issues
        """
        issues = []

        # Required field validation
        issues.extend(self._validate_required_fields(record, row_index))

        # Unit consistency checks
        issues.extend(self._validate_speed_consistency(record, row_index))
        issues.extend(self._validate_power_consistency(record, row_index))

        # Manufacturer validation
        issues.extend(self._validate_manufacturer(record, row_index))

        # Propulsion type validation
        issues.extend(self._validate_propulsion(record, row_index))

        # Logical consistency
        issues.extend(self._validate_logical_consistency(record, row_index))

        return issues

    def _validate_required_fields(
        self, record: dict[str, Any], row_index: int
    ) -> list[ValidationIssue]:
        """Validate required fields are present."""
        issues = []

        if not record.get("manufacturer"):
            issues.append(
                ValidationIssue(
                    severity=Severity.ERROR,
                    field="manufacturer",
                    message="Missing required field: manufacturer",
                    row_index=row_index,
                )
            )

        if not record.get("model"):
            issues.append(
                ValidationIssue(
                    severity=Severity.ERROR,
                    field="model",
                    message="Missing required field: model",
                    row_index=row_index,
                )
            )

        return issues

    def _validate_speed_consistency(
        self, record: dict[str, Any], row_index: int
    ) -> list[ValidationIssue]:
        """Validate mph and km/h values are consistent."""
        issues = []

        mph = self._get_float(record, "top_speed_mph")
        kmh = self._get_float(record, "top_speed_kmh")

        if mph is not None and kmh is not None:
            expected_kmh = mph * self.MPH_TO_KMH
            diff = abs(kmh - expected_kmh) / expected_kmh if expected_kmh > 0 else 0

            if diff > self.TOLERANCE:
                car_id = self._get_car_id(record)
                issues.append(
                    ValidationIssue(
                        severity=Severity.WARNING,
                        field="top_speed_mph/kmh",
                        message=f"Speed values inconsistent: {mph} mph != {kmh} km/h (expected ~{expected_kmh:.1f} km/h)",
                        value={"mph": mph, "kmh": kmh},
                        row_index=row_index,
                        suggestion=f"Check {car_id} - values may be from different sources",
                    )
                )

        return issues

    def _validate_power_consistency(
        self, record: dict[str, Any], row_index: int
    ) -> list[ValidationIssue]:
        """Validate hp and kW values are consistent."""
        issues = []

        hp = self._get_float(record, "power_hp")
        kw = self._get_float(record, "power_kw")

        if hp is not None and kw is not None:
            expected_kw = hp * self.HP_TO_KW
            diff = abs(kw - expected_kw) / expected_kw if expected_kw > 0 else 0

            if diff > self.TOLERANCE:
                car_id = self._get_car_id(record)
                issues.append(
                    ValidationIssue(
                        severity=Severity.WARNING,
                        field="power_hp/kw",
                        message=f"Power values inconsistent: {hp} hp != {kw} kW (expected ~{expected_kw:.1f} kW)",
                        value={"hp": hp, "kw": kw},
                        row_index=row_index,
                        suggestion=f"Check {car_id} - values may be from different sources",
                    )
                )

        return issues

    def _validate_manufacturer(
        self, record: dict[str, Any], row_index: int
    ) -> list[ValidationIssue]:
        """Validate manufacturer is known."""
        issues = []

        manufacturer = record.get("manufacturer", "")
        if not manufacturer:
            return issues

        # Check if manufacturer is in our known list
        normalized = self.normalizer.normalize(manufacturer)
        country = self.normalizer.get_country(normalized)

        if not country:
            issues.append(
                ValidationIssue(
                    severity=Severity.WARNING,
                    field="manufacturer",
                    message=f"Unknown manufacturer: '{manufacturer}'",
                    value=manufacturer,
                    row_index=row_index,
                    suggestion="Add manufacturer to manufacturers.yaml",
                )
            )

        # Check if country code matches
        record_country = record.get("country", "")
        if country and record_country and country != record_country:
            issues.append(
                ValidationIssue(
                    severity=Severity.WARNING,
                    field="country",
                    message=f"Country code mismatch: record has '{record_country}', manufacturer config has '{country}'",
                    value=record_country,
                    row_index=row_index,
                )
            )

        return issues

    def _validate_propulsion(
        self, record: dict[str, Any], row_index: int
    ) -> list[ValidationIssue]:
        """Validate propulsion type is valid."""
        issues = []

        propulsion = record.get("propulsion", "")
        if not propulsion:
            return issues

        valid_types = {"ICE", "Electric", "Hybrid", "Plug-in Hybrid"}
        if propulsion not in valid_types:
            issues.append(
                ValidationIssue(
                    severity=Severity.WARNING,
                    field="propulsion",
                    message=f"Unknown propulsion type: '{propulsion}'",
                    value=propulsion,
                    row_index=row_index,
                    suggestion=f"Use one of: {', '.join(sorted(valid_types))}",
                )
            )

        return issues

    def _validate_logical_consistency(
        self, record: dict[str, Any], row_index: int
    ) -> list[ValidationIssue]:
        """Validate logical consistency between fields."""
        issues = []

        # 0-60 should be less than 0-100 mph
        zero_60 = self._get_float(record, "0_60_mph_sec")
        zero_100 = self._get_float(record, "0_100_mph_sec")

        if zero_60 is not None and zero_100 is not None:
            if zero_60 >= zero_100:
                car_id = self._get_car_id(record)
                issues.append(
                    ValidationIssue(
                        severity=Severity.ERROR,
                        field="0_60_mph_sec",
                        message=f"0-60 ({zero_60}s) should be less than 0-100 ({zero_100}s)",
                        value={"0-60": zero_60, "0-100": zero_100},
                        row_index=row_index,
                        suggestion=f"Check {car_id} - values may be swapped",
                    )
                )

        # Quarter mile time should be greater than 0-60
        quarter_mile = self._get_float(record, "quarter_mile_sec")

        if zero_60 is not None and quarter_mile is not None:
            if quarter_mile <= zero_60:
                car_id = self._get_car_id(record)
                issues.append(
                    ValidationIssue(
                        severity=Severity.ERROR,
                        field="quarter_mile_sec",
                        message=f"Quarter mile ({quarter_mile}s) should be greater than 0-60 ({zero_60}s)",
                        value={"quarter_mile": quarter_mile, "0-60": zero_60},
                        row_index=row_index,
                        suggestion=f"Check {car_id} - values seem incorrect",
                    )
                )

            # Check for implausible 0-60 / quarter mile correlation
            # Sub-2 second 0-60 requires sub-10 second quarter mile (hypercars only)
            # Sub-3 second 0-60 requires sub-11 second quarter mile
            # Slow quarter mile (>15s) should not have fast 0-60 (<5s)
            if zero_60 < 2.0 and quarter_mile > 10.0:
                car_id = self._get_car_id(record)
                issues.append(
                    ValidationIssue(
                        severity=Severity.ERROR,
                        field="0_60_mph_sec",
                        message=f"Implausible 0-60 ({zero_60}s) for quarter mile ({quarter_mile}s) - sub-2s 0-60 requires sub-10s quarter mile",
                        value={"0-60": zero_60, "quarter_mile": quarter_mile},
                        row_index=row_index,
                        suggestion=f"Check {car_id} - 0-60 time likely parsed incorrectly",
                    )
                )
            elif zero_60 < 4.0 and quarter_mile > 14.0:
                car_id = self._get_car_id(record)
                issues.append(
                    ValidationIssue(
                        severity=Severity.ERROR,
                        field="0_60_mph_sec",
                        message=f"Implausible 0-60 ({zero_60}s) for quarter mile ({quarter_mile}s) - values don't correlate",
                        value={"0-60": zero_60, "quarter_mile": quarter_mile},
                        row_index=row_index,
                        suggestion=f"Check {car_id} - 0-60 time likely parsed incorrectly",
                    )
                )

        return issues

    def _find_duplicates(
        self, data: list[dict[str, Any]]
    ) -> list[ValidationIssue]:
        """Find duplicate records based on key fields.

        Two rows sharing a (year, manufacturer, model) key are the same car
        shipped twice under different car_ids -- a data-quality defect, not a
        stylistic nit, so this is ERROR severity: it fails `etl.cli validate`
        and is counted in the quality report, the same way a range violation
        is. The manufacturer is resolved through ManufacturerNormalizer
        first, so "Lucid" and "Lucid Motors" are caught as the same key
        rather than silently compared as different manufacturers.
        """
        issues = []
        seen: dict[tuple, list[int]] = {}

        for row_index, record in enumerate(data, start=1):
            # Create key from year, manufacturer, model
            key = (
                record.get("year", ""),
                self.normalizer.normalize(record.get("manufacturer", "")).lower(),
                record.get("model", "").lower(),
            )

            if key in seen:
                seen[key].append(row_index)
            else:
                seen[key] = [row_index]

        # Report duplicates
        for key, row_indices in seen.items():
            if len(row_indices) > 1:
                year, manufacturer, model = key
                car_id = f"{year} {manufacturer} {model}".strip()
                issues.append(
                    ValidationIssue(
                        severity=Severity.ERROR,
                        field="duplicate",
                        message=f"Duplicate entries found for '{car_id}' at rows: {row_indices}",
                        value={"key": key, "rows": row_indices},
                    )
                )

        return issues

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
