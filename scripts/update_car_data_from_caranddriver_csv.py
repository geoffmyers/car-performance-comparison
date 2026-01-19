#!/usr/bin/env python3
"""
Parse Car and Driver CSV files and update the master car performance database.

This script:
1. Reads all CSV files from the caranddriver/ directory and subdirectories
2. Parses and normalizes data from various Car and Driver data sources:
   - car-review-specs.csv: Performance test data (0-60, quarter mile, braking, etc.)
   - Lightning_Lap_Results: VIR track lap times
3. Standardizes manufacturer names, years, and performance metrics
4. Merges duplicate entries by year + manufacturer + model
5. Updates the master car-performance-data.csv without modifying source files

Usage:
    python update_car_data_from_caranddriver_csv.py
"""

import csv
import re
from pathlib import Path
from typing import Optional


# Manufacturer to country mapping (same as Wikipedia script for consistency)
MANUFACTURER_COUNTRIES = {
    "AC": "GB", "Acura": "JP", "Alfa Romeo": "IT", "Alpine": "FR", "Alpina": "DE",
    "AMC": "US", "Aprilia": "IT", "Ariel": "GB", "Artega": "DE", "Ascari": "GB",
    "Aspark": "JP", "Aston Martin": "GB", "Audi": "DE", "BAC": "GB", "Bentley": "GB",
    "BMW": "DE", "Bowler": "GB", "Brabham": "AU", "Brabus": "DE", "Bugatti": "FR",
    "Buick": "US", "BYD": "CN", "Cadillac": "US", "Callaway": "US", "Caterham": "GB",
    "Chevrolet": "US", "Chrysler": "US", "Citroën": "FR", "Clive Sutton": "GB",
    "Cosworth": "GB", "Cupra": "ES", "Czinger": "US", "Dacia": "RO", "Dallara": "IT",
    "Datsun": "JP", "Dauer": "DE", "De Tomaso": "IT", "Denza": "CN", "Dodge": "US",
    "Donkervoort": "NL", "Drako": "US", "Einride": "SE", "Eagle": "GB",
    "Faraday Future": "US", "Ferrari": "IT", "Fiat": "IT", "Fisker": "US", "Ford": "US",
    "Genesis": "KR", "Geely": "CN", "Ginetta": "GB", "GMC": "US", "Gordon Murray": "GB",
    "Gumpert": "DE", "Hawk": "GB", "Hennessey": "US", "Holden": "AU", "Honda": "JP",
    "HSV": "AU", "Hummer": "US", "Hyundai": "KR", "Hyptec": "CN", "Infiniti": "JP",
    "Iso": "IT", "Italdesign": "IT", "Jaguar": "GB", "Jeep": "US", "Jensen": "GB",
    "Karma": "US", "Kia": "KR", "Koenigsegg": "SE", "KTM": "AT", "Lada": "RU",
    "LaFerrari": "IT", "Lamborghini": "IT", "Lancia": "IT", "Land Rover": "GB",
    "Lexus": "JP", "Lincoln": "US", "Lister": "GB", "Litchfield": "GB", "Lotus": "GB",
    "Lucid": "US", "M-Hero": "CN", "Marcos": "GB", "Maserati": "IT", "Mazda": "JP",
    "McLaren": "GB", "Mercedes-AMG": "DE", "Mercedes-Benz": "DE", "Mercedes": "DE",
    "Mercury": "US", "MG": "GB", "Mini": "GB", "MINI": "GB", "Mitsubishi": "JP",
    "MMX": "DE", "Mobility Ventures": "US", "Morgan": "GB", "Mosler": "US", "Napier": "GB",
    "NIO": "CN", "Nissan": "JP", "Noble": "GB", "Oldsmobile": "US", "Opel": "DE",
    "Overfinch": "GB", "Packard": "US", "Pagani": "IT", "Peugeot": "FR", "Pininfarina": "IT",
    "Plymouth": "US", "Polestar": "SE", "Pontiac": "US", "Porsche": "DE", "Praga": "CZ",
    "Prodrive": "GB", "RacingLine": "GB", "Radical": "GB", "Ram": "US",
    "Range Rover": "GB", "Renault": "FR", "Renaultsport": "FR", "Rimac": "HR",
    "Rivian": "US", "Rolls-Royce": "GB", "Roush": "US", "Ruf": "DE", "Saab": "SE",
    "Saleen": "US", "SEAT": "ES", "Shelby": "US", "Singer": "US", "Skoda": "CZ",
    "Smart": "DE", "Spyker": "NL", "SSC": "US", "Subaru": "JP", "Sunbeam": "GB",
    "Suzuki": "JP", "Tesla": "US", "Toyota": "JP", "TR": "GB", "Trabant": "DE",
    "Triumph": "GB", "Tuthill": "GB", "TVR": "GB", "Ultima": "GB", "Vauxhall": "GB",
    "Vector": "US", "Venturi": "FR", "Veritas": "DE", "Volkswagen": "DE", "Volvo": "SE",
    "W Motors": "AE", "Wiesmann": "DE", "Xiaomi": "CN", "Yangwang": "CN",
    "YANGWANG": "CN", "Zeekr": "CN", "Zenos": "GB", "Zenvo": "DK",
}

