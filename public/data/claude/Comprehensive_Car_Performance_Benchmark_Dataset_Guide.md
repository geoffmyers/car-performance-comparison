---
title: Comprehensive Car Performance Benchmark Dataset Guide
created: 2026-01-19
modified: 2026-01-19
description: "No single comprehensive, downloadable database exists for all performance metrics, but this guide maps the fragmented landscape of automotive testing data. Major publications protect their..."
tags: [nextjs]
---

# Comprehensive Car Performance Benchmark Dataset Guide

**No single comprehensive, downloadable database exists for all performance metrics**, but this guide maps the fragmented landscape of automotive testing data. Major publications protect their proprietary test data, making bulk access difficult. However, substantial resources exist across GitHub repositories, data science platforms, government sources, and international archives—enough to construct meaningful research datasets.

The most actionable paths for comprehensive data are: scraping FastestLaps.com using the LapMiner tool for lap times; downloading the free **ilyasozkurt/automobile-models-and-specs** GitHub dataset for 0-60 times; accessing **EPA FuelEconomy.gov** for official specs; and purchasing commercial databases like Auto-Data.net API or CarsDataset.com for deeper performance metrics including braking and acceleration data.

---

## US automotive publication databases offer web access but no downloads

### Car and Driver
| Attribute | Details |
|-----------|---------|
| **Primary Database** | https://www.caranddriver.com/compare/ |
| **Performance Metrics** | 113+ data points: 0-60 mph, quarter-mile, 70-0 braking, skidpad g-force, top speed |
| **Time Period** | 1956–present (~400 vehicles tested annually) |
| **Format** | Web interface only—no CSV/API available |
| **Cost** | Free comparison tool; some content behind paywall |

**Lightning Lap Database**: https://www.caranddriver.com/features/a23319884/lightning-lap-times-historical-data/ contains **345+ vehicles** tested at Virginia International Raceway (2006–2025), organized by price class (LL1–LL5). Times displayed as text; no bulk download.

### Motor Trend
| Attribute | Details |
|-----------|---------|
| **Primary Database** | https://www.motortrend.com/car-reviews/first-tests |
| **Performance Metrics** | 0-60 mph (with 1-foot rollout), quarter-mile + trap speed, 60-0 and 100-0 braking, Figure-8 handling test, skidpad g, slalom speeds |
| **Time Period** | October 1949–present (75+ years) |
| **Format** | Individual reviews only—no bulk export |
| **Unique Asset** | Motor Trend invented the Figure-8 test; FastestLaps.com aggregates **2,138** Figure-8 lap times at https://fastestlaps.com/tracks/motortrend-figure-8 |

### Road & Track
| Attribute | Details |
|-----------|---------|
| **Historical Archive** | Stanford REVS Digital Library: https://searchworks.stanford.edu/view/10103243 |
| **Content** | Complete magazine archives from **1947–2012** including original road test data sheets, performance charts, methodology notes |
| **Access** | In-person at Stanford Libraries Special Collections; 36-hour advance request required |
| **Format** | Physical archive with partial digitization |

A legacy Data Panel Archive (circa 2011–2014) that offered free downloadable data sheets for 400+ vehicles is no longer accessible.

### MotorWeek (PBS)
| Attribute | Details |
|-----------|---------|
| **Archive** | https://motorweek.org/episode/ |
| **Time Period** | October 1981–present (1,929 episodes across 45 seasons) |
| **Format** | Video only—no structured performance database |
| **Note** | Episode archive searchable at American Archive of Public Broadcasting |

---

## GitHub repositories provide the best free structured datasets

### ilyasozkurt/automobile-models-and-specs ⭐ Recommended
| Attribute | Details |
|-----------|---------|
| **URL** | https://github.com/ilyasozkurt/automobile-models-and-specs |
| **Records** | 124 brands, 7,207 models, ~30,066 engine variants |
| **Performance Metrics** | **0-62 mph times**, top speed, CO₂ emissions, fuel economy |
| **Other Data** | Engine specs, brakes, tire size, dimensions, drag coefficient |
| **Format** | CSV, JSON, SQL, XML (zipped) |
| **License** | Open repository (229 stars) |
| **Last Update** | October 2024 |
| **Source** | Scraped from autoevolution.com; includes PHP scraper |

### vbalagovic/cars-dataset
| Attribute | Details |
|-----------|---------|
| **URL** | https://github.com/vbalagovic/cars-dataset |
| **Records** | 12,000+ variants from 100+ brands (1990–2025) |
| **Performance Metrics** | 0-100 km/h times, top speed, emissions |
| **Format** | CSV, JSON, SQL |
| **License** | Sample free; full dataset requires purchase via Stripe |

