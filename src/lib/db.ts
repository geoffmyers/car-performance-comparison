import Database from "better-sqlite3";
import path from "path";

let db: Database.Database | null = null;

function getDbPath(): string {
  return path.join(process.cwd(), "public", "data", "car-performance-data.db");
}

export function getDb(): Database.Database {
  if (!db) {
    db = new Database(getDbPath(), { readonly: true });
    // No need to set WAL mode for readonly database
  }
  return db;
}

export interface CarRow {
  id: number;
  manufacturer: string | null;
  country: string | null;
  model: string | null;
  year: string | null;
  propulsion: string | null;
  "0_60_mph_sec": number | null;
  "0_100_kmh_sec": number | null;
  "0_100_mph_sec": number | null;
  "0_200_kmh_sec": number | null;
  quarter_mile_sec: number | null;
  quarter_mile_speed_mph: number | null;
  top_speed_mph: number | null;
  top_speed_kmh: number | null;
  power_hp: number | null;
  power_kw: number | null;
  torque: string | null;
  engine: string | null;
  braking_70_0_ft: number | null;
  braking_100_0_ft: number | null;
  skidpad_g: number | null;
  curb_weight_lb: number | null;
  nurburgring_lap_sec: number | null;
  nurburgring_date: string | null;
  nurburgring_driver: string | null;
  top_gear_lap_sec: number | null;
  top_gear_episode: string | null;
  lightning_lap_sec: number | null;
  sources: string | null;
}

export interface PaginatedResult<T> {
  data: T[];
  pagination: {
    page: number;
    pageSize: number;
    totalCount: number;
    totalPages: number;
  };
}

export interface CarsQueryParams {
  page?: number;
  pageSize?: number;
  sortBy?: string;
  sortOrder?: "asc" | "desc";
  manufacturer?: string;
  country?: string;
  yearMin?: number;
  yearMax?: number;
  search?: string;
  source?: string;
}

const VALID_SORT_COLUMNS = new Set([
  "manufacturer",
  "country",
  "model",
  "year",
  "propulsion",
  "0_60_mph_sec",
  "0_100_kmh_sec",
  "0_100_mph_sec",
  "0_200_kmh_sec",
  "quarter_mile_sec",
  "quarter_mile_speed_mph",
  "top_speed_mph",
  "top_speed_kmh",
  "power_hp",
  "power_kw",
  "braking_70_0_ft",
  "braking_100_0_ft",
  "skidpad_g",
  "curb_weight_lb",
  "nurburgring_lap_sec",
  "top_gear_lap_sec",
  "lightning_lap_sec",
]);

// Required fields that must be present for a car to be displayed
const REQUIRED_FIELD_CONDITIONS = [
  "manufacturer IS NOT NULL AND manufacturer != ''",
  "country IS NOT NULL AND country != ''",
  "model IS NOT NULL AND model != ''",
  "year IS NOT NULL AND year != ''",
  '"0_60_mph_sec" IS NOT NULL',
];