# Normalize manufacturer names
MANUFACTURER_ALIASES = {
    "80": "Napier",  # Fix malformed Wikipedia data (80 was horsepower, Napier is manufacturer)
    "Alfa": "Alfa Romeo",  # Handle "Alfa" being split from "Romeo"
    "Aston": "Aston Martin",  # Handle "Aston" being split from "Martin"
    "Land": "Land Rover",  # Handle "Land" being split from "Rover"
    "Range": "Range Rover",  # Handle "Range" being split from "Rover"
    "Mercedes": "Mercedes-Benz",
    "Mercedes Amg": "Mercedes-AMG",
    "Mercedes-amg": "Mercedes-AMG",
    "Mercedes Benz": "Mercedes-Benz",
    "MINI": "Mini",
    "Bmw": "BMW",
    "Gmc": "GMC",
    "Vw": "Volkswagen",
    "VW": "Volkswagen",
    "YANGWANG": "Yangwang",
    "Renaultsport": "Renault",
    "LaFerrari": "Ferrari",
    "Land rover": "Land Rover",
    "Rolls Royce": "Rolls-Royce",
    "Aston martin": "Aston Martin",
    "Srt": "Dodge",  # SRT is a Dodge sub-brand
    "SRT": "Dodge",
}

# Files to skip (test files, non-performance data)
SKIP_FILES = {
    'car-review-specs-old.csv',
    'car-review-specs-test.csv',
    'car-review-specs-test2.csv',
    'compare-model-data.csv',  # This is trim/model metadata, not performance data
}


def clean_text(text: str) -> str:
    """Clean text by removing extra whitespace."""
    if not text:
        return ""
    text = ' '.join(text.split())
    return text.strip()


def normalize_manufacturer(manufacturer: str) -> str:
    """Normalize manufacturer name to standard form."""
    if not manufacturer:
        return ""
    manufacturer = clean_text(manufacturer)

    # Check aliases first (exact match)
    if manufacturer in MANUFACTURER_ALIASES:
        return MANUFACTURER_ALIASES[manufacturer]

    # Title case for comparison
    title_case = manufacturer.title() if manufacturer.islower() else manufacturer
    if title_case in MANUFACTURER_ALIASES:
        return MANUFACTURER_ALIASES[title_case]

    # Check if manufacturer is in our known list
    if manufacturer in MANUFACTURER_COUNTRIES:
        return manufacturer
    if title_case in MANUFACTURER_COUNTRIES:
        return title_case

    return title_case


