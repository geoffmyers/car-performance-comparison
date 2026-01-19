#!/usr/bin/env python3
"""
Extract car model data from compare-model-data.json into a flat CSV file.
Each row represents a single car model trim.
"""

import json
import csv
from pathlib import Path


def main():
    script_dir = Path(__file__).parent
    input_file = script_dir / "compare-model-data.json"
    output_file = script_dir / "compare-model-data.csv"

    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    makes = data["system_settings"][0]["data"]

    rows = []
    for make in makes:
        make_id = make.get("id", "")
        make_display = make.get("display", "")
        make_internal_id = make.get("_id", "")

        for model in make.get("models", []):
            model_id = model.get("id", "")
            model_display = model.get("display", "")

            for year_data in model.get("years", []):
                year = year_data.get("display", "")
                year_id = year_data.get("id", "")
                rover_id = year_data.get("content", {}).get("rover_id", "")

                for trim in year_data.get("tested_trims", []):
                    rows.append({
                        "make_id": make_id,
                        "make_display": make_display,
                        "make_internal_id": make_internal_id,
                        "model_id": model_id,
                        "model_display": model_display,
                        "year": year,
                        "year_id": year_id,
                        "rover_id": rover_id,
                        "trim_id": trim.get("id", ""),
                        "trim_display": trim.get("display", ""),
                        "chrome_style_id": trim.get("chrome_style_id", ""),
                    })

    fieldnames = [
        "make_id",
        "make_display",
        "make_internal_id",
        "model_id",
        "model_display",
        "year",
        "year_id",
        "rover_id",
        "trim_id",
        "trim_display",
        "chrome_style_id",
    ]

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Extracted {len(rows)} trims to {output_file}")


if __name__ == "__main__":
    main()