export function getCars(params: CarsQueryParams): PaginatedResult<CarRow> {
  const db = getDb();
  const page = params.page ?? 1;
  const pageSize = Math.min(params.pageSize ?? 50, 100);
  const offset = (page - 1) * pageSize;

  // Start with required field conditions
  const conditions: string[] = [...REQUIRED_FIELD_CONDITIONS];
  const values: (string | number)[] = [];

  // Filter by manufacturer
  if (params.manufacturer) {
    conditions.push("manufacturer = ?");
    values.push(params.manufacturer);
  }

  // Filter by country
  if (params.country) {
    conditions.push("country = ?");
    values.push(params.country);
  }

  // Filter by year range
  if (params.yearMin) {
    conditions.push("CAST(year AS INTEGER) >= ?");
    values.push(params.yearMin);
  }
  if (params.yearMax) {
    conditions.push("CAST(year AS INTEGER) <= ?");
    values.push(params.yearMax);
  }

  // Full-text search
  if (params.search) {
    conditions.push("id IN (SELECT rowid FROM cars_fts WHERE cars_fts MATCH ?)");
    values.push(`${params.search}*`);
  }

  // Filter by source (sources field is comma-separated)
  if (params.source) {
    // Match source anywhere in the comma-separated list
    conditions.push("(sources = ? OR sources LIKE ? OR sources LIKE ? OR sources LIKE ?)");
    values.push(params.source); // exact match (single source)
    values.push(`${params.source},%`); // starts with source
    values.push(`%, ${params.source},%`); // in the middle
    values.push(`%, ${params.source}`); // ends with source
  }

  // Always have WHERE clause since required field conditions are always present
  const whereClause = `WHERE ${conditions.join(" AND ")}`;

  // Validate sort column
  let orderClause = "ORDER BY manufacturer ASC, model ASC";
  if (params.sortBy && VALID_SORT_COLUMNS.has(params.sortBy)) {
    const sortOrder =
      params.sortOrder?.toLowerCase() === "desc" ? "DESC" : "ASC";
    // Handle NULL values in sorting - put them at the end
    orderClause = `ORDER BY "${params.sortBy}" IS NULL, "${params.sortBy}" ${sortOrder}`;
  }

  // Get total count
  const countStmt = db.prepare(`SELECT COUNT(*) as count FROM cars ${whereClause}`);
  const countResult = countStmt.get(...values) as { count: number };
  const totalCount = countResult.count;

  // Get paginated data
  const dataStmt = db.prepare(
    `SELECT * FROM cars ${whereClause} ${orderClause} LIMIT ? OFFSET ?`
  );
  const data = dataStmt.all(...values, pageSize, offset) as CarRow[];

  return {
    data,
    pagination: {
      page,
      pageSize,
      totalCount,
      totalPages: Math.ceil(totalCount / pageSize),
    },
  };
}

export interface MetaData {
  manufacturers: string[];
  countries: string[];
  sources: string[];
  yearRange: { min: number; max: number };
}

// Base WHERE clause for valid records (used in metadata queries too)
const VALID_RECORDS_WHERE = `WHERE ${REQUIRED_FIELD_CONDITIONS.join(" AND ")}`;

export function getMeta(): MetaData {
  const db = getDb();

  // Get unique manufacturers from valid records only
  const manufacturersStmt = db.prepare(
    `SELECT DISTINCT manufacturer FROM cars ${VALID_RECORDS_WHERE} ORDER BY manufacturer`
  );
  const manufacturers = (manufacturersStmt.all() as { manufacturer: string }[]).map(
    (r) => r.manufacturer
  );

  // Get unique countries from valid records only
  const countriesStmt = db.prepare(
    `SELECT DISTINCT country FROM cars ${VALID_RECORDS_WHERE} ORDER BY country`
  );
  const countries = (countriesStmt.all() as { country: string }[]).map(
    (r) => r.country
  );

  // Get year range from valid records only
  const yearRangeStmt = db.prepare(
    `SELECT MIN(CAST(year AS INTEGER)) as min, MAX(CAST(year AS INTEGER)) as max FROM cars ${VALID_RECORDS_WHERE}`
  );
  const yearRange = yearRangeStmt.get() as { min: number; max: number };

  // Get unique sources from valid records (sources are comma-separated)
  const sourcesStmt = db.prepare(
    `SELECT DISTINCT sources FROM cars ${VALID_RECORDS_WHERE} AND sources IS NOT NULL AND sources <> ''`
  );
  const sourcesRows = sourcesStmt.all() as { sources: string }[];
  // Extract unique individual sources from comma-separated values
  const sourceSet = new Set<string>();
  for (const row of sourcesRows) {
    const parts = row.sources.split(",").map((s) => s.trim());
    for (const part of parts) {
      if (part) sourceSet.add(part);
    }
  }
  const sources = Array.from(sourceSet).sort();

  return {
    manufacturers,
    countries,
    sources,
    yearRange: {
      min: yearRange.min ?? 1900,
      max: yearRange.max ?? new Date().getFullYear(),
    },
  };
}
