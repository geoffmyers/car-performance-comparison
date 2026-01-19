#!/usr/bin/env python3
"""
Parse Wikipedia CSV files and update the master car performance database.

This script:
1. Reads all CSV files from the wikipedia/ directory and subdirectories
2. Parses and normalizes data from various Wikipedia data sources
3. Standardizes manufacturer names, years, and performance metrics
4. Merges duplicate entries by year + manufacturer + model
5. Updates the master car-performance-data.csv without modifying source files

Usage:
    python update_car_data_from_wikipedia_csv.py
"""

import csv
import re
from pathlib import Path
from typing import Optional


# Manufacturer to country mapping
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
    "Lexus": "JP", "Lister": "GB", "Litchfield": "GB", "Lotus": "GB", "Lucid": "US",
    "M-Hero": "CN", "Marcos": "GB", "Maserati": "IT", "Mazda": "JP", "McLaren": "GB",
    "Mercedes-AMG": "DE", "Mercedes-Benz": "DE", "Mercedes": "DE", "Mercury": "US",
    "MG": "GB", "Mini": "GB", "MINI": "GB", "Mitsubishi": "JP", "MMX": "DE",
    "Morgan": "GB", "Mosler": "US", "Napier": "GB", "NIO": "CN", "Nissan": "JP",
    "Noble": "GB", "Oldsmobile": "US", "Opel": "DE", "Overfinch": "GB", "Packard": "US",
    "Pagani": "IT", "Peugeot": "FR", "Pininfarina": "IT", "Plymouth": "US",
    "Polestar": "SE", "Pontiac": "US", "Porsche": "DE", "Praga": "CZ", "Prodrive": "GB",
    "RacingLine": "GB", "Radical": "GB", "Ram": "US", "Range Rover": "GB",
    "Renault": "FR", "Renaultsport": "FR", "Rimac": "HR", "Rivian": "US",
    "Rolls-Royce": "GB", "Roush": "US", "Ruf": "DE", "Saab": "SE", "Saleen": "US",
    "SEAT": "ES", "Shelby": "US", "Singer": "US", "Skoda": "CZ", "Smart": "DE",
    "Spyker": "NL", "SSC": "US", "Subaru": "JP", "Sunbeam": "GB", "Suzuki": "JP",
    "Tesla": "US", "Toyota": "JP", "TR": "GB", "Triumph": "GB", "Tuthill": "GB",
    "TVR": "GB", "Ultima": "GB", "Vauxhall": "GB", "Vector": "US", "Venturi": "FR",
    "Veritas": "DE", "Volkswagen": "DE", "Volvo": "SE", "W Motors": "AE",
    "Wiesmann": "DE", "Xiaomi": "CN", "Yangwang": "CN", "YANGWANG": "CN",
    "Zeekr": "CN", "Zenos": "GB", "Zenvo": "DK",
}

# Normalize manufacturer names
MANUFACTURER_ALIASES = {
    "Mercedes": "Mercedes-Benz",
    "Mercedes AMG": "Mercedes-AMG",
    "MINI": "Mini",
    "YANGWANG": "Yangwang",
    "Renaultsport": "Renault",
    "LaFerrari": "Ferrari",
}


def clean_text(text: str) -> str:
    """Clean text by removing footnotes, extra whitespace, etc."""
    if not text:
        return ""
    # Remove footnote references like [1], [a], [iv], etc.
    text = re.sub(r'\[[\w\d,\s]+\]', '', text)
    # Remove citation needed, etc.
    text = re.sub(r'\[citation needed\]', '', text, flags=re.IGNORECASE)
    # Remove "—N/a", "N/a", "n/a" as standalone placeholders (not part of words)
    # Use word boundaries to avoid matching "Na" in "Napier"
    text = re.sub(r'\b—?[Nn]/?[Aa]\b', '', text)
    # Clean whitespace
    text = ' '.join(text.split())
    return text.strip()


def normalize_manufacturer(manufacturer: str) -> str:
    """Normalize manufacturer name."""
    manufacturer = clean_text(manufacturer)
    return MANUFACTURER_ALIASES.get(manufacturer, manufacturer)