def extract_manufacturer_from_make(make_str: str) -> tuple[str, str]:
    """Extract manufacturer from make string that may include model info.

    E.g., "Toyota Prius" -> ("Toyota", "Prius")
          "Mercedes Amg" -> ("Mercedes-AMG", "")
          "Alfa Romeo" -> ("Alfa Romeo", "")
    """
    if not make_str:
        return "", ""

    make_str = clean_text(make_str)

    # First check if the whole string is a known manufacturer (handles "Alfa Romeo", "Land Rover", etc.)
    normalized = normalize_manufacturer(make_str)
    if normalized in MANUFACTURER_COUNTRIES:
        return normalized, ""

    # Check for known multi-word manufacturers first (longest match)
    for mfr in sorted(MANUFACTURER_COUNTRIES.keys(), key=len, reverse=True):
        mfr_lower = mfr.lower()
        make_lower = make_str.lower()

        if make_lower.startswith(mfr_lower):
            remaining = make_str[len(mfr):].strip()
            return normalize_manufacturer(mfr), remaining
        # Also check with spaces normalized
        if make_lower.replace(' ', '-') == mfr_lower.replace(' ', '-'):
            return normalize_manufacturer(mfr), ""

    # Try to split on first space and check if first word is a manufacturer
    parts = make_str.split(' ', 1)
    if len(parts) >= 1:
        first_normalized = normalize_manufacturer(parts[0])
        if first_normalized in MANUFACTURER_COUNTRIES:
            return first_normalized, parts[1] if len(parts) > 1 else ""

    # Return as-is if no match
    return normalize_manufacturer(make_str), ""


def get_country_for_manufacturer(manufacturer: str) -> str:
    """Get country code for manufacturer."""
    return MANUFACTURER_COUNTRIES.get(manufacturer, "")


def parse_float(value: str) -> Optional[float]:
    """Parse a float value from string, handling common formats."""
    if not value or value in ['', 'N/A', 'n/a', '-']:
        return None
    try:
        # Remove commas and whitespace
        cleaned = value.replace(',', '').strip()
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def parse_year(year_str: str) -> Optional[str]:
    """Parse year from string."""
    if not year_str:
        return None
    year_str = clean_text(str(year_str))
    # Match 4-digit year
    match = re.search(r'(19\d{2}|20\d{2})', year_str)
    if match:
        return match.group(1)
    return None


def parse_lap_time_to_seconds(time_str: str) -> Optional[float]:
    """Parse lap time string (mm:ss.s format) to seconds."""
    if not time_str:
        return None
    time_str = clean_text(time_str)

    # Handle mm:ss.sss format (e.g., "2:34.9" or "6:29.090")
    match = re.search(r'(\d+):(\d+(?:\.\d+)?)', time_str)
    if match:
        minutes = int(match.group(1))
        seconds = float(match.group(2))
        return minutes * 60 + seconds

    return None


def clean_model_name(model: str, manufacturer: str) -> str:
    """Clean up model name by removing test suffixes and normalizing."""
    if not model:
        return ""

    model = clean_text(model)

    # Remove common C&D test suffixes
    suffixes_to_remove = [
        r'\s+Test\s*$',
        r'\s+First Drive\s*\|?\s*$',
        r'\s+First Drive$',
        r'\s+Instrumented\s*$',
        r'\s+Full Test\s*$',
        r'\s+Quick Take\s*$',
        r'\s+Road Test\s*$',
        r'\s+Drive\s*$',
        r'\s+Review\s*$',
        r'\s+Prototype\s*$',
        r'\s+Tested\s*$',
        r'\s+Long Term\s*$',
        r'\s+Long Term Wrap\s*$',
        r'\s*\|\s*$',  # Trailing pipe
    ]

    for suffix in suffixes_to_remove:
        model = re.sub(suffix, '', model, flags=re.IGNORECASE)

    # Clean up multiple spaces
    model = ' '.join(model.split())

    return model.strip()


def detect_propulsion(engine_type: str, model: str) -> str:
    """Detect propulsion type from engine description or model name."""
    if not engine_type and not model:
        return ""

    text = f"{engine_type or ''} {model or ''}".lower()

    if 'electric' in text or ' ev ' in text or text.endswith(' ev') or 'e-tron' in text:
        if 'plug-in' in text or 'phev' in text:
            return 'Plug-in Hybrid'
        if 'range extender' in text or 'rex' in text:
            return 'Hybrid'
        if 'hybrid' not in text:
            return 'Electric'

    if 'plug-in hybrid' in text or 'phev' in text:
        return 'Plug-in Hybrid'

    if 'hybrid' in text:
        return 'Hybrid'

    # Check for obvious ICE indicators
    if any(x in text for x in ['turbocharged', 'supercharged', 'v-8', 'v-6', 'inline-4',
                                'inline-6', 'v8', 'v6', 'v10', 'v12', 'flat-6', 'diesel']):
        return 'ICE'

    return ""


