#!/usr/bin/env python3
"""
Fetch Car and Driver review pages, extract performance specifications,
and save to a consolidated CSV file.

Run from the caranddriver directory with the virtual environment:
    source venv/bin/activate
    python fetch-car-reviews.py
"""

import csv
import json
import logging
import os
import re
import time
import random
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

# Configuration
BASE_DELAY = 2.0  # Base delay between requests
JITTER_FACTOR = 0.5  # Random jitter
MAX_RETRIES = 3
INITIAL_BACKOFF = 5.0
HTML_DIR = "html"  # Directory to save HTML files

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("fetch-car-reviews.log"),
    ],
)
logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def add_jitter(delay: float) -> float:
    """Add random jitter to delay."""
    jitter = delay * JITTER_FACTOR * random.random()
    return delay + jitter


def fetch_page(url: str, session: requests.Session) -> str | None:
    """Fetch a page with retry logic."""
    backoff = INITIAL_BACKOFF

    for attempt in range(MAX_RETRIES):
        try:
            response = session.get(url, headers=HEADERS, timeout=30)

            if response.status_code == 200:
                return response.text
            elif response.status_code == 429:
                wait_time = max(int(response.headers.get("Retry-After", backoff)), backoff)
                logger.warning(f"Rate limited. Waiting {wait_time}s (attempt {attempt + 1})")
                time.sleep(add_jitter(wait_time))
                backoff *= 2
            else:
                logger.error(f"HTTP {response.status_code} for {url}")
                return None

        except requests.exceptions.Timeout:
            logger.warning(f"Timeout (attempt {attempt + 1})")
            time.sleep(add_jitter(backoff))
            backoff *= 2
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            time.sleep(add_jitter(backoff))
            backoff *= 2

    return None


def extract_year_make_model_from_url(url: str) -> dict:
    """Extract year, make, model from URL path."""
    path = urlparse(url).path
    # Pattern: /reviews/a12345/2025-bmw-m5-test/
    match = re.search(r"/(\d{4})-([a-z]+(?:-[a-z]+)?)-(.+?)(?:-test|-drive|-review|-by-the-numbers)?/?$", path, re.I)
    if match:
        return {
            "year": match.group(1),
            "make": match.group(2).replace("-", " ").title(),
            "model": match.group(3).replace("-", " ").title(),
        }
    return {"year": "", "make": "", "model": ""}


def parse_value(text: str, pattern: str) -> str:
    """Extract a value using regex pattern."""
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else ""


def parse_specs_panel(soup: BeautifulSoup, url: str) -> dict:
    """Parse the specs panel and extract all performance data."""
    data = {
        "url": url,
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

    # Extract year/make/model from URL as fallback
    url_info = extract_year_make_model_from_url(url)
    data.update(url_info)

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
        logger.warning(f"No specs panel found for {url}")
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


def url_to_filename(url: str) -> str:
    """Convert URL to a safe filename."""
    path = urlparse(url).path
    # Remove leading/trailing slashes and replace remaining with dashes
    name = path.strip("/").replace("/", "-")
    return f"{name}.html"


def main():
    script_dir = Path(__file__).parent
    urls_file = script_dir / "car-review-urls.txt"
    output_csv = script_dir / "car-review-specs.csv"
    html_dir = script_dir / HTML_DIR

    # Create HTML directory
    html_dir.mkdir(exist_ok=True)

    # Load URLs
    with open(urls_file, "r") as f:
        urls = [line.strip() for line in f if line.strip() and line.strip().startswith("http")]

    logger.info(f"Found {len(urls)} URLs to process")

    # Create session
    session = requests.Session()

    # Process URLs
    results = []
    for i, url in enumerate(urls, 1):
        logger.info(f"Processing {i}/{len(urls)}: {url}")

        html_file = html_dir / url_to_filename(url)

        # Check if HTML already exists
        if html_file.exists():
            logger.info(f"  Using cached HTML: {html_file.name}")
            html = html_file.read_text(encoding="utf-8")
        else:
            html = fetch_page(url, session)
            if html:
                html_file.write_text(html, encoding="utf-8")
                logger.info(f"  Saved HTML: {html_file.name}")
            else:
                logger.error(f"  Failed to fetch: {url}")
                continue

            # Delay between requests (only for new fetches)
            if i < len(urls):
                delay = add_jitter(BASE_DELAY)
                time.sleep(delay)

        # Parse specs
        soup = BeautifulSoup(html, "html.parser")
        specs = parse_specs_panel(soup, url)
        results.append(specs)

        # Log extracted data
        if specs.get("zero_to_60_mph"):
            logger.info(f"  Found 0-60: {specs['zero_to_60_mph']} sec")
        if specs.get("quarter_mile_time"):
            logger.info(f"  Found 1/4 mile: {specs['quarter_mile_time']} sec @ {specs.get('quarter_mile_speed', 'N/A')} mph")

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
