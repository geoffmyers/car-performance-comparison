#!/usr/bin/env python3
"""
Quality report generator for car performance data.

This module provides:
- Completeness statistics per field
- Source distribution analysis
- Manufacturer distribution
- Validation summary
"""

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from etl.core.schema import Schema
from etl.validators.base import ValidationResult, Severity


@dataclass
class FieldStats:
    """Statistics for a single field."""

    name: str
    total_records: int = 0
    filled_count: int = 0
    empty_count: int = 0
    unique_values: int = 0

    @property
    def fill_rate(self) -> float:
        """Percentage of records with this field filled."""
        if self.total_records == 0:
            return 0.0
        return (self.filled_count / self.total_records) * 100


@dataclass
class QualityReport:
    """Complete quality report for a dataset."""

    generated_at: str = ""
    total_records: int = 0
    field_stats: dict[str, FieldStats] = field(default_factory=dict)
    source_distribution: dict[str, int] = field(default_factory=dict)
    manufacturer_distribution: dict[str, int] = field(default_factory=dict)
    country_distribution: dict[str, int] = field(default_factory=dict)
    year_range: tuple[str, str] = ("", "")
    validation_results: list[ValidationResult] = field(default_factory=list)

    @property
    def total_errors(self) -> int:
        """Total validation errors across all validators."""
        return sum(r.error_count for r in self.validation_results)

    @property
    def total_warnings(self) -> int:
        """Total validation warnings across all validators."""
        return sum(r.warning_count for r in self.validation_results)