class CarAndDriverCSVParser:
    """Parser for Car and Driver CSV data files."""

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.caranddriver_path = base_path / 'caranddriver'

    def parse_all_csv_files(self) -> list[dict]:
        """Parse all CSV files in the caranddriver directory."""
        all_cars = []

        # Find all CSV files
        csv_files = list(self.caranddriver_path.glob('**/*.csv'))
        print(f"Found {len(csv_files)} CSV files in caranddriver/")

        for csv_path in csv_files:
            # Skip test files and non-performance data
            if csv_path.name in SKIP_FILES:
                print(f"  Skipping {csv_path.name} (excluded)")
                continue

            try:
                cars = self._parse_csv_file(csv_path)
                all_cars.extend(cars)
                if cars:
                    print(f"  Parsed {csv_path.name}: {len(cars)} entries")
            except Exception as e:
                print(f"  Error parsing {csv_path.name}: {e}")

        return all_cars

    def _parse_csv_file(self, csv_path: Path) -> list[dict]:
        """Parse a single CSV file based on its content type."""
        filename = csv_path.name.lower()
        parent_dir = csv_path.parent.name.lower()

        # Determine parser based on filename/directory
        if 'lightning_lap' in filename or 'lightning_lap' in parent_dir:
            return self._parse_lightning_lap_csv(csv_path)
        elif 'car-review-specs' in filename:
            return self._parse_review_specs_csv(csv_path)
        else:
            # Try to auto-detect based on headers
            return self._parse_generic_csv(csv_path)

    def _parse_review_specs_csv(self, csv_path: Path) -> list[dict]:
        """Parse car-review-specs.csv - main C&D performance test data."""
        cars = []

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                # Get manufacturer and model - handle case where make includes model info
                make_raw = row.get('make', '')
                model_raw = row.get('model', '')

                # Extract manufacturer from make (may include model)
                manufacturer, model_prefix = extract_manufacturer_from_make(make_raw)

                if not manufacturer:
                    continue

                # Combine model_prefix with model_raw if needed
                if model_prefix and model_raw:
                    full_model = f"{model_prefix} {model_raw}"
                elif model_prefix:
                    full_model = model_prefix
                else:
                    full_model = model_raw

                if not full_model:
                    continue

                # Handle special case where "Alfa" was split from "Romeo"
                # Model might start with "Romeo " which should be stripped
                if manufacturer == "Alfa Romeo" and full_model.lower().startswith("romeo "):
                    full_model = full_model[6:].strip()  # Remove "Romeo "

                # Clean model name
                model = clean_model_name(full_model, manufacturer)

                # Get year
                year = parse_year(row.get('year', ''))

                # Detect propulsion type
                engine_type = row.get('engine_type', '')
                propulsion = detect_propulsion(engine_type, model)

                # Parse performance metrics
                zero_to_60 = parse_float(row.get('zero_to_60_mph', ''))
                zero_to_100 = parse_float(row.get('zero_to_100_mph', ''))
                quarter_mile_time = parse_float(row.get('quarter_mile_time', ''))
                quarter_mile_speed = parse_float(row.get('quarter_mile_speed', ''))
                top_speed = parse_float(row.get('top_speed', ''))
                braking_70_0 = parse_float(row.get('braking_70_0', ''))
                braking_100_0 = parse_float(row.get('braking_100_0', ''))
                skidpad_g = parse_float(row.get('skidpad_g', ''))
                power_hp = parse_float(row.get('power_hp', ''))
                torque = parse_float(row.get('torque_lb_ft', ''))
                curb_weight = parse_float(row.get('curb_weight', ''))

                # Skip entries with no performance data
                has_performance = any([
                    zero_to_60, zero_to_100, quarter_mile_time,
                    top_speed, braking_70_0, skidpad_g
                ])

                if not has_performance:
                    continue

                # Check if data is estimated
                is_estimated = row.get('is_estimated', '').lower() == 'yes'

                car_data = {
                    'manufacturer': manufacturer,
                    'model': model,
                    'year': year,
                    'propulsion': propulsion,
                    'source': 'caranddriver',
                    'source_url': row.get('url', ''),
                }

                # Add performance metrics if present
                if zero_to_60:
                    car_data['0_60_mph_sec'] = zero_to_60
                if zero_to_100:
                    car_data['0_100_mph_sec'] = zero_to_100
                if quarter_mile_time:
                    car_data['quarter_mile_sec'] = quarter_mile_time
                if top_speed:
                    car_data['top_speed_mph'] = top_speed
                if power_hp:
                    car_data['power_hp'] = power_hp
                    car_data['power_kw'] = round(power_hp * 0.7457, 1)
                if torque:
                    car_data['torque'] = f"{int(torque)} lb-ft"

                # Add C&D specific metrics
                if braking_70_0:
                    car_data['braking_70_0_ft'] = braking_70_0
                if braking_100_0:
                    car_data['braking_100_0_ft'] = braking_100_0
                if skidpad_g:
                    car_data['skidpad_g'] = skidpad_g
                if quarter_mile_speed:
                    car_data['quarter_mile_speed_mph'] = quarter_mile_speed
                if curb_weight:
                    car_data['curb_weight_lb'] = curb_weight

                # Mark if estimated
                if is_estimated:
                    car_data['is_estimated'] = True

                cars.append(car_data)

        return cars

    def _parse_lightning_lap_csv(self, csv_path: Path) -> list[dict]:
        """Parse Lightning Lap (VIR track) results CSV."""
        cars = []

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []

            # Find the year/make/model column and lap time column
            ymm_col = None
            time_col = None

            for h in headers:
                h_lower = h.lower()
                if 'year' in h_lower and 'make' in h_lower:
                    ymm_col = h
                elif 'lap' in h_lower and 'time' in h_lower:
                    time_col = h
                elif h_lower == 'time':
                    time_col = h

            if not ymm_col:
                # Try first column if it looks like "Year Make Model"
                ymm_col = headers[0] if headers else None
            if not time_col:
                # Try second column for lap time
                time_col = headers[1] if len(headers) > 1 else None

            if not ymm_col or not time_col:
                return []

            for row in reader:
                ymm_text = row.get(ymm_col, '')
                time_text = row.get(time_col, '')

                if not ymm_text or not time_text:
                    continue

                # Parse "2019 McLaren Senna" format
                match = re.match(r'^(\d{4})\s+(.+)$', ymm_text.strip())
                if not match:
                    continue

                year = match.group(1)
                make_model = match.group(2).strip()

                # Try to extract manufacturer from make_model
                manufacturer = None
                model = None

                # Check known manufacturers (longest first)
                for mfr in sorted(MANUFACTURER_COUNTRIES.keys(), key=len, reverse=True):
                    if make_model.lower().startswith(mfr.lower()):
                        manufacturer = normalize_manufacturer(mfr)
                        model = make_model[len(mfr):].strip()
                        break

                if not manufacturer:
                    # Try splitting on first space
                    parts = make_model.split(' ', 1)
                    if len(parts) >= 2:
                        manufacturer = normalize_manufacturer(parts[0])
                        model = parts[1]
                    else:
                        continue

                # Parse lap time
                lap_time_sec = parse_lap_time_to_seconds(time_text)
                if not lap_time_sec:
                    continue

                car_data = {
                    'manufacturer': manufacturer,
                    'model': model,
                    'year': year,
                    'lightning_lap_sec': lap_time_sec,
                    'source': 'caranddriver_lightning_lap',
                }

                cars.append(car_data)

        return cars

    def _parse_generic_csv(self, csv_path: Path) -> list[dict]:
        """Try to parse a generic CSV file - return empty if not recognized."""
        # For safety, don't try to parse unknown files
        return []


