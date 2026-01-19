#!/usr/bin/env python3
"""
Parse Wikipedia HTML files and extract car performance data to update CSV.
"""

import csv
import re
from pathlib import Path
from bs4 import BeautifulSoup

# Manufacturer to country mapping
MANUFACTURER_COUNTRIES = {
    "AC": "GB", "Acura": "JP", "Alfa Romeo": "IT", "Alpine": "FR", "AMC": "US",
    "Ariel": "GB", "Aston Martin": "GB", "Audi": "DE", "Bentley": "GB", "BMW": "DE",
    "Bugatti": "FR", "Buick": "US", "BYD": "CN", "Cadillac": "US", "Callaway": "US",
    "Caterham": "GB", "Chevrolet": "US", "Chrysler": "US", "Citroën": "FR", "Cupra": "ES",
    "Czinger": "US", "Dacia": "FR", "Datsun": "JP", "De Tomaso": "IT", "Dodge": "US",
    "Donkervoort": "NL", "Ferrari": "IT", "Fiat": "IT", "Fisker": "US", "Ford": "US",
    "Genesis": "KR", "Geely": "CN", "Ginetta": "GB", "GMC": "US", "Gordon Murray": "GB",
    "Hennessey": "US", "Honda": "JP", "Hummer": "US", "Hyundai": "KR", "Infiniti": "JP",
    "Iso": "IT", "Italdesign": "IT", "Jaguar": "GB", "Jeep": "US", "Jensen": "GB",
    "Karma": "US", "Kia": "KR", "Koenigsegg": "SE", "KTM": "AT", "Lada": "RU",
    "Lamborghini": "IT", "Lancia": "IT", "Land Rover": "GB", "Lexus": "JP", "Lister": "GB",
    "Lotus": "GB", "Lucid": "US", "Maserati": "IT", "Mazda": "JP", "McLaren": "GB",
    "Mercedes-AMG": "DE", "Mercedes-Benz": "DE", "Mercury": "US", "MG": "GB", "Mini": "GB",
    "Mitsubishi": "JP", "Mosler": "US", "Napier": "GB", "NIO": "CN", "Nissan": "JP",
    "Noble": "GB", "Oldsmobile": "US", "Opel": "DE", "Packard": "US", "Pagani": "IT",
    "Peugeot": "FR", "Plymouth": "US", "Polestar": "SE", "Pontiac": "US", "Porsche": "DE",
    "Radical": "GB", "Ram": "US", "Range Rover": "GB", "Renault": "FR", "Rimac": "HR",
    "Rivian": "US", "Rolls-Royce": "GB", "Ruf": "DE", "Saab": "SE", "Saleen": "US",
    "SEAT": "ES", "Shelby": "US", "Singer": "US", "Smart": "DE", "Spyker": "NL",
    "SSC": "US", "Subaru": "JP", "Sunbeam": "GB", "Suzuki": "JP", "Tesla": "US",
    "Toyota": "JP", "Triumph": "GB", "TVR": "GB", "Ultima": "GB", "Vauxhall": "GB",
    "Vector": "US", "Venturi": "FR", "Volkswagen": "DE", "Volvo": "SE", "W Motors": "AE",
    "Wiesmann": "DE", "Xiaomi": "CN", "Yangwang": "CN", "Zenvo": "DK",
}

def clean_text(text):
    """Clean text by removing footnotes, extra whitespace, etc."""
    if not text:
        return ""
    # Remove footnote references like [1], [a], [iv], etc.
    text = re.sub(r'\[[\w\d,\s]+\]', '', text)
    # Remove citation needed, etc.
    text = re.sub(r'\[citation needed\]', '', text, flags=re.IGNORECASE)
    # Clean whitespace
    text = ' '.join(text.split())
    return text.strip()

