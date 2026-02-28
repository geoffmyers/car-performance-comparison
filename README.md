---
title: Car Performance Database
created: 2026-01-18
modified: 2026-01-19
description: "A comprehensive web application for comparing car performance data across 60,000+ vehicles. Search, filter, and sort by acceleration times, top speeds, lap times, power output, and more."
tags: [nextjs, readme]
---

# Car Performance Database

A comprehensive web application for comparing car performance data across 60,000+ vehicles. Search, filter, and sort by acceleration times, top speeds, lap times, power output, and more.

## Features

- **60,000+ Vehicles**: Data aggregated from multiple authoritative sources
- **Performance Metrics**: 0-60 mph, quarter mile, top speed, Nurburgring lap times, and more
- **Advanced Filtering**: Filter by manufacturer, country, year range, and propulsion type
- **Full-Text Search**: Search across manufacturer and model names
- **Server-Side Pagination**: Fast loading with SQLite-backed API
- **Dark Mode Support**: Automatic theme detection
- **Responsive Design**: Works on desktop and mobile

## Tech Stack

- **Frontend**: Next.js 16, React 19, TanStack Table v8
- **Styling**: Tailwind CSS 4
- **Database**: SQLite with better-sqlite3
- **Validation**: Zod
- **ETL Pipeline**: Python 3.11+

## Data Sources

| Source | Description | Priority |
|--------|-------------|----------|
| Car and Driver | Instrumented test data (0-60, quarter mile, skidpad) | High |
| Car and Driver Lightning Lap | VIR track lap times (2006-2025) | High |
| Wikipedia Nurburgring | Nordschleife lap times | Medium |
| Wikipedia Top Gear | Test track Power Lap times | Medium |
| Wikipedia Records | Acceleration and speed records | Medium |
| Autoevolution | Comprehensive vehicle specifications | Medium |
| EPA Fuel Economy | Official vehicle specifications | Low |
| Kaggle | Community-contributed specifications (1945-2020) | Low |

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.11+ (for ETL pipeline)
- npm or yarn

### Installation

```bash
# Install Node.js dependencies
npm install

# Install Python dependencies (for ETL)
pip install pyyaml beautifulsoup4
```

### Development

```bash
# Start the development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the application.

### Building for Production

```bash
# Build the Next.js application
npm run build

# Start the production server
npm start
```

## Project Structure

```
car-performance-comparison/
├── src/
│   ├── app/                    # Next.js app router pages
│   │   ├── api/cars/           # API routes for car data
│   │   └── page.tsx            # Main application page
│   ├── components/             # React components
│   │   ├── DataTable.tsx       # Main data table with TanStack
│   │   ├── FilterPanel.tsx     # Filter controls
│   │   └── Pagination.tsx      # Pagination controls
│   ├── hooks/                  # Custom React hooks
│   │   └── useCarsApi.ts       # API data fetching hook
│   ├── lib/                    # Utilities
│   │   ├── db.ts               # SQLite database service
│   │   └── schemas.ts          # Zod validation schemas
│   └── types/                  # TypeScript types
│       └── car.ts              # Auto-generated car data types
├── etl/                        # Python ETL pipeline
│   ├── cli.py                  # CLI entry point
│   ├── config/
│   │   ├── schema.yaml         # Data field definitions
│   │   └── sources.yaml        # Data source configuration
│   ├── core/
│   │   ├── converters.py       # Value parsing/conversion
│   │   ├── enricher.py         # Data enrichment
│   │   ├── manufacturers.py    # Manufacturer normalization
│   │   ├── merger.py           # Multi-source data merging
│   │   └── schema.py           # Schema loading
│   ├── outputs/
│   │   ├── csv_writer.py       # CSV output
│   │   ├── sqlite_writer.py    # SQLite output
│   │   ├── typescript_gen.py   # TypeScript type generation
│   │   └── quality_report.py   # Data quality reporting
│   ├── parsers/                # Source-specific parsers
│   │   ├── base.py             # Base parser class
│   │   ├── caranddriver/       # Car and Driver parsers
│   │   ├── wikipedia/          # Wikipedia parsers
│   │   ├── fueleconomy/        # EPA data parser
│   │   ├── kaggle/             # Kaggle dataset parser
│   │   └── github/             # Autoevolution parser
│   └── validators/             # Data validation
└── public/data/                # Data files
    ├── car-performance-data.db # SQLite database
    └── car-performance-data.csv # CSV export
```

## ETL Pipeline

The ETL pipeline aggregates data from multiple sources into a unified database.

### Running the ETL

```bash
# Run full ETL pipeline
python -m etl.cli run

# Run with verbose output
python -m etl.cli run -v

# Generate only SQLite (skip CSV)
python -m etl.cli run --output-format sqlite

# Show pipeline status
python -m etl.cli status
```

### Adding New Data Sources

1. Create a parser in `etl/parsers/<source>/`
2. Inherit from `BaseParser` in `etl/parsers/base.py`
3. Add source configuration to `etl/config/sources.yaml`
4. Register the parser in `etl/parsers/registry.py`

## API Reference

### GET /api/cars

Fetch paginated car data with optional filtering.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| page | number | 1 | Page number |
| pageSize | number | 50 | Records per page (max 100) |
| sortBy | string | - | Column to sort by |
| sortOrder | asc/desc | asc | Sort direction |
| manufacturer | string | - | Filter by manufacturer |
| country | string | - | Filter by country code |
| yearMin | number | - | Minimum year |
| yearMax | number | - | Maximum year |
| search | string | - | Full-text search |

**Response:**
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "pageSize": 50,
    "totalCount": 60997,
    "totalPages": 1220
  }
}
```

### GET /api/cars/meta

Fetch filter metadata (manufacturers, countries, year range).

**Response:**
```json
{
  "manufacturers": ["Acura", "Alfa Romeo", ...],
  "countries": [{"value": "US", "label": "United States"}, ...],
  "yearRange": {"min": 1886, "max": 2025},
  "totalCount": 60997,
  "sources": [{"value": "Car and Driver", ...}]
}
```

## Performance Metrics

The database includes the following performance metrics:

| Metric | Unit | Description |
|--------|------|-------------|
| 0-60 mph | seconds | Acceleration time |
| 0-100 km/h | seconds | Acceleration time (metric) |
| 0-100 mph | seconds | Acceleration time |
| Quarter Mile | seconds | 1/4 mile time |
| Top Speed | mph/km/h | Maximum velocity |
| Nurburgring Lap | seconds | Nordschleife lap time |
| Top Gear Lap | seconds | TG test track time |
| Lightning Lap | seconds | VIR lap time |
| Power | hp/kW | Engine output |
| Torque | lb-ft/Nm | Torque output |
| Curb Weight | lbs/kg | Vehicle weight |

## License

Private project - not for distribution.
