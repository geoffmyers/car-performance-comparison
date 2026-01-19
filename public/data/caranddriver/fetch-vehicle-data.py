#!/usr/bin/env python3
"""
Batch fetch vehicle comparison data from Car and Driver GraphQL API.
Iterates through trim IDs from CSV and queries the API in batches.
Implements aggressive rate limiting and exponential backoff.
"""

import csv
import json
import time
import random
import logging
from pathlib import Path
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configuration
BATCH_SIZE = 100  # Number of trim IDs per request (tested up to 1000, but 100 is safer)
BASE_DELAY = 2.0  # Base delay between requests in seconds
MAX_RETRIES = 5  # Maximum number of retries per batch
INITIAL_BACKOFF = 5.0  # Initial backoff time in seconds
MAX_BACKOFF = 300.0  # Maximum backoff time (5 minutes)
JITTER_FACTOR = 0.3  # Random jitter factor (0-30% of delay)
RATE_LIMIT_THRESHOLD = 5  # Start slowing down when remaining requests fall below this

# API Configuration
API_URL = "https://heimdall.hearstapps.com/voltron"
HEADERS = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.8",
    "authorization": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Imp3dF9zZWNyZXRfZnJlIn0.e30.wlF-prqbR7gQ28qeFJrGOTKcct5p5jzNfrO6NBcc7C8",
    "cache-control": "no-cache",
    "content-type": "application/json",
    "dnt": "1",
    "origin": "https://www.caranddriver.com",
    "pragma": "no-cache",
    "referer": "https://www.caranddriver.com/",
    "sec-ch-ua": '"Brave";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "cross-site",
    "sec-gpc": "1",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
    "x-user-agent": "fre/1.7.54 Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
}

GRAPHQL_QUERY = """
    query vehicleCompareSelectedVehicleQuery($trimIds: [String!]!) {
        vehicle_compare_data(IDs: $trimIds) {
            id
            display
            make
            model
            year
            sibling_compare_data
            lede_image {
                id
                media_type
                metadata {
                    crops
                }
                media_object {
                    id
                    hips_url
                    metadata {
                        crops
                    }
                }
            }
            dataPoints
        }
    }
"""

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("fetch-vehicle-data.log"),
    ],
)
logger = logging.getLogger(__name__)


def create_session() -> requests.Session:
    """Create a requests session with retry logic."""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def add_jitter(delay: float) -> float:
    """Add random jitter to delay to avoid thundering herd."""
    jitter = delay * JITTER_FACTOR * random.random()
    return delay + jitter


def fetch_batch(
    session: requests.Session, trim_ids: list[str], batch_num: int, total_batches: int
) -> tuple[list[dict], dict]:
    """
    Fetch vehicle data for a batch of trim IDs.
    Returns (vehicles, rate_limit_info).
    """
    payload = {"query": GRAPHQL_QUERY, "variables": {"trimIds": trim_ids}}

    backoff = INITIAL_BACKOFF
    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            response = session.post(
                API_URL, headers=HEADERS, json=payload, timeout=60
            )

            rate_limit_info = {
                "limit": response.headers.get("ratelimit-limit"),
                "remaining": response.headers.get("ratelimit-remaining"),
                "reset": response.headers.get("ratelimit-reset"),
            }

            if response.status_code == 200:
                data = response.json()
                vehicles = data.get("vehicle_compare_data", [])
                logger.info(
                    f"Batch {batch_num}/{total_batches}: Fetched {len(vehicles)} vehicles "
                    f"(Rate limit: {rate_limit_info['remaining']}/{rate_limit_info['limit']} remaining)"
                )
                return vehicles, rate_limit_info

            elif response.status_code == 429:
                # Rate limited - use exponential backoff
                retry_after = int(response.headers.get("Retry-After", backoff))
                wait_time = max(retry_after, backoff)
                logger.warning(
                    f"Rate limited on batch {batch_num}. Waiting {wait_time:.1f}s (attempt {attempt + 1}/{MAX_RETRIES})"
                )
                time.sleep(add_jitter(wait_time))
                backoff = min(backoff * 2, MAX_BACKOFF)

            else:
                logger.error(
                    f"Batch {batch_num}: HTTP {response.status_code} - {response.text[:200]}"
                )
                last_error = f"HTTP {response.status_code}"
                time.sleep(add_jitter(backoff))
                backoff = min(backoff * 2, MAX_BACKOFF)

        except requests.exceptions.Timeout:
            logger.warning(
                f"Timeout on batch {batch_num} (attempt {attempt + 1}/{MAX_RETRIES})"
            )
            last_error = "Timeout"
            time.sleep(add_jitter(backoff))
            backoff = min(backoff * 2, MAX_BACKOFF)

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error on batch {batch_num}: {e}")
            last_error = str(e)
            time.sleep(add_jitter(backoff))
            backoff = min(backoff * 2, MAX_BACKOFF)

    logger.error(f"Batch {batch_num} failed after {MAX_RETRIES} attempts: {last_error}")
    return [], {}