def parse_car_name(car_text: str) -> tuple[str, str]:
    """Parse car name into manufacturer and model.

    Handles various formats:
    - "Porsche 911" -> (Porsche, 911)
    - "80 Napier" -> (Napier, 80)  # model prefix + manufacturer
    - "Mercedes-AMG GT" -> (Mercedes-AMG, GT)
    """
    car_text = clean_text(car_text)

    # Try to match known manufacturers anywhere in the text
    # (longest first to match "Mercedes-AMG" before "Mercedes")
    for manufacturer in sorted(MANUFACTURER_COUNTRIES.keys(), key=len, reverse=True):
        # Check if starts with manufacturer
        if car_text.lower().startswith(manufacturer.lower()):
            model = car_text[len(manufacturer):].strip()
            # Remove leading separators
            model = re.sub(r'^[\s\-/]+', '', model)
            return normalize_manufacturer(manufacturer), model

        # Check if manufacturer appears after a leading number/model (e.g., "80 Napier")
        # This handles cases like "80 Napier" where 80 is the model and Napier is manufacturer
        match = re.match(rf'^([\d\w\-\.]+)\s+({re.escape(manufacturer)})(?:\s+(.*))?$',
                         car_text, re.IGNORECASE)
        if match:
            prefix = match.group(1)
            suffix = match.group(3) or ''
            model = f"{prefix} {suffix}".strip() if suffix else prefix
            return normalize_manufacturer(manufacturer), model

    # Fallback: split on first space (if first part isn't purely numeric)
    parts = car_text.split(' ', 1)
    if len(parts) == 2:
        # If first part is purely numeric, it's likely a model number not manufacturer
        if parts[0].isdigit():
            return "", car_text  # Unknown manufacturer
        return normalize_manufacturer(parts[0]), parts[1]
    return normalize_manufacturer(car_text), ""


def parse_time_to_seconds(time_str: str) -> Optional[float]:
    """Parse time string to seconds (float)."""
    if not time_str:
        return None

    time_str = clean_text(time_str)
    if not time_str or time_str in ['DNF', 'DNS', 'unknown']:
        return None

    # Handle mm:ss.sss format (e.g., "01:09.6" or "6:29.090")
    match = re.search(r'(\d+):(\d+(?:\.\d+)?)', time_str)
    if match:
        minutes = int(match.group(1))
        seconds = float(match.group(2))
        return minutes * 60 + seconds

    # Handle just seconds (e.g., "1.9", "2.4 s", "9.06 s at 243.9 km/h")
    match = re.search(r'^(\d+(?:\.\d+)?)\s*(?:s|sec|seconds?)?', time_str)
    if match:
        return float(match.group(1))

    return None


def parse_speed(speed_str: str) -> tuple[Optional[float], Optional[float]]:
    """Parse speed string to mph and km/h."""
    if not speed_str:
        return None, None

    speed_str = clean_text(speed_str)
    mph = None
    kmh = None

    # Try to find km/h first (often in format "20 km/h (12 mph)")
    kmh_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:km/?h|kph|kmh)', speed_str, re.IGNORECASE)
    if kmh_match:
        kmh = float(kmh_match.group(1).replace(',', '.'))

    # Try to find mph
    mph_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:mph|mi/?h)', speed_str, re.IGNORECASE)
    if mph_match:
        mph = float(mph_match.group(1).replace(',', '.'))

    # If only one found, calculate the other
    if mph and not kmh:
        kmh = round(mph * 1.60934, 1)
    elif kmh and not mph:
        mph = round(kmh / 1.60934, 1)

    return mph, kmh