### Endless077/LapMiner ⭐ For Track Data
| Attribute | Details |
|-----------|---------|
| **URL** | https://github.com/Endless077/LapMiner |
| **Purpose** | Scraping tool for FastestLaps.com data |
| **Output** | Lap times, acceleration data, vehicle specs across multiple tracks |
| **License** | GPL-3.0 |
| **Note** | Creates custom datasets from the largest lap time aggregator |

---

## Kaggle and academic platforms have mixed-quality options

### Sports Car Prices Dataset
| Attribute | Details |
|-----------|---------|
| **URL** | https://www.kaggle.com/datasets/rkiattisak/sports-car-prices-dataset |
| **Performance Metrics** | **0-60 mph times** (1.85–5.3 seconds range), horsepower, torque |
| **Coverage** | Porsche, Ferrari, Lamborghini, Bugatti, McLaren |
| **Format** | CSV |
| **License** | Free for research |

### UCI Auto MPG Dataset ⭐ Classic ML Benchmark
| Attribute | Details |
|-----------|---------|
| **URL** | https://archive.ics.uci.edu/dataset/9/auto+mpg |
| **Performance Metrics** | **0-60 mph acceleration times**, MPG, displacement, horsepower |
| **Records** | 398 vehicles |
| **Time Period** | 1970–1982 model years |
| **Format** | Data file with Python import: `from ucimlrepo import fetch_ucirepo` |
| **License** | CC BY 4.0 |

### Car Specification Dataset 1945–2020
| Attribute | Details |
|-----------|---------|
| **URL** | https://www.kaggle.com/datasets/jahaidulislam/car-specification-dataset-1945-2020 |
| **Records** | **70,000+** (24.87 MB, 78 columns) |
| **Time Period** | 75 years of historical coverage |
| **Caution** | Significant missing values—97% missing CO₂, 99% missing safety ratings |

### EPA Fuel Economy Dataset ⭐ Gold Standard for Official Data
| Attribute | Details |
|-----------|---------|
| **URL** | https://fueleconomy.gov/feg/download.shtml |
| **Records** | All EPA-tested vehicles 1984–present |
| **Metrics** | MPG, MPGe, kWh/100mi, CO₂, GHG scores, engine specs |
| **Format** | CSV, XLS, XML; **REST API available** at fueleconomy.gov/feg/ws/ |
| **License** | Public domain |
| **Note** | No 0-60/braking data—focused on efficiency metrics |

---

## International archives offer Europe's most rigorous testing data

### Auto Motor und Sport Testarchiv (Germany)
| Attribute | Details |
|-----------|---------|
| **URL** | https://www.auto-motor-und-sport.de/testarchiv/ |
| **Records** | **7,000+ tests** spanning 20+ years |
| **Metrics** | 0-100 km/h, max speed, braking distances, fuel consumption |
| **Format** | Searchable web interface (German); some content behind ams+ subscription |
| **Filters** | Brand, model, generation, year (1900–2026), price, power, drivetrain |

### Sport Auto Supertest ⭐ Most Rigorous Magazine Testing
The gold standard for European performance testing since March 1997. **200+ Supertests** with a 100-point scoring system measuring:
- Nürburgring Nordschleife lap times (20.6km configuration)
- Hockenheimring lap times
- Lateral acceleration (skidpad equivalent)
- Wind tunnel testing (drag/lift coefficients)
- 0–200–0 km/h acceleration/braking
- Slalom and lane-change tests
- 33 data points per Nordschleife lap including sector speeds and g-forces

Driver Horst von Saurma serves as the consistent benchmark—his times often match factory drivers within seconds.

### Autocar Archive (UK) ⭐ World's Oldest Car Magazine
| Attribute | Details |
|-----------|---------|
| **URL** | https://shop.exacteditions.com/gb/autocar |
| **Records** | **6,690+ issues** fully searchable (1895–present) |
| **Metrics** | 0-60 mph, 0-100 mph, max speed, braking distances, complete specs |
| **Time Period** | 130+ years—invented the road test in 1928 |
| **Format** | Scanned pages via Exact Editions platform |
| **Cost** | £39.99/quarter digital; £54.99 with print |
| **Historic Value** | First performance figures for Jaguar XJ220, McLaren F1, Bugatti Veyron |

### Evo Magazine Leaderboard (UK) — Free Access
| Attribute | Details |
|-----------|---------|
| **URL** | https://www.evo.co.uk/video/16996/evo-leaderboard-lap-times-the-worlds-fastest-cars-tested-on-track |
| **Tracks** | Anglesey Coastal (1.55mi), Bedford Autodrome (1.8mi), Blyton Park (1.6mi) |
| **Format** | Full lap time tables published free online |
| **Notable Times** | Fastest road car: BAC Mono 2.5 at 1:07.7; Ferrari SF90 at 1:10.0 |

### Best Motoring Tsukuba Database (Japan)
| Attribute | Details |
|-----------|---------|
| **URL** | https://fastestlaps.com/tracks/tsukuba (aggregated times) |
| **Time Period** | 1987–2011 (legendary TV show with Keiichi Tsuchiya) |
| **Track** | Tsukuba Circuit (2.045 km) |
| **Records** | 300+ times archived at strikeengine.com/lap-times-1457/ |

