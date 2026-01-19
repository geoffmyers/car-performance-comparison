#!/usr/bin/env python3
"""
Crawl Car and Driver sitemap to compile a master list of all review URLs.

This script:
1. Fetches the sitemap index to find all content sitemaps
2. Downloads and parses each sitemap
3. Extracts all URLs matching /reviews/ pattern
4. Saves to car-review-urls.txt

Run from the caranddriver directory with the virtual environment:
    source venv/bin/activate
    python crawl-review-urls.py
"""

import gzip
import logging
import re
import time
import random
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET

import requests

# Configuration
BASE_DELAY = 1.0  # Delay between sitemap fetches
JITTER_FACTOR = 0.3
SITEMAP_INDEX_URL = "https://www.caranddriver.com/sitemap_index.xml"

# XML namespaces used in sitemaps
NAMESPACES = {
    "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("crawl-review-urls.log"),
    ],
)
logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
}


def add_jitter(delay: float) -> float:
    """Add random jitter to delay."""
    jitter = delay * JITTER_FACTOR * random.random()
    return delay + jitter


def fetch_url(url: str, session: requests.Session) -> bytes | None:
    """Fetch a URL and return raw content."""
    try:
        response = session.get(url, headers=HEADERS, timeout=60)
        if response.status_code == 200:
            return response.content
        else:
            logger.error(f"HTTP {response.status_code} for {url}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error for {url}: {e}")
        return None


def parse_sitemap_index(content: bytes) -> list[str]:
    """Parse sitemap index XML and return list of sitemap URLs."""
    root = ET.fromstring(content)
    sitemap_urls = []

    for sitemap in root.findall("sm:sitemap", NAMESPACES):
        loc = sitemap.find("sm:loc", NAMESPACES)
        if loc is not None and loc.text:
            sitemap_urls.append(loc.text)

    return sitemap_urls


def parse_sitemap(content: bytes, is_gzipped: bool = False) -> list[str]:
    """Parse sitemap XML and return list of page URLs."""
    if is_gzipped:
        content = gzip.decompress(content)

    root = ET.fromstring(content)
    urls = []

    for url_elem in root.findall("sm:url", NAMESPACES):
        loc = url_elem.find("sm:loc", NAMESPACES)
        if loc is not None and loc.text:
            urls.append(loc.text)

    return urls


def filter_review_urls(urls: list[str]) -> list[str]:
    """Filter URLs to only include review pages."""
    review_urls = []

    for url in urls:
        # Match URLs like /reviews/a12345/...
        if re.search(r"/reviews/a\d+/", url):
            review_urls.append(url)

    return review_urls


def main():
    script_dir = Path(__file__).parent
    output_file = script_dir / "car-review-urls.txt"

    session = requests.Session()
    all_review_urls = set()

    # Step 1: Fetch sitemap index
    logger.info(f"Fetching sitemap index: {SITEMAP_INDEX_URL}")
    index_content = fetch_url(SITEMAP_INDEX_URL, session)
    if not index_content:
        logger.error("Failed to fetch sitemap index")
        return

    sitemap_urls = parse_sitemap_index(index_content)
    logger.info(f"Found {len(sitemap_urls)} sitemaps in index")

    # Filter to content sitemaps (most likely to contain reviews)
    content_sitemaps = [url for url in sitemap_urls if "content" in url.lower()]
    logger.info(f"Found {len(content_sitemaps)} content sitemaps")

    # If no content sitemaps found, try all sitemaps
    if not content_sitemaps:
        content_sitemaps = sitemap_urls
        logger.info("No content-specific sitemaps found, using all sitemaps")

    # Step 2: Fetch each sitemap and extract review URLs
    for i, sitemap_url in enumerate(content_sitemaps, 1):
        logger.info(f"Processing sitemap {i}/{len(content_sitemaps)}: {sitemap_url}")

        sitemap_content = fetch_url(sitemap_url, session)
        if not sitemap_content:
            continue

        # Check if gzipped
        is_gzipped = sitemap_url.endswith(".gz")

        try:
            urls = parse_sitemap(sitemap_content, is_gzipped)
            review_urls = filter_review_urls(urls)

            logger.info(f"  Found {len(urls)} total URLs, {len(review_urls)} review URLs")
            all_review_urls.update(review_urls)

        except Exception as e:
            logger.error(f"  Error parsing sitemap: {e}")

        # Delay between requests
        if i < len(content_sitemaps):
            time.sleep(add_jitter(BASE_DELAY))

    # Step 3: Sort and save
    sorted_urls = sorted(all_review_urls)

    with open(output_file, "w") as f:
        for url in sorted_urls:
            f.write(url + "\n")

    logger.info(f"\n{'='*60}")
    logger.info(f"Crawl complete!")
    logger.info(f"Total review URLs found: {len(sorted_urls)}")
    logger.info(f"Saved to: {output_file}")

    # Show some stats
    years = {}
    for url in sorted_urls:
        match = re.search(r"/(\d{4})-", url)
        if match:
            year = match.group(1)
            years[year] = years.get(year, 0) + 1

    logger.info(f"\nReviews by year (sample):")
    for year in sorted(years.keys(), reverse=True)[:10]:
        logger.info(f"  {year}: {years[year]}")


if __name__ == "__main__":
    main()