def parse_power(power_str: str) -> tuple[Optional[float], Optional[float]]:
    """Parse power string to hp and kW."""
    if not power_str:
        return None, None

    power_str = clean_text(power_str)
    hp = None
    kw = None

    # Try to find kW (often in format "1,550 kW (2,079 hp; 2,107 PS)")
    kw_match = re.search(r'(\d+(?:,\d+)?(?:\.\d+)?)\s*kW', power_str, re.IGNORECASE)
    if kw_match:
        kw = float(kw_match.group(1).replace(',', ''))

    # Try to find hp/bhp
    hp_match = re.search(r'(\d+(?:,\d+)?(?:\.\d+)?)\s*(?:hp|bhp)', power_str, re.IGNORECASE)
    if hp_match:
        hp = float(hp_match.group(1).replace(',', ''))
    else:
        # Try PS (metric horsepower)
        ps_match = re.search(r'(\d+(?:,\d+)?(?:\.\d+)?)\s*PS', power_str)
        if ps_match:
            ps = float(ps_match.group(1).replace(',', ''))
            hp = round(ps * 0.9863, 1)

    # If only one found, calculate the other
    if hp and not kw:
        kw = round(hp * 0.7457, 1)
    elif kw and not hp:
        hp = round(kw / 0.7457, 1)

    return hp, kw


def parse_year(year_str: str) -> Optional[str]:
    """Parse year from string."""
    if not year_str:
        return None

    year_str = clean_text(year_str)
    # Match 4-digit year
    match = re.search(r'(19\d{2}|20\d{2})', year_str)
    if match:
        return match.group(1)
    return None


def parse_propulsion(prop_str: str) -> str:
    """Normalize propulsion type."""
    if not prop_str:
        return ""

    prop_str = clean_text(prop_str).lower()

    if 'electric' in prop_str:
        return 'Electric'
    elif 'plug-in hybrid' in prop_str or 'phev' in prop_str:
        return 'Plug-in Hybrid'
    elif 'hybrid' in prop_str:
        return 'Hybrid'
    elif 'ice' in prop_str or 'internal combustion' in prop_str:
        return 'ICE'

    return ""


def get_country_for_manufacturer(manufacturer: str) -> str:
    """Get country code for manufacturer."""
    return MANUFACTURER_COUNTRIES.get(manufacturer, "")