def normalize_model_name(model: str) -> str:
    """Normalize model name for key matching."""
    model = model.lower().strip()
    # Remove year from model if present in parentheses
    model = re.sub(r'\s*\(\d{4}\)\s*', ' ', model).strip()
    # Remove extra specifications in parentheses for basic matching
    base_model = re.sub(r'\s*\([^)]+\)\s*', ' ', model).strip()
    base_model = re.sub(r'\s+', ' ', base_model)
    return base_model


def create_car_key(car: dict, include_year: bool = True) -> tuple:
    """Create a unique key for a car based on manufacturer, model, and optionally year."""
    manufacturer = car.get('manufacturer', '').lower().strip()
    model = normalize_model_name(car.get('model', ''))

    if include_year:
        year = car.get('year') or ''
        return (year, manufacturer, model)
    else:
        return (manufacturer, model)


def merge_car_data(existing_data: list[dict], new_data: list[dict]) -> list[dict]:
    """Merge new data into existing data, updating or adding entries."""
    # Create lookups
    lookup_with_year = {}  # (year, manufacturer, model) -> car
    lookup_no_year = {}    # (manufacturer, model) -> list of cars

    def add_to_lookups(car: dict):
        """Add car to lookup dictionaries."""
        key_with_year = create_car_key(car, include_year=True)
        key_no_year = create_car_key(car, include_year=False)

        if key_with_year not in lookup_with_year:
            lookup_with_year[key_with_year] = car
        else:
            _merge_into(lookup_with_year[key_with_year], car)

        # Track all entries by model (for year-less matching)
        if key_no_year not in lookup_no_year:
            lookup_no_year[key_no_year] = []
        # Keep reference to the entry
        if lookup_with_year[key_with_year] not in lookup_no_year[key_no_year]:
            lookup_no_year[key_no_year].append(lookup_with_year[key_with_year])

    # Process existing data
    for car in existing_data:
        add_to_lookups(car.copy())

    # Merge new data
    for car in new_data:
        key_with_year = create_car_key(car, include_year=True)
        key_no_year = create_car_key(car, include_year=False)

        # First try exact match with year
        if key_with_year in lookup_with_year:
            _merge_into(lookup_with_year[key_with_year], car)
        # If new entry has a year, add as new entry
        elif car.get('year'):
            new_car = car.copy()
            source = new_car.pop('source', '')
            new_car['sources'] = source
            new_car['country'] = get_country_for_manufacturer(new_car.get('manufacturer', ''))
            add_to_lookups(new_car)
        # No year in new entry - try to find matching entry without year
        elif key_no_year in lookup_no_year:
            # Merge into first matching entry
            existing = lookup_no_year[key_no_year][0]
            _merge_into(existing, car)
        else:
            # Add as new entry
            new_car = car.copy()
            source = new_car.pop('source', '')
            new_car['sources'] = source
            new_car['country'] = get_country_for_manufacturer(new_car.get('manufacturer', ''))
            add_to_lookups(new_car)

    # Convert back to list and sort
    result = list(lookup_with_year.values())
    result.sort(key=lambda x: (
        x.get('manufacturer', ''),
        x.get('model', ''),
        x.get('year') or ''
    ))

    return result


