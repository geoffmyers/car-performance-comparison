#!/usr/bin/env python3
"""
SQLite output writer for car performance data.

This module provides:
- Writing merged car data to SQLite database
- Schema-enforced table structure with CHECK constraints
- Indexes for efficient querying
- FTS5 full-text search support
"""

import sqlite3
from pathlib import Path
from typing import Any

from etl.core.schema import Schema


class SQLiteWriter:
    """Writes car performance data to SQLite database."""

    TABLE_NAME = "cars"
    FTS_TABLE_NAME = "cars_fts"

    def __init__(self, schema: Schema):
        """Initialize the SQLite writer.

        Args:
            schema: Schema instance for column definitions
        """
        self.schema = schema

    def write(
        self,
        data: list[dict[str, Any]],
        output_path: Path,
    ) -> int:
        """Write car data to SQLite database.

        Creates a new database, dropping any existing one.

        Args:
            data: List of car data dictionaries
            output_path: Path to output SQLite database file

        Returns:
            Number of records written
        """
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Remove existing database
        if output_path.exists():
            output_path.unlink()

        conn = sqlite3.connect(output_path)
        try:
            self._create_schema(conn)
            count = self._insert_data(conn, data)
            self._create_indexes(conn)
            self._create_fts_table(conn)
            conn.commit()
            return count
        finally:
            conn.close()

    def _get_column_type(self, field_name: str) -> str:
        """Get SQLite column type for a field.

        Args:
            field_name: Name of the field

        Returns:
            SQLite type (TEXT, REAL, INTEGER)
        """
        field = self.schema.get_field(field_name)
        if not field:
            return "TEXT"

        field_type = field.get("type", "string")
        if field_type == "numeric":
            # Use REAL for all numeric types to handle decimals
            return "REAL"
        return "TEXT"

    def _get_check_constraint(self, field_name: str) -> str | None:
        """Get CHECK constraint for a numeric field.

        Args:
            field_name: Name of the field

        Returns:
            CHECK constraint SQL or None
        """
        field = self.schema.get_field(field_name)
        if not field:
            return None

        if field.get("type") != "numeric":
            return None

        constraints = []
        min_val = field.get("min")
        max_val = field.get("max")

        if min_val is not None:
            constraints.append(f'"{field_name}" >= {min_val}')
        if max_val is not None:
            constraints.append(f'"{field_name}" <= {max_val}')

        if constraints:
            return f"CHECK({' AND '.join(constraints)})"
        return None

    def _create_schema(self, conn: sqlite3.Connection) -> None:
        """Create the cars table with schema-defined columns.

        Uses car_id (hash) as the PRIMARY KEY for uniqueness enforcement.

        Args:
            conn: SQLite connection
        """
        columns_sql = []

        for field_name in self.schema.column_order:
            col_type = self._get_column_type(field_name)
            check = self._get_check_constraint(field_name)

            # Build column definition
            col_def = f'"{field_name}" {col_type}'

            # car_id is the primary key
            field = self.schema.get_field(field_name)
            if field and field.get("primary_key"):
                col_def += " PRIMARY KEY"
            # Add NOT NULL for required fields (but not car_id, already has PRIMARY KEY)
            elif field and field.get("required"):
                col_def += " NOT NULL"

            if check:
                col_def += f" {check}"

            columns_sql.append(col_def)

        # Create table
        create_sql = f"""
            CREATE TABLE {self.TABLE_NAME} (
                {','.join(columns_sql)}
            )
        """
        conn.execute(create_sql)

    def _insert_data(
        self, conn: sqlite3.Connection, data: list[dict[str, Any]]
    ) -> int:
        """Insert car data into the database.

        Args:
            conn: SQLite connection
            data: List of car data dictionaries

        Returns:
            Number of records inserted
        """
        columns = self.schema.column_order
        placeholders = ", ".join(["?" for _ in columns])
        quoted_columns = ", ".join([f'"{col}"' for col in columns])

        insert_sql = f"""
            INSERT INTO {self.TABLE_NAME} ({quoted_columns})
            VALUES ({placeholders})
        """

        cursor = conn.cursor()
        count = 0

        for record in data:
            values = []
            for col in columns:
                value = record.get(col)
                # Convert empty strings to None for numeric fields
                if value == "":
                    value = None
                elif value is not None:
                    field = self.schema.get_field(col)
                    if field and field.get("type") == "numeric":
                        try:
                            value = float(value) if value else None
                        except (ValueError, TypeError):
                            value = None
                values.append(value)

            try:
                cursor.execute(insert_sql, values)
                count += 1
            except sqlite3.IntegrityError as e:
                # Log constraint violations but continue
                manufacturer = record.get("manufacturer", "Unknown")
                model = record.get("model", "Unknown")
                print(f"Warning: Skipping record {manufacturer} {model}: {e}")

        return count

    def _create_indexes(self, conn: sqlite3.Connection) -> None:
        """Create indexes for efficient querying.

        Args:
            conn: SQLite connection
        """
        indexes = [
            ("idx_manufacturer", "manufacturer"),
            ("idx_country", "country"),
            ("idx_year", "year"),
            ("idx_manufacturer_model", "manufacturer, model"),
        ]

        for index_name, columns in indexes:
            conn.execute(
                f'CREATE INDEX {index_name} ON {self.TABLE_NAME} ({columns})'
            )

    def _create_fts_table(self, conn: sqlite3.Connection) -> None:
        """Create FTS5 virtual table for full-text search.

        Note: Since car_id is a TEXT primary key (not INTEGER), we use
        an external content table approach without content_rowid.

        Args:
            conn: SQLite connection
        """
        # Create FTS5 virtual table (external content without rowid mapping)
        conn.execute(f"""
            CREATE VIRTUAL TABLE {self.FTS_TABLE_NAME} USING fts5(
                car_id,
                manufacturer,
                model
            )
        """)

        # Populate FTS table from cars table
        conn.execute(f"""
            INSERT INTO {self.FTS_TABLE_NAME} (car_id, manufacturer, model)
            SELECT car_id, manufacturer, model FROM {self.TABLE_NAME}
        """)

    def validate_output(self, output_path: Path) -> tuple[bool, list[str]]:
        """Validate a written SQLite database.

        Args:
            output_path: Path to SQLite database to validate

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        if not output_path.exists():
            return False, ["Database file does not exist"]

        try:
            conn = sqlite3.connect(output_path)
            cursor = conn.cursor()

            # Check table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (self.TABLE_NAME,)
            )
            if not cursor.fetchone():
                errors.append(f"Table '{self.TABLE_NAME}' does not exist")
                return False, errors

            # Check columns
            cursor.execute(f"PRAGMA table_info({self.TABLE_NAME})")
            db_columns = {row[1] for row in cursor.fetchall()}
            expected = set(self.schema.column_order)

            missing = expected - db_columns
            if missing:
                errors.append(f"Missing columns: {', '.join(sorted(missing))}")

            # Check FTS table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (self.FTS_TABLE_NAME,)
            )
            if not cursor.fetchone():
                errors.append(f"FTS table '{self.FTS_TABLE_NAME}' does not exist")

            # Check indexes
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name=?",
                (self.TABLE_NAME,)
            )
            indexes = {row[0] for row in cursor.fetchall()}
            expected_indexes = {
                "idx_manufacturer", "idx_country", "idx_year", "idx_manufacturer_model"
            }
            missing_indexes = expected_indexes - indexes
            if missing_indexes:
                errors.append(f"Missing indexes: {', '.join(sorted(missing_indexes))}")

            # Check record count
            cursor.execute(f"SELECT COUNT(*) FROM {self.TABLE_NAME}")
            count = cursor.fetchone()[0]
            if count == 0:
                errors.append("No records in database")

            conn.close()

        except Exception as e:
            errors.append(f"Error reading database: {str(e)}")

        return len(errors) == 0, errors

    def get_record_count(self, output_path: Path) -> int:
        """Get the number of records in the database.

        Args:
            output_path: Path to SQLite database

        Returns:
            Number of records, or 0 if database doesn't exist
        """
        if not output_path.exists():
            return 0

        try:
            conn = sqlite3.connect(output_path)
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {self.TABLE_NAME}")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception:
            return 0