class QualityReportGenerator:
    """Generates quality reports for car performance data."""

    def __init__(self, schema: Schema):
        """Initialize the generator.

        Args:
            schema: Schema instance for field metadata
        """
        self.schema = schema

    def generate(
        self,
        data: list[dict[str, Any]],
        validation_results: list[ValidationResult] | None = None,
    ) -> QualityReport:
        """Generate a quality report for the data.

        Args:
            data: List of car data dictionaries
            validation_results: Optional validation results to include

        Returns:
            QualityReport with statistics and analysis
        """
        report = QualityReport(
            generated_at=datetime.now().isoformat(),
            total_records=len(data),
            validation_results=validation_results or [],
        )

        # Calculate field statistics
        report.field_stats = self._calculate_field_stats(data)

        # Calculate distributions
        report.source_distribution = self._calculate_source_distribution(data)
        report.manufacturer_distribution = self._calculate_manufacturer_distribution(data)
        report.country_distribution = self._calculate_country_distribution(data)

        # Get year range
        report.year_range = self._calculate_year_range(data)

        return report

    def _calculate_field_stats(
        self, data: list[dict[str, Any]]
    ) -> dict[str, FieldStats]:
        """Calculate statistics for each field."""
        stats = {}

        for field_name in self.schema.column_order:
            field_stats = FieldStats(
                name=field_name,
                total_records=len(data),
            )

            values = []
            for record in data:
                value = record.get(field_name)
                if value is not None and value != "":
                    field_stats.filled_count += 1
                    values.append(str(value))
                else:
                    field_stats.empty_count += 1

            field_stats.unique_values = len(set(values))
            stats[field_name] = field_stats

        return stats

    def _calculate_source_distribution(
        self, data: list[dict[str, Any]]
    ) -> dict[str, int]:
        """Calculate distribution of records by source."""
        source_counter: Counter[str] = Counter()

        for record in data:
            sources = record.get("sources", "")
            if sources:
                for source in sources.split(","):
                    source = source.strip()
                    if source:
                        source_counter[source] += 1

        return dict(source_counter.most_common())

    def _calculate_manufacturer_distribution(
        self, data: list[dict[str, Any]]
    ) -> dict[str, int]:
        """Calculate distribution of records by manufacturer."""
        counter: Counter[str] = Counter()

        for record in data:
            manufacturer = record.get("manufacturer", "Unknown")
            counter[manufacturer] += 1

        return dict(counter.most_common())

    def _calculate_country_distribution(
        self, data: list[dict[str, Any]]
    ) -> dict[str, int]:
        """Calculate distribution of records by country."""
        counter: Counter[str] = Counter()

        for record in data:
            country = record.get("country", "Unknown")
            counter[country] += 1

        return dict(counter.most_common())

    def _calculate_year_range(
        self, data: list[dict[str, Any]]
    ) -> tuple[str, str]:
        """Calculate the year range in the data."""
        years = []

        for record in data:
            year = record.get("year", "")
            if year and year.isdigit():
                years.append(year)

        if not years:
            return ("", "")

        return (min(years), max(years))

    def format_text(self, report: QualityReport) -> str:
        """Format report as plain text.

        Args:
            report: QualityReport to format

        Returns:
            Formatted text report
        """
        lines = [
            "=" * 60,
            "CAR PERFORMANCE DATA QUALITY REPORT",
            "=" * 60,
            f"Generated: {report.generated_at}",
            f"Total Records: {report.total_records:,}",
            "",
        ]

        # Year range
        if report.year_range[0]:
            lines.append(f"Year Range: {report.year_range[0]} - {report.year_range[1]}")
            lines.append("")

        # Validation summary
        if report.validation_results:
            lines.extend([
                "-" * 40,
                "VALIDATION SUMMARY",
                "-" * 40,
                f"Total Errors: {report.total_errors}",
                f"Total Warnings: {report.total_warnings}",
                "",
            ])

            for result in report.validation_results:
                if result.issues:
                    lines.append(f"{result.validator_name}:")
                    lines.append(f"  Errors: {result.error_count}")
                    lines.append(f"  Warnings: {result.warning_count}")
                    lines.append("")

        # Field completeness
        lines.extend([
            "-" * 40,
            "FIELD COMPLETENESS",
            "-" * 40,
        ])

        # Group by category
        for category in self.schema.categories:
            fields = self.schema.get_fields_by_category(category)
            if not fields:
                continue

            lines.append(f"\n{category}:")
            for field_name in fields:
                if field_name in report.field_stats:
                    stats = report.field_stats[field_name]
                    bar = self._progress_bar(stats.fill_rate)
                    lines.append(
                        f"  {field_name:25s} {bar} {stats.fill_rate:5.1f}% "
                        f"({stats.filled_count:,}/{stats.total_records:,})"
                    )

        # Source distribution
        lines.extend([
            "",
            "-" * 40,
            "SOURCE DISTRIBUTION",
            "-" * 40,
        ])

        for source, count in report.source_distribution.items():
            pct = (count / report.total_records) * 100
            lines.append(f"  {source:30s} {count:6,} ({pct:5.1f}%)")

        # Top manufacturers
        lines.extend([
            "",
            "-" * 40,
            "TOP 20 MANUFACTURERS",
            "-" * 40,
        ])

        for i, (manufacturer, count) in enumerate(
            list(report.manufacturer_distribution.items())[:20]
        ):
            pct = (count / report.total_records) * 100
            lines.append(f"  {manufacturer:30s} {count:6,} ({pct:5.1f}%)")

        # Country distribution
        lines.extend([
            "",
            "-" * 40,
            "COUNTRY DISTRIBUTION",
            "-" * 40,
        ])

        for country, count in report.country_distribution.items():
            pct = (count / report.total_records) * 100
            lines.append(f"  {country:30s} {count:6,} ({pct:5.1f}%)")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)

    def format_json(self, report: QualityReport) -> str:
        """Format report as JSON.

        Args:
            report: QualityReport to format

        Returns:
            JSON string
        """
        data = {
            "generated_at": report.generated_at,
            "total_records": report.total_records,
            "year_range": {
                "min": report.year_range[0],
                "max": report.year_range[1],
            },
            "validation": {
                "total_errors": report.total_errors,
                "total_warnings": report.total_warnings,
                "validators": [
                    {
                        "name": r.validator_name,
                        "errors": r.error_count,
                        "warnings": r.warning_count,
                    }
                    for r in report.validation_results
                ],
            },
            "field_completeness": {
                name: {
                    "filled": stats.filled_count,
                    "empty": stats.empty_count,
                    "fill_rate": round(stats.fill_rate, 2),
                    "unique_values": stats.unique_values,
                }
                for name, stats in report.field_stats.items()
            },
            "source_distribution": report.source_distribution,
            "manufacturer_distribution": dict(
                list(report.manufacturer_distribution.items())[:50]
            ),
            "country_distribution": report.country_distribution,
        }

        return json.dumps(data, indent=2)

    def format_html(self, report: QualityReport) -> str:
        """Format report as HTML.

        Args:
            report: QualityReport to format

        Returns:
            HTML string
        """
        # Simple HTML template
        html_parts = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "<title>Car Performance Data Quality Report</title>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 20px; }",
            "h1 { color: #333; }",
            "h2 { color: #666; border-bottom: 1px solid #ccc; }",
            "table { border-collapse: collapse; margin: 10px 0; }",
            "th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }",
            "th { background-color: #f4f4f4; }",
            ".progress { width: 200px; background: #eee; border-radius: 4px; }",
            ".progress-bar { height: 20px; background: #4CAF50; border-radius: 4px; }",
            ".error { color: #d32f2f; }",
            ".warning { color: #f57c00; }",
            "</style>",
            "</head>",
            "<body>",
            "<h1>Car Performance Data Quality Report</h1>",
            f"<p>Generated: {report.generated_at}</p>",
            f"<p>Total Records: <strong>{report.total_records:,}</strong></p>",
        ]

        if report.year_range[0]:
            html_parts.append(
                f"<p>Year Range: {report.year_range[0]} - {report.year_range[1]}</p>"
            )

        # Validation summary
        if report.validation_results:
            html_parts.extend([
                "<h2>Validation Summary</h2>",
                f"<p class='error'>Errors: {report.total_errors}</p>",
                f"<p class='warning'>Warnings: {report.total_warnings}</p>",
            ])

        # Field completeness table
        html_parts.extend([
            "<h2>Field Completeness</h2>",
            "<table>",
            "<tr><th>Field</th><th>Category</th><th>Fill Rate</th><th>Filled</th></tr>",
        ])

        for field_name in self.schema.column_order:
            if field_name in report.field_stats:
                stats = report.field_stats[field_name]
                category = self.schema.get_field_category(field_name)
                bar_width = int(stats.fill_rate * 2)  # 200px max
                html_parts.append(
                    f"<tr>"
                    f"<td>{field_name}</td>"
                    f"<td>{category}</td>"
                    f"<td><div class='progress'><div class='progress-bar' style='width:{bar_width}px'></div></div> {stats.fill_rate:.1f}%</td>"
                    f"<td>{stats.filled_count:,}</td>"
                    f"</tr>"
                )

        html_parts.append("</table>")

        # Source distribution
        html_parts.extend([
            "<h2>Source Distribution</h2>",
            "<table>",
            "<tr><th>Source</th><th>Count</th><th>Percentage</th></tr>",
        ])

        for source, count in report.source_distribution.items():
            pct = (count / report.total_records) * 100
            html_parts.append(
                f"<tr><td>{source}</td><td>{count:,}</td><td>{pct:.1f}%</td></tr>"
            )

        html_parts.extend([
            "</table>",
            "</body>",
            "</html>",
        ])

        return "\n".join(html_parts)

    def write(
        self,
        report: QualityReport,
        output_path: Path,
        format: str = "text",
    ) -> None:
        """Write report to file.

        Args:
            report: QualityReport to write
            output_path: Path to output file
            format: Output format ("text", "json", or "html")
        """
        if format == "json":
            content = self.format_json(report)
        elif format == "html":
            content = self.format_html(report)
        else:
            content = self.format_text(report)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

    def _progress_bar(self, percentage: float, width: int = 20) -> str:
        """Create an ASCII progress bar."""
        filled = int(width * percentage / 100)
        empty = width - filled
        return f"[{'█' * filled}{'░' * empty}]"