class WikipediaCSVParser:
    """Parser for Wikipedia CSV data files."""

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.wikipedia_path = base_path / 'wikipedia'

    def parse_all_csv_files(self) -> list[dict]:
        """Parse all CSV files in the wikipedia directory."""
        all_cars = []

        # Find all CSV files
        csv_files = list(self.wikipedia_path.glob('**/*.csv'))
        print(f"Found {len(csv_files)} CSV files to parse")

        for csv_path in csv_files:
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
        import unicodedata
        # Determine the type of data based on directory/filename
        # Normalize to NFC to handle macOS NFD-encoded filenames
        parent_dir = unicodedata.normalize('NFC', csv_path.parent.name).lower()
        filename = unicodedata.normalize('NFC', csv_path.name).lower()

        if 'acceleration' in parent_dir or 'acceleration' in filename:
            return self._parse_acceleration_csv(csv_path)
        elif 'nürburgring' in parent_dir or 'nurburgring' in filename:
            return self._parse_nurburgring_csv(csv_path)
        elif 'speed_records' in parent_dir or 'speed' in filename:
            return self._parse_speed_records_csv(csv_path)
        elif 'power_output' in parent_dir or 'power' in filename:
            return self._parse_power_output_csv(csv_path)
        elif 'top_gear' in parent_dir or 'top_gear' in filename:
            return self._parse_top_gear_csv(csv_path)
        elif 'pikes_peak' in parent_dir or 'pikes' in filename:
            return self._parse_pikes_peak_csv(csv_path)
        elif 'goodwood' in parent_dir or 'goodwood' in filename:
            return self._parse_goodwood_csv(csv_path)
        else:
            # Try to auto-detect based on headers
            return self._parse_generic_csv(csv_path)

    def _parse_acceleration_csv(self, csv_path: Path) -> list[dict]:
        """Parse acceleration data CSV."""
        cars = []

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []

            # Determine which type of acceleration data this is
            # based on headers
            is_quarter_mile = any('100' in h.lower() and 'mph' in h.lower() for h in headers)
            is_0_100_kmh = any('100' in h.lower() and 'km' in h.lower() for h in headers)

            for row in reader:
                car_text = row.get('Car', '')
                if not car_text or car_text == 'Car':
                    continue

                manufacturer, model = parse_car_name(car_text)

                # Get year - check multiple possible column names
                year = None
                for year_col in ['Year', 'Model\nyear', 'Model year']:
                    if year_col in row:
                        year = parse_year(row[year_col])
                        if year:
                            break

                propulsion = parse_propulsion(row.get('Propulsion', ''))

                # Parse time
                time_str = row.get('Time', '')
                time_sec = parse_time_to_seconds(time_str)

                if not manufacturer or not time_sec:
                    continue

                car_data = {
                    'manufacturer': manufacturer,
                    'model': model,
                    'year': year,
                    'propulsion': propulsion,
                    'source': 'acceleration'
                }

                # Determine which metric this is
                if is_quarter_mile:
                    car_data['quarter_mile_sec'] = time_sec
                    # Try to extract speed at quarter mile
                    if 'at' in time_str.lower():
                        _, kmh = parse_speed(time_str)
                        # Speed at quarter mile could be stored if needed
                elif is_0_100_kmh:
                    car_data['0_100_kmh_sec'] = time_sec
                else:
                    # Default to 0-60 mph
                    car_data['0_60_mph_sec'] = time_sec

                cars.append(car_data)

        return cars

    def _parse_nurburgring_csv(self, csv_path: Path) -> list[dict]:
        """Parse Nürburgring lap times CSV.

        Handles production car lap times from the main Nurburgring data.
        Skips race cars (F1, F2, GT3, etc.) and non-car data (cycling).
        """
        cars = []

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []

            # Skip files that aren't production car data
            # (e.g., race car records, cycling records)
            if 'Category' in headers or 'Class' in headers or 'Rider' in headers:
                return []

            # Find vehicle column - could be 'Vehicle' or 'Make Model'
            vehicle_col = None
            if 'Vehicle' in headers:
                vehicle_col = 'Vehicle'
            elif 'Make Model' in headers:
                vehicle_col = 'Make Model'

            if not vehicle_col:
                return []

            for row in reader:
                # Get vehicle name
                vehicle = row.get(vehicle_col, '')
                if not vehicle:
                    continue

                manufacturer, model = parse_car_name(vehicle)

                # Skip if not a known manufacturer (likely race car or special)
                if not manufacturer or manufacturer not in MANUFACTURER_COUNTRIES:
                    continue

                # Parse time
                time_str = row.get('Time', '')
                time_sec = parse_time_to_seconds(time_str)

                if not time_sec:
                    continue

                # Get driver and date
                driver = clean_text(row.get('Driver', ''))
                date = clean_text(row.get('Date', ''))

                # Extract year from date or model name
                year = parse_year(date) or parse_year(model)

                car_data = {
                    'manufacturer': manufacturer,
                    'model': model,
                    'year': year,
                    'nurburgring_lap_sec': time_sec,
                    'nurburgring_driver': driver,
                    'nurburgring_date': date,
                    'source': 'nurburgring'
                }

                cars.append(car_data)

        return cars

    def _parse_speed_records_csv(self, csv_path: Path) -> list[dict]:
        """Parse speed records CSV."""
        cars = []

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                # Get make and model
                car_text = row.get('Make and model', '')
                if not car_text:
                    continue

                manufacturer, model = parse_car_name(car_text)

                # Parse top speed
                speed_str = row.get('Top speed', '')
                mph, kmh = parse_speed(speed_str)

                if not manufacturer or (not mph and not kmh):
                    continue

                year = parse_year(row.get('Year', ''))
                engine = clean_text(row.get('Engine', ''))

                car_data = {
                    'manufacturer': manufacturer,
                    'model': model,
                    'year': year,
                    'top_speed_mph': mph,
                    'top_speed_kmh': kmh,
                    'engine': engine,
                    'source': 'speed_records'
                }

                cars.append(car_data)

        return cars

    def _parse_power_output_csv(self, csv_path: Path) -> list[dict]:
        """Parse power output CSV."""
        cars = []

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                vehicle = row.get('Vehicle', '')
                if not vehicle:
                    continue

                manufacturer, model = parse_car_name(vehicle)

                # Parse power
                power_str = row.get('Power', '')
                hp, kw = parse_power(power_str)

                if not manufacturer or (not hp and not kw):
                    continue

                year = parse_year(row.get('Year', ''))
                propulsion_type = row.get('Type', '')
                propulsion = parse_propulsion(propulsion_type)

                car_data = {
                    'manufacturer': manufacturer,
                    'model': model,
                    'year': year,
                    'power_hp': hp,
                    'power_kw': kw,
                    'propulsion': propulsion,
                    'source': 'power_output'
                }

                cars.append(car_data)

        return cars

    def _parse_top_gear_csv(self, csv_path: Path) -> list[dict]:
        """Parse Top Gear lap times CSV."""
        cars = []

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                vehicle = row.get('Vehicle', '')
                if not vehicle:
                    continue

                manufacturer, model = parse_car_name(vehicle)

                # Parse time
                time_str = row.get('Time', '')
                time_sec = parse_time_to_seconds(time_str)

                if not manufacturer or not time_sec:
                    continue

                episode = clean_text(row.get('Episode', ''))

                car_data = {
                    'manufacturer': manufacturer,
                    'model': model,
                    'top_gear_lap_sec': time_sec,
                    'top_gear_episode': episode,
                    'source': 'top_gear'
                }

                cars.append(car_data)

        return cars

    def _parse_pikes_peak_csv(self, csv_path: Path) -> list[dict]:
        """Parse Pikes Peak data CSV.

        Note: Pikes Peak data is mostly historical race results with limited
        performance data. We skip this data as it doesn't contain useful
        performance metrics like lap times, acceleration, etc.
        """
        # Skip Pikes Peak data - it's race history, not car performance specs
        return []

    def _parse_goodwood_csv(self, csv_path: Path) -> list[dict]:
        """Parse Goodwood Festival of Speed CSV."""
        # This data is mostly about event displays, not performance data
        # Return empty for now as it doesn't contain useful performance metrics
        return []

    def _parse_generic_csv(self, csv_path: Path) -> list[dict]:
        """Try to parse a generic CSV file with auto-detection.

        Only parses files that appear to contain car performance data.
        """
        cars = []

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []

            # Skip files that don't look like car performance data
            # Check for performance-related columns
            has_performance_data = any(
                any(k in h.lower() for k in ['time', 'speed', 'power', 'hp', 'kw', 'mph', 'km/h'])
                for h in headers
            )

            # Must have a vehicle/car column and some performance data
            car_col = next((h for h in headers if any(k in h.lower() for k in ['car', 'vehicle'])), None)

            if not car_col or not has_performance_data:
                return []

            year_col = next((h for h in headers if 'year' in h.lower()), None)
            time_col = next((h for h in headers if 'time' in h.lower()), None)
            speed_col = next((h for h in headers if 'speed' in h.lower()), None)
            power_col = next((h for h in headers if 'power' in h.lower()), None)

            for row in reader:
                car_text = row.get(car_col, '')
                if not car_text:
                    continue

                manufacturer, model = parse_car_name(car_text)

                # Must be a known manufacturer or have valid performance data
                if not manufacturer or manufacturer not in MANUFACTURER_COUNTRIES:
                    continue

                # Ensure we have some performance data for this row
                has_data = False

                car_data = {
                    'manufacturer': manufacturer,
                    'model': model,
                    'source': 'wikipedia'
                }

                if year_col:
                    car_data['year'] = parse_year(row.get(year_col, ''))

                if time_col:
                    time_sec = parse_time_to_seconds(row.get(time_col, ''))
                    if time_sec:
                        has_data = True

                if speed_col:
                    mph, kmh = parse_speed(row.get(speed_col, ''))
                    if mph:
                        car_data['top_speed_mph'] = mph
                        has_data = True
                    if kmh:
                        car_data['top_speed_kmh'] = kmh
                        has_data = True

                if power_col:
                    hp, kw = parse_power(row.get(power_col, ''))
                    if hp:
                        car_data['power_hp'] = hp
                        has_data = True
                    if kw:
                        car_data['power_kw'] = kw
                        has_data = True

                if has_data:
                    cars.append(car_data)

        return cars