def _merge_into(existing: dict, new: dict):
    """Merge new car data into existing car data."""
    # Fields to merge (don't overwrite if existing has value, except for specific cases)
    merge_fields = [
        'year', 'propulsion', '0_60_mph_sec', '0_100_kmh_sec', '0_100_mph_sec',
        '0_200_kmh_sec', 'quarter_mile_sec', 'quarter_mile_speed_mph',
        'top_speed_mph', 'top_speed_kmh', 'power_hp', 'power_kw', 'torque',
        'engine', 'nurburgring_lap_sec', 'nurburgring_date', 'nurburgring_driver',
        'top_gear_lap_sec', 'top_gear_episode', 'lightning_lap_sec',
        'braking_70_0_ft', 'braking_100_0_ft', 'skidpad_g', 'curb_weight_lb',
    ]

    for field in merge_fields:
        new_val = new.get(field)
        if new_val and not existing.get(field):
            existing[field] = new_val

    # Append source
    existing_sources = existing.get('sources', '')
    new_source = new.get('source', '') or new.get('sources', '')
    if new_source:
        existing_source_list = [s.strip() for s in existing_sources.split(',') if s.strip()]
        new_source_list = [s.strip() for s in new_source.split(',') if s.strip()]
        for src in new_source_list:
            if src and src not in existing_source_list:
                existing_source_list.append(src)
        existing['sources'] = ', '.join(existing_source_list)


