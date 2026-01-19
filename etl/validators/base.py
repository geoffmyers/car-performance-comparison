#!/usr/bin/env python3
"""
Base validator classes for the ETL pipeline.

This module provides:
- Base abstract validator class
- ValidationResult and ValidationIssue dataclasses
- Severity enum for issue classification
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Severity(Enum):
    """Severity level for validation issues."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ValidationIssue:
    """A single validation issue."""

    severity: Severity
    field: str
    message: str
    value: Any = None
    row_index: int | None = None
    suggestion: str | None = None

    def __str__(self) -> str:
        parts = [f"[{self.severity.value.upper()}]"]
        if self.row_index is not None:
            parts.append(f"Row {self.row_index}:")
        parts.append(f"{self.field}: {self.message}")
        if self.value is not None:
            parts.append(f"(value: {self.value})")
        if self.suggestion:
            parts.append(f"Suggestion: {self.suggestion}")
        return " ".join(parts)


@dataclass
class ValidationResult:
    """Result of running validation on data."""

    issues: list[ValidationIssue] = field(default_factory=list)
    records_validated: int = 0
    validator_name: str = ""

    @property
    def is_valid(self) -> bool:
        """Check if validation passed (no errors)."""
        return not any(i.severity == Severity.ERROR for i in self.issues)

    @property
    def error_count(self) -> int:
        """Count of error-level issues."""
        return sum(1 for i in self.issues if i.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        """Count of warning-level issues."""
        return sum(1 for i in self.issues if i.severity == Severity.WARNING)

    @property
    def info_count(self) -> int:
        """Count of info-level issues."""
        return sum(1 for i in self.issues if i.severity == Severity.INFO)

    def add_error(
        self,
        field: str,
        message: str,
        value: Any = None,
        row_index: int | None = None,
        suggestion: str | None = None,
    ) -> None:
        """Add an error-level issue."""
        self.issues.append(
            ValidationIssue(
                severity=Severity.ERROR,
                field=field,
                message=message,
                value=value,
                row_index=row_index,
                suggestion=suggestion,
            )
        )

    def add_warning(
        self,
        field: str,
        message: str,
        value: Any = None,
        row_index: int | None = None,
        suggestion: str | None = None,
    ) -> None:
        """Add a warning-level issue."""
        self.issues.append(
            ValidationIssue(
                severity=Severity.WARNING,
                field=field,
                message=message,
                value=value,
                row_index=row_index,
                suggestion=suggestion,
            )
        )

    def add_info(
        self,
        field: str,
        message: str,
        value: Any = None,
        row_index: int | None = None,
    ) -> None:
        """Add an info-level issue."""
        self.issues.append(
            ValidationIssue(
                severity=Severity.INFO,
                field=field,
                message=message,
                value=value,
                row_index=row_index,
            )
        )

    def merge(self, other: "ValidationResult") -> None:
        """Merge another validation result into this one."""
        self.issues.extend(other.issues)
        self.records_validated += other.records_validated

    def get_issues_by_field(self, field: str) -> list[ValidationIssue]:
        """Get all issues for a specific field."""
        return [i for i in self.issues if i.field == field]

    def get_issues_by_severity(self, severity: Severity) -> list[ValidationIssue]:
        """Get all issues of a specific severity."""
        return [i for i in self.issues if i.severity == severity]


class BaseValidator(ABC):
    """Abstract base class for validators."""

    def __init__(self, name: str = ""):
        """Initialize the validator.

        Args:
            name: Name of the validator for reporting
        """
        self.name = name or self.__class__.__name__

    @abstractmethod
    def validate(self, data: list[dict[str, Any]]) -> ValidationResult:
        """Validate a list of records.

        Args:
            data: List of car data dictionaries

        Returns:
            ValidationResult with any issues found
        """
        pass

    def validate_record(
        self, record: dict[str, Any], row_index: int
    ) -> list[ValidationIssue]:
        """Validate a single record.

        Override this for record-by-record validation.

        Args:
            record: Single car data dictionary
            row_index: Row index for error reporting

        Returns:
            List of validation issues
        """
        return []