def normalize_model_name(model: str) -> str:
    """Normalize model name for key matching."""
    model = model.lower().strip()
    # Remove year from model if present in parentheses like (2002) or (2015)
    model = re.sub(r'\(\d{4}\)', '', model).strip()
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
    """Merge new data into existing data, updating or adding entries.

    Uses two-phase matching:
    1. First by (year, manufacturer, model) for exact matches
    2. Then by (manufacturer, model) for entries where one has no year
    """
    # Create lookups - one with year, one without
    lookup_with_year = {}  # (year, manufacturer, model) -> car
    lookup_no_year = {}    # (manufacturer, model) -> car

    def add_to_lookups(car: dict):
        """Add car to both lookup dictionaries."""
        key_with_year = create_car_key(car, include_year=True)
        key_no_year = create_car_key(car, include_year=False)

        if key_with_year not in lookup_with_year:
            lookup_with_year[key_with_year] = car
        else:
            _merge_into(lookup_with_year[key_with_year], car)

        # Update no-year lookup to point to same car
        if key_no_year not in lookup_no_year:
            lookup_no_year[key_no_year] = lookup_with_year[key_with_year]
        else:
            # If no-year key already exists, merge if the existing entry has no year
            existing = lookup_no_year[key_no_year]
            if not existing.get('year') or not car.get('year'):
                _merge_into(existing, car)

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
        # Then try matching by model only if this or existing entry has no year
        elif key_no_year in lookup_no_year:
            existing = lookup_no_year[key_no_year]
            existing_year = existing.get('year')
            new_year = car.get('year')

            # Only merge if one entry has no year (allows filling in missing year)
            if not existing_year or not new_year:
                _merge_into(existing, car)
                # If new entry provides year, update the lookup
                if new_year and not existing_year:
                    existing['year'] = new_year
            else:
                # Both have years but different - add as new entry
                new_car = car.copy()
                source = new_car.pop('source', '')
                new_car['sources'] = source
                new_car['country'] = get_country_for_manufacturer(new_car.get('manufacturer', ''))
                lookup_with_year[key_with_year] = new_car
        else:
            # Add new entry
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
    # Fields to merge (don't overwrite if existing has value)
    merge_fields = [
        'year', 'propulsion', '0_60_mph_sec', '0_100_kmh_sec', '0_100_mph_sec',
        '0_200_kmh_sec', 'quarter_mile_sec', 'top_speed_mph', 'top_speed_kmh',
        'power_hp', 'power_kw', 'torque', 'engine', 'nurburgring_lap_sec',
        'nurburgring_date', 'nurburgring_driver', 'top_gear_lap_sec',
        'top_gear_episode'
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

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)


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

    # Parse Wikipedia CSV files
    parser = WikipediaCSVParser(base_path)
    new_data = parser.parse_all_csv_files()
    print(f"\nParsed {len(new_data)} entries from Wikipedia CSVs")

    # Merge data
    merged_data = merge_car_data(existing_data, new_data)
    print(f"\nMerged to {len(merged_data)} unique car entries")

    # Define output columns
    columns = [
        'manufacturer', 'country', 'model', 'year', 'propulsion',
        '0_60_mph_sec', '0_100_kmh_sec', '0_100_mph_sec', '0_200_kmh_sec',
        'quarter_mile_sec', 'top_speed_mph', 'top_speed_kmh',
        'power_hp', 'power_kw', 'torque', 'engine',
        'nurburgring_lap_sec', 'nurburgring_date', 'nurburgring_driver',
        'top_gear_lap_sec', 'top_gear_episode', 'sources'
    ]

    # Save merged data
    save_data(csv_path, merged_data, columns)
    print(f"\nSaved {len(merged_data)} cars to {csv_path}")

    # Print summary
    print("\n=== Summary ===")
    print(f"Total cars: {len(merged_data)}")
    manufacturers = set(c.get('manufacturer', '') for c in merged_data)
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


if __name__ == '__main__':
    main()
