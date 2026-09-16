# Architecture

A Next.js app over a build-time ETL pipeline. Data is prepared ahead of time;
the app queries a prepared database rather than scraping at request time.

## Layout

| Path | What lives there |
|---|---|
| `etl/` | Ingestion — parsing source documents and normalising figures into a consistent schema. |
| `src/` | The Next.js application: tables, filtering and comparison UI. |
| `public/data/` | The generated database and CSV. The raw source material the ETL reads is not published. |
| `scripts/` | Build helpers. |

## Notes

- Range and consistency validators (`etl/validators/`) run over the merged data
  on every pipeline run; **Zod** validates the API's query parameters.
- Tabular UI is built on **TanStack Table**; storage uses **better-sqlite3**.
- Each record keeps the list of sources it was built from, and each source in
  `etl/config/sources.yaml` carries the priority used when sources disagree.
