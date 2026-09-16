# Architecture

A Next.js app over a build-time ETL pipeline. Data is prepared ahead of time;
the app queries a prepared database rather than scraping at request time.

## Layout

| Path | What lives there |
|---|---|
| `etl/` | Ingestion — parsing source documents and normalising figures into a consistent schema. |
| `src/` | The Next.js application: tables, filtering and comparison UI. |
| `public/data/` | Captured source material and the generated data set. |
| `scripts/` | Build helpers. |

## Notes

- Figures are validated with **Zod** on the way in, so a malformed or missing
  value fails at build rather than rendering as a blank cell.
- Tabular UI is built on **TanStack Table**; storage uses **better-sqlite3**.
- Each figure keeps its source. When two sources disagree, the data set records
  both rather than silently preferring one.