---

## FastestLaps.com is the most comprehensive lap time aggregator

| Attribute | Details |
|-----------|---------|
| **URL** | https://fastestlaps.com |
| **Coverage** | Multi-track global database since 2006 |
| **Key Tracks** | Nürburgring Nordschleife (887+ times), Tsukuba (77+), Anglesey (221+), Motor Trend Figure-8 (2,138) |
| **Data** | Lap times, acceleration metrics, vehicle specs |
| **Access** | Free web browsing; no official API or download |
| **Data Extraction** | Use **LapMiner** GitHub tool for scraping |

**Official Nürburgring Records** (certified since 2019): https://nuerburgring.de/info/nuerburgring/records

---

## Commercial APIs provide structured access to performance data

### Auto-Data.net API ⭐ Best for Acceleration Data
| Attribute | Details |
|-----------|---------|
| **URL** | https://api.auto-data.net/ |
| **Metrics** | **0-60 mph, 0-100 km/h, 0-200, 0-300, top speed**, horsepower, torque |
| **Records** | 55,000+ specs, 3,500+ models, 10,000+ generations |
| **Format** | XML/JSON API |
| **Cost** | Commercial—contact for pricing |

### Car Specs on RapidAPI
| Attribute | Details |
|-----------|---------|
| **URL** | https://rapidapi.com/alekivanovski96-O1vKHrFskQm/api/car-specs |
| **Metrics** | 0-100 km/h, 0-60 mph, 0-200/300, top speed |
| **Records** | 55,000+ trims, 250+ brands since 1945 |
| **Format** | JSON via RapidAPI |
| **Features** | VIN decoder, 99.88% uptime |

### NHTSA vPIC API (Free Government Source)
| Attribute | Details |
|-----------|---------|
| **URL** | https://vpic.nhtsa.dot.gov/api |
| **Metrics** | VIN decoding, engine type/cylinders/displacement, drive type |
| **Format** | XML, CSV, JSON; standalone database downloads |
| **Cost** | Free—no API key required, 24/7 availability |
| **Limitation** | Manufacturer specs only—no tested performance data |

### JATO Dynamics (Enterprise)
| Attribute | Details |
|-----------|---------|
| **URL** | https://developer.jato.com/ |
| **Coverage** | 50+ markets, 200+ brands, 1,000 datapoints per vehicle |
| **Format** | RESTful API with OAuth 2.0 |
| **Cost** | Enterprise pricing |

### CarQuery API
| Attribute | Details |
|-----------|---------|
| **URL** | https://www.carqueryapi.com/ |
| **Format** | JSON API + downloadable SQL/CSV |
| **Cost** | Basic $45, Advanced $75 (36 fields), Full $95 |

**Note**: Edmunds API is discontinued for public developers—only available to partners.

---

## What performance data is realistically available

| Metric | Free Sources | Paid Sources |
|--------|--------------|--------------|
| **0-60 mph / 0-100 km/h** | GitHub repos, Kaggle, FastestLaps | Auto-Data.net, CarsDataset.com |
| **Quarter-mile times** | Very limited—zeroto60times.com (web only) | Auto-Data.net API |
| **Skidpad g-force** | Not available in any open dataset | Would require publication scraping |
| **60-0 braking distance** | Not available in any open dataset | Would require publication scraping |
| **Track lap times** | FastestLaps.com via LapMiner scraper | — |
| **Top speed** | Multiple GitHub repos, Kaggle | Most commercial APIs |
| **Slalom/Figure-8** | FastestLaps aggregates Motor Trend data | — |

---

## Recommended approach for building a research dataset

**For acceleration data (0-60/0-100)**: Download the free **ilyasozkurt/automobile-models-and-specs** repository (30,000+ records) or purchase CarsDataset.com ($45–95) for cleaner, normalized data.

**For lap times**: Deploy the **LapMiner** tool against FastestLaps.com to extract Nürburgring, Tsukuba, and track times into structured formats.

**For historical US magazine data**: The Stanford Road & Track archive (1947–2012) is the only accessible compilation of original test sheets, requiring in-person academic access.

**For braking and skidpad data**: No open dataset exists. Options include purchasing the Auto-Data.net API subscription, or building a custom scraper for Car and Driver/Motor Trend individual reviews—though this may violate terms of service.

**For official specifications**: EPA FuelEconomy.gov and NHTSA vPIC provide free, high-quality APIs with government-verified data, though performance metrics are limited to engine specs rather than tested acceleration/braking.

The fragmented nature of automotive performance data reflects the proprietary value publications place on their testing programs. The most complete research dataset would combine GitHub repositories for acceleration times, FastestLaps scraping for track data, and commercial API access for braking/handling metrics.
