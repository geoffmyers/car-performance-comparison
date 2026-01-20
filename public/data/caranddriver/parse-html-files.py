#!/usr/bin/env python3
"""
Parse cached HTML files and extract specs to CSV.
This script processes already-downloaded HTML files without making network requests.
"""

import csv
import logging
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def extract_year_make_model_from_filename(filename: str) -> dict:
    """Extract year, make, model from filename."""
    # Pattern: reviews-a12345-2025-bmw-m5-test-review.html
    match = re.search(r"-(\d{4})-([a-z]+(?:-[a-z]+)?)-(.+?)\.html$", filename, re.I)
    if match:
        return {
            "year": match.group(1),
            "make": match.group(2).replace("-", " ").title(),
            "model": match.group(3).replace("-", " ").title(),
        }
    return {"year": "", "make": "", "model": ""}


def parse_specs_panel(soup: BeautifulSoup, filename: str) -> dict:
    """Parse the specs panel and extract all performance data."""
    data = {
        "url": "",
        "year": "",
        "make": "",
        "model": "",
        "vehicle_type": "",
        "base_price": "",
        "as_tested_price": "",
        "engine_type": "",
        "displacement": "",
        "power_hp": "",
        "power_rpm": "",
        "torque_lb_ft": "",
        "torque_rpm": "",
        "transmission": "",
        "wheelbase": "",
        "length": "",
        "width": "",
        "height": "",
        "curb_weight": "",
        "zero_to_60_mph": "",
        "zero_to_100_mph": "",
        "quarter_mile_time": "",
        "quarter_mile_speed": "",
        "top_speed": "",
        "braking_70_0": "",
        "braking_100_0": "",
        "skidpad_g": "",
        "rolling_start_5_60": "",
        "top_gear_30_50": "",
        "top_gear_50_70": "",
        "fuel_economy_combined": "",
        "fuel_economy_city": "",
        "fuel_economy_highway": "",
        "fuel_economy_observed": "",
        "ev_range": "",
        "is_estimated": "",
    }

    # Extract year/make/model from filename as fallback
    file_info = extract_year_make_model_from_filename(filename)
    data.update(file_info)

    # Try to get title for better year/make/model
    title = soup.find("title")
    if title:
        title_text = title.get_text()
        # Pattern: "2025 BMW M5 Review, Pricing, and Specs"
        match = re.match(r"(\d{4})\s+(.+?)\s+Review", title_text)
        if match:
            data["year"] = match.group(1)
            name_parts = match.group(2).split()
            if len(name_parts) >= 2:
                data["make"] = name_parts[0]
                data["model"] = " ".join(name_parts[1:])

    specs_panel = soup.find("div", attrs={"data-embed": "specs-panel"})
    if not specs_panel:
        return data

    text = specs_panel.get_text(separator="\n", strip=True)

    # Check if estimated
    if "EST" in text or "est" in text.lower() or "claim" in text.lower():
        data["is_estimated"] = "yes"

    # Vehicle type
    match = re.search(r"(?:VEHICLE TYPE|Vehicle Type)[:\s]*([^\n]+)", text, re.I)
    if match:
        data["vehicle_type"] = match.group(1).strip()

    # Price
    match = re.search(r"(?:BASE PRICE|Base)[:\s]*\$?([\d,]+)", text, re.I)
    if match:
        data["base_price"] = match.group(1).replace(",", "")
    match = re.search(r"As Tested[:\s]*\$?([\d,]+)", text, re.I)
    if match:
        data["as_tested_price"] = match.group(1).replace(",", "")

    # Engine
    match = re.search(r"(?:ENGINE TYPE|POWERTRAIN)[:\s]*([^\n]+)", text, re.I)
    if match:
        data["engine_type"] = match.group(1).strip()

    # Displacement
    match = re.search(r"Displacement[:\s]*([\d.]+)\s*(?:cu in|L|cc)", text, re.I)
    if match:
        data["displacement"] = match.group(1)

    # Power
    match = re.search(r"(?:Power|combined output)[:\s]*([\d,]+)\s*hp(?:\s*@\s*([\d,]+)\s*rpm)?", text, re.I)
    if match:
        data["power_hp"] = match.group(1).replace(",", "")
        if match.group(2):
            data["power_rpm"] = match.group(2).replace(",", "")

    # Torque
    match = re.search(r"Torque[:\s]*([\d,]+)\s*lb-ft(?:\s*@\s*([\d,]+)\s*rpm)?", text, re.I)
    if match:
        data["torque_lb_ft"] = match.group(1).replace(",", "")
        if match.group(2):
            data["torque_rpm"] = match.group(2).replace(",", "")

    # Transmission
    match = re.search(r"(?:TRANSMISSION|Transmission)[:\s]*([^\n]+)", text, re.I)
    if match:
        data["transmission"] = match.group(1).strip()

    # Dimensions
    match = re.search(r"Wheelbase[:\s]*([\d.]+)\s*in", text, re.I)
    if match:
        data["wheelbase"] = match.group(1)
    match = re.search(r"Length[:\s]*([\d.]+)\s*in", text, re.I)
    if match:
        data["length"] = match.group(1)
    match = re.search(r"Width[:\s]*([\d.]+)\s*in", text, re.I)
    if match:
        data["width"] = match.group(1)
    match = re.search(r"Height[:\s]*([\d.]+)\s*in", text, re.I)
    if match:
        data["height"] = match.group(1)
    # Curb weight (handles ranges like "4200-4300 lb")
    match = re.search(r"Curb [Ww]eight[^\d]*([\d,]+)(?:[–-][\d,]+)?\s*lb", text, re.I)
    if match:
        data["curb_weight"] = match.group(1).replace(",", "")

    # Performance - 0-60 (handles ranges like "4.4-5.8 sec", captures first value)
    match = re.search(r"(?:Zero to 60 mph|60 mph)[:\s]*([\d.]+)(?:[–-][\d.]+)?\s*sec", text, re.I)
    if match:
        data["zero_to_60_mph"] = match.group(1)

    # Performance - 0-100 (handles ranges)
    match = re.search(r"(?:Zero to 100 mph|100 mph)[:\s]*([\d.]+)(?:[–-][\d.]+)?\s*sec", text, re.I)
    if match:
        data["zero_to_100_mph"] = match.group(1)

    # Quarter mile (handles ranges)
    match = re.search(r"(?:Standing ¼-mile|1/4-Mile|¼-mile)[:\s]*([\d.]+)(?:[–-][\d.]+)?\s*sec(?:\s*@\s*([\d]+)(?:[–-][\d]+)?\s*mph)?", text, re.I)
    if match:
        data["quarter_mile_time"] = match.group(1)
        if match.group(2):
            data["quarter_mile_speed"] = match.group(2)

    # Top speed (already handles ranges with \d\-]+)
    match = re.search(r"Top [Ss]peed[:\s]*([\d]+)(?:[–-][\d]+)?\s*mph", text, re.I)
    if match:
        data["top_speed"] = match.group(1)

    # Braking
    match = re.search(r"(?:Braking,?\s*)?70[–-]0\s*mph[:\s]*([\d]+)\s*ft", text, re.I)
    if match:
        data["braking_70_0"] = match.group(1)
    match = re.search(r"(?:Braking,?\s*)?100[–-]0\s*mph[:\s]*([\d]+)\s*ft", text, re.I)
    if match:
        data["braking_100_0"] = match.group(1)

    # Skidpad
    match = re.search(r"(?:Roadholding|Skidpad)[^\d]*([\d.]+)\s*g", text, re.I)
    if match:
        data["skidpad_g"] = match.group(1)

    # Rolling start
    match = re.search(r"Rolling Start,?\s*5[–-]60\s*mph[:\s]*([\d.]+)\s*sec", text, re.I)
    if match:
        data["rolling_start_5_60"] = match.group(1)

    # Top gear
    match = re.search(r"Top Gear,?\s*30[–-]50\s*mph[:\s]*([\d.]+)\s*sec", text, re.I)
    if match:
        data["top_gear_30_50"] = match.group(1)
    match = re.search(r"Top Gear,?\s*50[–-]70\s*mph[:\s]*([\d.]+)\s*sec", text, re.I)
    if match:
        data["top_gear_50_70"] = match.group(1)

    # Fuel economy
    match = re.search(r"Combined/[Cc]ity/[Hh]ighway[:\s]*([\d]+)/([\d]+)/([\d]+)", text, re.I)
    if match:
        data["fuel_economy_combined"] = match.group(1)
        data["fuel_economy_city"] = match.group(2)
        data["fuel_economy_highway"] = match.group(3)

    match = re.search(r"Observed[:\s]*([\d]+)\s*mpg", text, re.I)
    if match:
        data["fuel_economy_observed"] = match.group(1)

    # EV Range
    match = re.search(r"EV Range[:\s]*([\d]+)\s*mi", text, re.I)
    if match:
        data["ev_range"] = match.group(1)

    return data


def main():
    script_dir = Path(__file__).parent
    html_dir = script_dir / "html"
    output_csv = script_dir / "car-review-specs.csv"

    # Get limit from command line args
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None

    # Get all HTML files
    html_files = sorted(html_dir.glob("*.html"))
    if limit:
        html_files = html_files[:limit]

    logger.info(f"Processing {len(html_files)} HTML files")

    results = []
    for i, html_file in enumerate(html_files, 1):
        if i % 100 == 0:
            logger.info(f"Processed {i}/{len(html_files)} files")

        try:
            html = html_file.read_text(encoding="utf-8")
            soup = BeautifulSoup(html, "html.parser")
            specs = parse_specs_panel(soup, html_file.name)
            results.append(specs)
        except Exception as e:
            logger.error(f"Error processing {html_file.name}: {e}")

    # Write CSV
    if results:
        fieldnames = list(results[0].keys())
        with open(output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

        logger.info(f"\nWrote {len(results)} records to {output_csv}")

        # Summary stats
        with_perf = sum(1 for r in results if r.get("zero_to_60_mph"))
        logger.info(f"Records with 0-60 times: {with_perf}/{len(results)}")
    else:
        logger.error("No results to write")


if __name__ == "__main__":
    main()
