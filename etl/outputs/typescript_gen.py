#!/usr/bin/env python3
"""
TypeScript type generator from schema.

This module provides:
- Generating CarData interface from schema
- Generating ColumnConfig array from schema
- Generating country name mapping
"""

from pathlib import Path
from typing import Any

from etl.core.schema import Schema
from etl.core.manufacturers import ManufacturerNormalizer


class TypeScriptGenerator:
    """Generates TypeScript types from schema configuration."""

    def __init__(self, schema: Schema, normalizer: ManufacturerNormalizer):
        """Initialize the generator.

        Args:
            schema: Schema instance
            normalizer: ManufacturerNormalizer for country mappings
        """
        self.schema = schema
        self.normalizer = normalizer

    def generate(self, output_path: Path) -> None:
        """Generate TypeScript types file.

        Args:
            output_path: Path to output TypeScript file
        """
        content = self._generate_content()

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

    def _generate_content(self) -> str:
        """Generate the full TypeScript file content."""
        parts = [
            self._generate_car_data_interface(),
            "",
            self._generate_column_config_interface(),
            "",
            self._generate_column_configs(),
            "",
            self._generate_categories(),
            "",
            self._generate_country_names(),
        ]

        return "\n".join(parts)

    def _generate_car_data_interface(self) -> str:
        """Generate CarData interface."""
        lines = ["export interface CarData {"]

        for col in self.schema.column_order:
            # TypeScript field name (quote if it starts with number or has special chars)
            if col[0].isdigit() or "-" in col:
                field_name = f'"{col}"'
            else:
                field_name = col

            lines.append(f"  {field_name}: string;")

        lines.append("}")

        return "\n".join(lines)

    def _generate_column_config_interface(self) -> str:
        """Generate ColumnConfig interface."""
        return """export interface ColumnConfig {
  id: keyof CarData;
  header: string;
  category: string;
  unit?: string;
  isNumeric?: boolean;
}"""

    def _generate_column_configs(self) -> str:
        """Generate columnConfigs array."""
        lines = ["export const columnConfigs: ColumnConfig[] = ["]

        # Get default visible columns for ordering
        default_visible = set(self.schema.default_visible_columns)

        # Add visible columns first (in default order)
        lines.append("  // Default visible columns in order")
        for col in self.schema.default_visible_columns:
            config_line = self._column_config_line(col)
            if config_line:
                lines.append(f"  {config_line}")

        # Add hidden columns
        lines.append("  // Hidden by default")
        for col in self.schema.column_order:
            if col not in default_visible:
                config_line = self._column_config_line(col)
                if config_line:
                    lines.append(f"  {config_line}")

        lines.append("];")

        return "\n".join(lines)

    def _column_config_line(self, col: str) -> str:
        """Generate a single column config entry."""
        field = self.schema.get_field(col)
        if field is None:
            return ""

        # Build the config object
        parts = []

        # id (quote if necessary)
        if col[0].isdigit() or "-" in col:
            parts.append(f'id: "{col}"')
        else:
            parts.append(f'id: "{col}"')

        # header
        header = field.get("header", col)
        parts.append(f'header: "{header}"')

        # category
        category = field.get("category", "General")
        parts.append(f'category: "{category}"')

        # unit (optional)
        unit = field.get("unit")
        if unit:
            # Map unit names to display format
            unit_display = self._format_unit(unit)
            parts.append(f'unit: "{unit_display}"')

        # isNumeric (optional)
        if field.get("is_numeric") or field.get("type") == "numeric":
            parts.append("isNumeric: true")

        return "{ " + ", ".join(parts) + " },"

    def _format_unit(self, unit: str) -> str:
        """Format unit for display."""
        unit_map = {
            "seconds": "sec",
            "mph": "mph",
            "km/h": "km/h",
            "hp": "hp",
            "kW": "kW",
            "lb-ft": "lb-ft",
            "ft": "ft",
            "g": "g",
            "lb": "lb",
        }
        return unit_map.get(unit, unit)

    def _generate_categories(self) -> str:
        """Generate category array."""
        categories = self.schema.categories
        cats_str = ", ".join(f'"{c}"' for c in categories)
        return f"export const columnCategories = [{cats_str}] as const;"

    def _generate_country_names(self) -> str:
        """Generate country name mapping."""
        lines = [
            "// Country code to name mapping",
            "export const countryNames: Record<string, string> = {",
        ]

        # Get country names from normalizer config
        country_names = self.normalizer.country_names

        # Sort by country code for consistency
        for code in sorted(country_names.keys()):
            name = country_names[code]
            lines.append(f'  {code}: "{name}",')

        lines.append("};")

        return "\n".join(lines)


def generate_types(
    schema_path: Path | None = None,
    output_path: Path | None = None,
) -> None:
    """Convenience function to generate TypeScript types.

    Args:
        schema_path: Path to schema.yaml (defaults to config location)
        output_path: Path for output (defaults to src/types/car.ts)
    """
    schema = Schema(schema_path)
    normalizer = ManufacturerNormalizer()

    if output_path is None:
        output_path = (
            Path(__file__).parent.parent.parent / "src" / "types" / "car.ts"
        )

    generator = TypeScriptGenerator(schema, normalizer)
    generator.generate(output_path)