def parse_car_name(car_text):
    """Parse car name into manufacturer and model."""
    car_text = clean_text(car_text)

    # Try to match known manufacturers
    for manufacturer in sorted(MANUFACTURER_COUNTRIES.keys(), key=len, reverse=True):
        if car_text.startswith(manufacturer):
            model = car_text[len(manufacturer):].strip()
            # Remove leading separators
            model = re.sub(r'^[\s\-/]+', '', model)
            return manufacturer, model

    # Fallback: split on first space
    parts = car_text.split(' ', 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return car_text, ""

def parse_time_to_seconds(time_str):
    """Parse time string to seconds (float)."""
    if not time_str:
        return None

    time_str = clean_text(time_str)

    # Handle mm:ss.sss format
    match = re.search(r'(\d+):(\d+(?:\.\d+)?)', time_str)
    if match:
        minutes = int(match.group(1))
        seconds = float(match.group(2))
        return minutes * 60 + seconds

    # Handle just seconds
    match = re.search(r'(\d+(?:\.\d+)?)\s*(?:s|sec|seconds?)?', time_str)
    if match:
        return float(match.group(1))

    return None

def parse_speed(speed_str):
    """Parse speed string to mph and km/h."""
    if not speed_str:
        return None, None

    speed_str = clean_text(speed_str)
    mph = None
    kmh = None

    # Try to find mph
    match = re.search(r'(\d+(?:\.\d+)?)\s*(?:mph|mi/h)', speed_str, re.IGNORECASE)
    if match:
        mph = float(match.group(1))

    # Try to find km/h
    match = re.search(r'(\d+(?:\.\d+)?)\s*(?:km/h|kph|kmh)', speed_str, re.IGNORECASE)
    if match:
        kmh = float(match.group(1))

    # If only one found, calculate the other
    if mph and not kmh:
        kmh = mph * 1.60934
    elif kmh and not mph:
        mph = kmh / 1.60934

    return mph, kmh

def parse_power(power_str):
    """Parse power string to hp and kW."""
    if not power_str:
        return None, None

    power_str = clean_text(power_str)
    hp = None
    kw = None

    # Try to find hp/bhp/PS
    match = re.search(r'(\d+(?:,\d+)?(?:\.\d+)?)\s*(?:hp|bhp|PS)', power_str, re.IGNORECASE)
    if match:
        hp = float(match.group(1).replace(',', ''))

    # Try to find kW
    match = re.search(r'(\d+(?:,\d+)?(?:\.\d+)?)\s*kW', power_str, re.IGNORECASE)
    if match:
        kw = float(match.group(1).replace(',', ''))

    # If only one found, calculate the other
    if hp and not kw:
        kw = hp * 0.7457
    elif kw and not hp:
        hp = kw / 0.7457

    return hp, kw

def parse_year(year_str):
    """Parse year from string."""
    if not year_str:
        return None

    year_str = clean_text(year_str)
    match = re.search(r'(19\d{2}|20\d{2})', year_str)
    if match:
        return match.group(1)
    return None

def parse_acceleration_html(html_path):
    """Parse the acceleration Wikipedia page."""
    cars = []

    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    # Find section headings to determine which table is which
    current_section = None

    for element in soup.find_all(['h2', 'table']):
        if element.name == 'h2':
            heading_text = element.get_text(strip=True).lower()
            if '0–60' in heading_text or '0-60' in heading_text:
                current_section = '0_60_mph'
            elif '1⁄4' in heading_text or 'quarter' in heading_text or '1/4' in heading_text:
                current_section = 'quarter_mile'
            elif '0–100' in heading_text or '0-100' in heading_text:
                current_section = '0_100_kmh'
            else:
                current_section = None
            continue

        if element.name == 'table' and 'wikitable' in element.get('class', []) and current_section:
            rows = element.find_all('tr')
            if not rows:
                continue

            # Get headers
            header_row = rows[0]
            headers = [clean_text(th.get_text()) for th in header_row.find_all(['th', 'td'])]

            # Find column indices
            car_idx = next((i for i, h in enumerate(headers) if 'car' in h.lower()), None)
            year_idx = next((i for i, h in enumerate(headers) if 'year' in h.lower()), None)
            propulsion_idx = next((i for i, h in enumerate(headers) if 'propulsion' in h.lower()), None)
            time_idx = next((i for i, h in enumerate(headers) if 'time' in h.lower()), None)

            if car_idx is None or time_idx is None:
                continue

            for row in rows[1:]:
                cells = row.find_all(['td', 'th'])
                if len(cells) <= max(car_idx, time_idx):
                    continue

                car_text = cells[car_idx].get_text()
                manufacturer, model = parse_car_name(car_text)

                year = None
                if year_idx is not None and len(cells) > year_idx:
                    year = parse_year(cells[year_idx].get_text())

                propulsion = ""
                if propulsion_idx is not None and len(cells) > propulsion_idx:
                    propulsion = clean_text(cells[propulsion_idx].get_text())

                time_text = cells[time_idx].get_text()
                time_sec = parse_time_to_seconds(time_text)

                if manufacturer and time_sec:
                    car_data = {
                        'manufacturer': manufacturer,
                        'model': model,
                        'year': year,
                        'propulsion': propulsion,
                        'source': 'acceleration'
                    }

                    # Assign to correct field based on section
                    if current_section == '0_60_mph':
                        car_data['0_60_mph_sec'] = time_sec
                    elif current_section == 'quarter_mile':
                        car_data['quarter_mile_sec'] = time_sec
                    elif current_section == '0_100_kmh':
                        car_data['0_100_kmh_sec'] = time_sec

                    cars.append(car_data)

    return cars

def parse_speed_records_html(html_path):
    """Parse the speed records Wikipedia page."""
    cars = []

    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    tables = soup.find_all('table', class_='wikitable')

    for table in tables:
        rows = table.find_all('tr')
        if not rows:
            continue

        header_row = rows[0]
        headers = [clean_text(th.get_text()) for th in header_row.find_all(['th', 'td'])]

        car_idx = next((i for i, h in enumerate(headers) if 'make' in h.lower() or 'model' in h.lower()), None)
        year_idx = next((i for i, h in enumerate(headers) if 'year' in h.lower()), None)
        speed_idx = next((i for i, h in enumerate(headers) if 'speed' in h.lower()), None)
        engine_idx = next((i for i, h in enumerate(headers) if 'engine' in h.lower()), None)

        if car_idx is None or speed_idx is None:
            continue

        for row in rows[1:]:
            cells = row.find_all(['td', 'th'])
            if len(cells) <= max(car_idx, speed_idx):
                continue

            car_text = cells[car_idx].get_text()
            manufacturer, model = parse_car_name(car_text)

            year = None
            if year_idx is not None and len(cells) > year_idx:
                year = parse_year(cells[year_idx].get_text())

            speed_text = cells[speed_idx].get_text()
            mph, kmh = parse_speed(speed_text)

            engine = ""
            if engine_idx is not None and len(cells) > engine_idx:
                engine = clean_text(cells[engine_idx].get_text())

            if manufacturer and (mph or kmh):
                cars.append({
                    'manufacturer': manufacturer,
                    'model': model,
                    'year': year,
                    'top_speed_mph': mph,
                    'top_speed_kmh': kmh,
                    'engine': engine,
                    'source': 'speed_records'
                })

    return cars

def parse_power_output_html(html_path):
    """Parse the power output Wikipedia page."""
    cars = []

    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    tables = soup.find_all('table', class_='wikitable')

    for table in tables:
        rows = table.find_all('tr')
        if not rows:
            continue

        header_row = rows[0]
        headers = [clean_text(th.get_text()) for th in header_row.find_all(['th', 'td'])]

        vehicle_idx = next((i for i, h in enumerate(headers) if 'vehicle' in h.lower()), None)
        year_idx = next((i for i, h in enumerate(headers) if 'year' in h.lower()), None)
        power_idx = next((i for i, h in enumerate(headers) if 'power' in h.lower()), None)

        if vehicle_idx is None or power_idx is None:
            continue

        for row in rows[1:]:
            cells = row.find_all(['td', 'th'])
            if len(cells) <= max(vehicle_idx, power_idx):
                continue

            car_text = cells[vehicle_idx].get_text()
            manufacturer, model = parse_car_name(car_text)

            year = None
            if year_idx is not None and len(cells) > year_idx:
                year = parse_year(cells[year_idx].get_text())

            power_text = cells[power_idx].get_text()
            hp, kw = parse_power(power_text)

            if manufacturer and (hp or kw):
                cars.append({
                    'manufacturer': manufacturer,
                    'model': model,
                    'year': year,
                    'power_hp': hp,
                    'power_kw': kw,
                    'source': 'power_output'
                })

    return cars

def parse_nurburgring_html(html_path):
    """Parse the Nürburgring lap times Wikipedia page."""
    cars = []

    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    tables = soup.find_all('table', class_='wikitable')

    for table in tables:
        rows = table.find_all('tr')
        if not rows:
            continue

        header_row = rows[0]
        headers = [clean_text(th.get_text()) for th in header_row.find_all(['th', 'td'])]

        # Find column indices
        time_idx = next((i for i, h in enumerate(headers) if 'time' in h.lower()), None)
        car_idx = next((i for i, h in enumerate(headers) if 'vehicle' in h.lower() or 'make' in h.lower() or 'model' in h.lower()), None)
        driver_idx = next((i for i, h in enumerate(headers) if 'driver' in h.lower()), None)
        date_idx = next((i for i, h in enumerate(headers) if 'date' in h.lower()), None)

        if time_idx is None or car_idx is None:
            continue

        for row in rows[1:]:
            cells = row.find_all(['td', 'th'])
            if len(cells) <= max(time_idx, car_idx):
                continue

            car_text = cells[car_idx].get_text()
            manufacturer, model = parse_car_name(car_text)

            time_text = cells[time_idx].get_text()
            time_sec = parse_time_to_seconds(time_text)

            driver = ""
            if driver_idx is not None and len(cells) > driver_idx:
                driver = clean_text(cells[driver_idx].get_text())

            date = ""
            if date_idx is not None and len(cells) > date_idx:
                date = clean_text(cells[date_idx].get_text())

            if manufacturer and time_sec:
                cars.append({
                    'manufacturer': manufacturer,
                    'model': model,
                    'nurburgring_lap_sec': time_sec,
                    'nurburgring_driver': driver,
                    'nurburgring_date': date,
                    'source': 'nurburgring'
                })

    return cars

def parse_top_gear_html(html_path):
    """Parse the Top Gear lap times Wikipedia page."""
    cars = []

    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    tables = soup.find_all('table', class_='wikitable')

    for table in tables:
        rows = table.find_all('tr')
        if not rows:
            continue

        header_row = rows[0]
        headers = [clean_text(th.get_text()) for th in header_row.find_all(['th', 'td'])]

        time_idx = next((i for i, h in enumerate(headers) if 'time' in h.lower()), None)
        vehicle_idx = next((i for i, h in enumerate(headers) if 'vehicle' in h.lower()), None)
        episode_idx = next((i for i, h in enumerate(headers) if 'episode' in h.lower()), None)

        if time_idx is None or vehicle_idx is None:
            continue

        for row in rows[1:]:
            cells = row.find_all(['td', 'th'])
            if len(cells) <= max(time_idx, vehicle_idx):
                continue

            car_text = cells[vehicle_idx].get_text()
            manufacturer, model = parse_car_name(car_text)

            time_text = cells[time_idx].get_text()
            time_sec = parse_time_to_seconds(time_text)

            episode = ""
            if episode_idx is not None and len(cells) > episode_idx:
                episode = clean_text(cells[episode_idx].get_text())

            if manufacturer and time_sec:
                cars.append({
                    'manufacturer': manufacturer,
                    'model': model,
                    'top_gear_lap_sec': time_sec,
                    'top_gear_episode': episode,
                    'source': 'top_gear'
                })

    return cars

def merge_car_data(existing_data, new_data):
    """Merge new data into existing data, updating or adding entries."""
    # Create a lookup by manufacturer+model
    lookup = {}
    for car in existing_data:
        key = (car.get('manufacturer', ''), car.get('model', ''))
        if key not in lookup:
            lookup[key] = car

    # Merge new data
    for car in new_data:
        key = (car.get('manufacturer', ''), car.get('model', ''))

        if key in lookup:
            # Update existing entry with new data (don't overwrite existing values)
            existing = lookup[key]
            for field, value in car.items():
                if field != 'source' and value and not existing.get(field):
                    existing[field] = value
            # Append source
            existing_sources = existing.get('sources', '')
            new_source = car.get('source', '')
            if new_source and new_source not in existing_sources:
                existing['sources'] = f"{existing_sources},{new_source}" if existing_sources else new_source
        else:
            # Add new entry
            car['sources'] = car.pop('source', '')
            # Add country
            manufacturer = car.get('manufacturer', '')
            car['country'] = MANUFACTURER_COUNTRIES.get(manufacturer, '')
            lookup[key] = car

    return list(lookup.values())

def main():
    base_path = Path(__file__).parent.parent / 'public' / 'data'
    html_path = base_path / 'wikipedia-articles-html'
    csv_path = base_path / 'car-performance-data.csv'

    # Read existing CSV
    existing_data = []
    if csv_path.exists():
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            existing_data = list(reader)

    print(f"Existing data: {len(existing_data)} cars")

    # Parse all HTML files
    all_new_data = []

    # Acceleration data
    accel_path = html_path / 'List of fastest production cars by acceleration - Wikipedia.html'
    if accel_path.exists():
        accel_data = parse_acceleration_html(accel_path)
        print(f"Parsed acceleration: {len(accel_data)} entries")
        all_new_data.extend(accel_data)

    # Speed records
    speed_path = html_path / 'List of production car speed records - Wikipedia.html'
    if speed_path.exists():
        speed_data = parse_speed_records_html(speed_path)
        print(f"Parsed speed records: {len(speed_data)} entries")
        all_new_data.extend(speed_data)

    # Power output
    power_path = html_path / 'List of production cars by power output - Wikipedia.html'
    if power_path.exists():
        power_data = parse_power_output_html(power_path)
        print(f"Parsed power output: {len(power_data)} entries")
        all_new_data.extend(power_data)

    # Nürburgring lap times
    nurburgring_path = html_path / 'List of Nürburgring Nordschleife lap times - Wikipedia.html'
    if nurburgring_path.exists():
        nurburgring_data = parse_nurburgring_html(nurburgring_path)
        print(f"Parsed Nürburgring: {len(nurburgring_data)} entries")
        all_new_data.extend(nurburgring_data)

    # Top Gear lap times
    topgear_path = html_path / 'List of Top Gear test track Power Lap times - Wikipedia.html'
    if topgear_path.exists():
        topgear_data = parse_top_gear_html(topgear_path)
        print(f"Parsed Top Gear: {len(topgear_data)} entries")
        all_new_data.extend(topgear_data)

    # Merge data
    merged_data = merge_car_data(existing_data, all_new_data)
    print(f"Merged data: {len(merged_data)} cars")

    # Define CSV columns
    columns = [
        'manufacturer', 'country', 'model', 'year', 'propulsion',
        '0_60_mph_sec', '0_100_kmh_sec', '0_100_mph_sec', '0_200_kmh_sec',
        'quarter_mile_sec', 'top_speed_mph', 'top_speed_kmh',
        'power_hp', 'power_kw', 'torque', 'engine',
        'nurburgring_lap_sec', 'nurburgring_date', 'nurburgring_driver',
        'top_gear_lap_sec', 'top_gear_episode', 'sources'
    ]

    # Write merged data to CSV
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(merged_data)

    print(f"Wrote {len(merged_data)} cars to {csv_path}")

if __name__ == '__main__':
    main()