def load_trim_ids(csv_path: Path) -> list[str]:
    """Load trim IDs from CSV file."""
    trim_ids = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("trim_id"):
                trim_ids.append(row["trim_id"])
    return trim_ids


def load_progress(progress_path: Path) -> set[str]:
    """Load already-fetched trim IDs from progress file."""
    if not progress_path.exists():
        return set()
    with open(progress_path, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


def save_progress(progress_path: Path, trim_ids: list[str]) -> None:
    """Append fetched trim IDs to progress file."""
    with open(progress_path, "a", encoding="utf-8") as f:
        for trim_id in trim_ids:
            f.write(f"{trim_id}\n")


def save_vehicles(output_path: Path, vehicles: list[dict], mode: str = "a") -> None:
    """Save vehicles to JSON Lines file (one JSON object per line)."""
    with open(output_path, mode, encoding="utf-8") as f:
        for vehicle in vehicles:
            f.write(json.dumps(vehicle) + "\n")


def main():
    script_dir = Path(__file__).parent
    csv_path = script_dir / "compare-model-data.csv"
    output_path = script_dir / "vehicle-data.jsonl"
    progress_path = script_dir / "fetch-progress.txt"

    # Load trim IDs and check progress
    all_trim_ids = load_trim_ids(csv_path)
    completed_ids = load_progress(progress_path)

    # Filter out already-fetched IDs
    remaining_ids = [tid for tid in all_trim_ids if tid not in completed_ids]

    logger.info(f"Total trim IDs: {len(all_trim_ids)}")
    logger.info(f"Already fetched: {len(completed_ids)}")
    logger.info(f"Remaining: {len(remaining_ids)}")

    if not remaining_ids:
        logger.info("All trim IDs have been fetched. Nothing to do.")
        return

    # Initialize output file if starting fresh
    if not completed_ids:
        output_path.write_text("")  # Clear file

    # Create batches
    batches = [
        remaining_ids[i : i + BATCH_SIZE]
        for i in range(0, len(remaining_ids), BATCH_SIZE)
    ]
    total_batches = len(batches)

    logger.info(f"Processing {total_batches} batches of up to {BATCH_SIZE} trim IDs each")

    # Create session
    session = create_session()

    # Process batches
    total_fetched = 0
    total_failed = 0
    start_time = datetime.now()

    for batch_num, batch_ids in enumerate(batches, 1):
        vehicles, rate_limit_info = fetch_batch(
            session, batch_ids, batch_num, total_batches
        )

        if vehicles:
            save_vehicles(output_path, vehicles)
            save_progress(progress_path, [v["id"] for v in vehicles])
            total_fetched += len(vehicles)
        else:
            total_failed += len(batch_ids)
            logger.warning(f"Failed to fetch batch {batch_num} ({len(batch_ids)} trim IDs)")

        # Calculate delay based on rate limit
        delay = BASE_DELAY
        if rate_limit_info.get("remaining"):
            remaining = int(rate_limit_info["remaining"])
            if remaining < RATE_LIMIT_THRESHOLD:
                # Increase delay when approaching rate limit
                delay = BASE_DELAY * (RATE_LIMIT_THRESHOLD - remaining + 1)
                logger.info(f"Rate limit approaching, increasing delay to {delay:.1f}s")

        # Don't delay after last batch
        if batch_num < total_batches:
            time.sleep(add_jitter(delay))

        # Progress report every 10 batches
        if batch_num % 10 == 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = total_fetched / elapsed if elapsed > 0 else 0
            remaining_count = len(remaining_ids) - (batch_num * BATCH_SIZE)
            eta_seconds = remaining_count / rate if rate > 0 else 0
            eta_minutes = eta_seconds / 60
            logger.info(
                f"Progress: {total_fetched} fetched, {total_failed} failed, "
                f"{rate:.1f} vehicles/sec, ETA: {eta_minutes:.1f} min"
            )

    # Final summary
    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info("=" * 60)
    logger.info("Fetch completed!")
    logger.info(f"Total fetched: {total_fetched}")
    logger.info(f"Total failed: {total_failed}")
    logger.info(f"Time elapsed: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
    logger.info(f"Output file: {output_path}")


if __name__ == "__main__":
    main()