def load_existing_data(csv_path: Path) -> list[dict]:
    """Load existing car performance data from CSV."""
    if not csv_path.exists():
        return []

    cars = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Normalize manufacturer name and update country if needed
            manufacturer = row.get('manufacturer', '')
            normalized = normalize_manufacturer(manufacturer)
            if normalized != manufacturer:
                row['manufacturer'] = normalized
            # Update country code if empty or manufacturer was normalized
            if not row.get('country') or normalized != manufacturer:
                row['country'] = get_country_for_manufacturer(normalized)
            cars.append(row)
    return cars


def save_data(csv_path: Path, data: list[dict], columns: list[str]):
    """Save car data to CSV."""
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()

        for car in data:
            # Clean up values
            cleaned = {}
            for col in columns:
                val = car.get(col, '')
                if val is None:
                    val = ''
                elif isinstance(val, float):
                    # Format floats nicely
                    if val == int(val):
                        val = str(int(val))
                    else:
                        val = f"{val:.2f}".rstrip('0').rstrip('.')
                elif isinstance(val, bool):
                    val = 'yes' if val else ''
                cleaned[col] = str(val)
            writer.writerow(cleaned)


def main():
    # Setup paths
    script_path = Path(__file__).parent
    base_path = script_path.parent / 'public' / 'data'
    csv_path = base_path / 'car-performance-data.csv'

    print(f"Base path: {base_path}")
    print(f"Output CSV: {csv_path}")
    print()

    # Load existing data
    existing_data = load_existing_data(csv_path)
    print(f"Loaded {len(existing_data)} existing car entries")

    # Parse Car and Driver CSV files
    parser = CarAndDriverCSVParser(base_path)
    new_data = parser.parse_all_csv_files()
    print(f"\nParsed {len(new_data)} entries from Car and Driver CSVs")

    # Merge data
    merged_data = merge_car_data(existing_data, new_data)
    print(f"\nMerged to {len(merged_data)} unique car entries")

    # Define output columns (same as existing + new C&D specific columns)
    columns = [
        'manufacturer', 'country', 'model', 'year', 'propulsion',
        '0_60_mph_sec', '0_100_kmh_sec', '0_100_mph_sec', '0_200_kmh_sec',
        'quarter_mile_sec', 'quarter_mile_speed_mph',
        'top_speed_mph', 'top_speed_kmh',
        'power_hp', 'power_kw', 'torque', 'engine',
        'braking_70_0_ft', 'braking_100_0_ft', 'skidpad_g', 'curb_weight_lb',
        'nurburgring_lap_sec', 'nurburgring_date', 'nurburgring_driver',
        'top_gear_lap_sec', 'top_gear_episode',
        'lightning_lap_sec',
        'sources'
    ]

    # Save merged data
    save_data(csv_path, merged_data, columns)
    print(f"\nSaved {len(merged_data)} cars to {csv_path}")

    # Print summary
    print("\n=== Summary ===")
    print(f"Total cars: {len(merged_data)}")
    manufacturers = set(c.get('manufacturer', '') for c in merged_data if c.get('manufacturer'))
    print(f"Unique manufacturers: {len(manufacturers)}")

    # Count by source
    source_counts = {}
    for car in merged_data:
        sources = car.get('sources', '')
        for src in sources.split(','):
            src = src.strip()
            if src:
                source_counts[src] = source_counts.get(src, 0) + 1

    print("\nEntries by source:")
    for src, count in sorted(source_counts.items(), key=lambda x: -x[1]):
        print(f"  {src}: {count}")

    # Count entries with key performance data
    with_0_60 = sum(1 for c in merged_data if c.get('0_60_mph_sec'))
    with_qm = sum(1 for c in merged_data if c.get('quarter_mile_sec'))
    with_lightning = sum(1 for c in merged_data if c.get('lightning_lap_sec'))
    with_nurburgring = sum(1 for c in merged_data if c.get('nurburgring_lap_sec'))

    print("\nPerformance data coverage:")
    print(f"  0-60 mph times: {with_0_60}")
    print(f"  Quarter mile times: {with_qm}")
    print(f"  Lightning Lap times: {with_lightning}")
    print(f"  Nürburgring times: {with_nurburgring}")


if __name__ == '__main__':
    main()
