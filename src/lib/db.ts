import Database from "better-sqlite3";
import path from "path";

let db: Database.Database | null = null;

function getDbPath(): string {
  return path.join(process.cwd(), "public", "data", "car-performance-data.db");
}

export function getDb(): Database.Database {
  if (!db) {
    db = new Database(getDbPath(), { readonly: true });
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
  body_style: string | null;
  engine_type: string | null;
  engine_displacement: number | null;
  engine_aspiration: string | null;
  engine_placement: string | null;
  drivetrain: string | null;
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
  // New filter parameters
  bodyStyle?: string;
  propulsion?: string;
  engineType?: string;
  engineAspiration?: string;
  enginePlacement?: string;
  drivetrain?: string;
  // Threshold filters (cumulative)
  displacementMin?: number;
  powerMin?: number;
  torqueMin?: number;
  weightMax?: number;
  powerToWeightMax?: number;
  accel060Max?: number;
  quarterMileMax?: number;
  topSpeedMin?: number;
}

const VALID_SORT_COLUMNS = new Set([
  "manufacturer",
  "country",
  "model",
  "year",
  "propulsion",
  "body_style",
  "engine_type",
  "engine_displacement",
  "engine_aspiration",
  "engine_placement",
  "drivetrain",
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

// Base WHERE clause for valid records
const VALID_RECORDS_WHERE = `WHERE ${REQUIRED_FIELD_CONDITIONS.join(" AND ")}`;

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
    conditions.push("(sources = ? OR sources LIKE ? OR sources LIKE ? OR sources LIKE ?)");
    values.push(params.source);
    values.push(`${params.source},%`);
    values.push(`%, ${params.source},%`);
    values.push(`%, ${params.source}`);
  }

  // New categorical filters
  if (params.bodyStyle) {
    conditions.push("body_style = ?");
    values.push(params.bodyStyle);
  }

  if (params.propulsion) {
    conditions.push("propulsion = ?");
    values.push(params.propulsion);
  }

  if (params.engineType) {
    conditions.push("engine_type = ?");
    values.push(params.engineType);
  }

  if (params.engineAspiration) {
    conditions.push("engine_aspiration = ?");
    values.push(params.engineAspiration);
  }

  if (params.enginePlacement) {
    conditions.push("engine_placement = ?");
    values.push(params.enginePlacement);
  }

  if (params.drivetrain) {
    conditions.push("drivetrain = ?");
    values.push(params.drivetrain);
  }

  // Threshold filters
  if (params.displacementMin) {
    conditions.push("engine_displacement >= ?");
    values.push(params.displacementMin);
  }

  if (params.powerMin) {
    conditions.push("power_hp >= ?");
    values.push(params.powerMin);
  }

  if (params.torqueMin) {
    // torque is stored as string like "300 lb-ft", extract number
    conditions.push("CAST(SUBSTR(torque, 1, INSTR(torque, ' ') - 1) AS REAL) >= ?");
    values.push(params.torqueMin);
  }

  if (params.weightMax) {
    conditions.push("curb_weight_lb <= ?");
    values.push(params.weightMax);
  }

  if (params.powerToWeightMax) {
    conditions.push("curb_weight_lb IS NOT NULL AND power_hp IS NOT NULL AND power_hp > 0 AND (curb_weight_lb / power_hp) <= ?");
    values.push(params.powerToWeightMax);
  }

  if (params.accel060Max) {
    conditions.push('"0_60_mph_sec" <= ?');
    values.push(params.accel060Max);
  }

  if (params.quarterMileMax) {
    conditions.push("quarter_mile_sec <= ?");
    values.push(params.quarterMileMax);
  }

  if (params.topSpeedMin) {
    conditions.push("top_speed_mph >= ?");
    values.push(params.topSpeedMin);
  }

  const whereClause = `WHERE ${conditions.join(" AND ")}`;

  // Validate sort column
  let orderClause = "ORDER BY manufacturer ASC, model ASC";
  if (params.sortBy && VALID_SORT_COLUMNS.has(params.sortBy)) {
    const sortOrder = params.sortOrder?.toLowerCase() === "desc" ? "DESC" : "ASC";
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

// Filter option with count
export interface FilterOption {
  value: string;
  count: number;
}

// Threshold option with count
export interface ThresholdOption {
  label: string;
  value: number;
  count: number;
}

export interface MetaData {
  manufacturers: FilterOption[];
  countries: FilterOption[];
  sources: FilterOption[];
  yearRange: { min: number; max: number };
  bodyStyles: FilterOption[];
  propulsions: FilterOption[];
  engineTypes: FilterOption[];
  engineAspirations: FilterOption[];
  enginePlacements: FilterOption[];
  drivetrains: FilterOption[];
  displacementThresholds: ThresholdOption[];
  powerThresholds: ThresholdOption[];
  torqueThresholds: ThresholdOption[];
  weightThresholds: ThresholdOption[];
  powerToWeightThresholds: ThresholdOption[];
  accel060Thresholds: ThresholdOption[];
  quarterMileThresholds: ThresholdOption[];
  topSpeedThresholds: ThresholdOption[];
}

function getFilterOptionsWithCounts(
  db: Database.Database,
  column: string
): FilterOption[] {
  const stmt = db.prepare(
    `SELECT ${column} as value, COUNT(*) as count
     FROM cars
     ${VALID_RECORDS_WHERE} AND ${column} IS NOT NULL AND ${column} != ''
     GROUP BY ${column}
     ORDER BY ${column}`
  );

  return stmt.all() as FilterOption[];
}

function getThresholdCounts(
  db: Database.Database,
  column: string,
  thresholds: { label: string; value: number }[],
  operator: ">" | "<" | ">=" | "<="
): ThresholdOption[] {
  const results: ThresholdOption[] = [];

  for (const threshold of thresholds) {
    const stmt = db.prepare(
      `SELECT COUNT(*) as count FROM cars
       ${VALID_RECORDS_WHERE} AND ${column} IS NOT NULL AND ${column} ${operator} ?`
    );
    const result = stmt.get(threshold.value) as { count: number };
    results.push({
      label: threshold.label,
      value: threshold.value,
      count: result.count,
    });
  }

  return results;
}

function getTorqueThresholdCounts(
  db: Database.Database,
  thresholds: { label: string; value: number }[]
): ThresholdOption[] {
  const results: ThresholdOption[] = [];

  for (const threshold of thresholds) {
    const stmt = db.prepare(
      `SELECT COUNT(*) as count FROM cars
       ${VALID_RECORDS_WHERE} AND torque IS NOT NULL
       AND CAST(SUBSTR(torque, 1, INSTR(torque, ' ') - 1) AS REAL) >= ?`
    );
    const result = stmt.get(threshold.value) as { count: number };
    results.push({
      label: threshold.label,
      value: threshold.value,
      count: result.count,
    });
  }

  return results;
}

function getPowerToWeightThresholdCounts(
  db: Database.Database,
  thresholds: { label: string; value: number }[]
): ThresholdOption[] {
  const results: ThresholdOption[] = [];

  for (const threshold of thresholds) {
    const stmt = db.prepare(
      `SELECT COUNT(*) as count FROM cars
       ${VALID_RECORDS_WHERE}
       AND curb_weight_lb IS NOT NULL
       AND power_hp IS NOT NULL
       AND power_hp > 0
       AND (curb_weight_lb / power_hp) <= ?`
    );
    const result = stmt.get(threshold.value) as { count: number };
    results.push({
      label: threshold.label,
      value: threshold.value,
      count: result.count,
    });
  }

  return results;
}

export function getMeta(): MetaData {
  const db = getDb();

  // Get manufacturers with counts
  const manufacturers = getFilterOptionsWithCounts(db, "manufacturer");

  // Get countries with counts
  const countries = getFilterOptionsWithCounts(db, "country");

  // Get year range
  const yearRangeStmt = db.prepare(
    `SELECT MIN(CAST(year AS INTEGER)) as min, MAX(CAST(year AS INTEGER)) as max FROM cars ${VALID_RECORDS_WHERE}`
  );
  const yearRange = yearRangeStmt.get() as { min: number; max: number };

  // Get sources with counts (comma-separated field)
  const sourcesStmt = db.prepare(
    `SELECT sources FROM cars ${VALID_RECORDS_WHERE} AND sources IS NOT NULL AND sources <> ''`
  );
  const sourcesRows = sourcesStmt.all() as { sources: string }[];

  const sourceCountMap = new Map<string, number>();
  for (const row of sourcesRows) {
    const parts = row.sources.split(",").map((s) => s.trim());
    for (const part of parts) {
      if (part) {
        sourceCountMap.set(part, (sourceCountMap.get(part) || 0) + 1);
      }
    }
  }
  const sources: FilterOption[] = Array.from(sourceCountMap.entries())
    .map(([value, count]) => ({ value, count }))
    .sort((a, b) => a.value.localeCompare(b.value));

  // Get new filter options with counts
  const bodyStyles = getFilterOptionsWithCounts(db, "body_style");
  const propulsions = getFilterOptionsWithCounts(db, "propulsion");
  const engineTypes = getFilterOptionsWithCounts(db, "engine_type");
  const engineAspirations = getFilterOptionsWithCounts(db, "engine_aspiration");
  const enginePlacements = getFilterOptionsWithCounts(db, "engine_placement");
  const drivetrains = getFilterOptionsWithCounts(db, "drivetrain");

  // Threshold options
  const displacementThresholds = getThresholdCounts(
    db,
    "engine_displacement",
    [
      { label: "> 1.0 L", value: 1.0 },
      { label: "> 2.0 L", value: 2.0 },
      { label: "> 3.0 L", value: 3.0 },
      { label: "> 4.0 L", value: 4.0 },
      { label: "> 5.0 L", value: 5.0 },
      { label: "> 6.0 L", value: 6.0 },
    ],
    ">"
  );

  const powerThresholds = getThresholdCounts(
    db,
    "power_hp",
    [
      { label: "> 100 hp", value: 100 },
      { label: "> 200 hp", value: 200 },
      { label: "> 300 hp", value: 300 },
      { label: "> 400 hp", value: 400 },
      { label: "> 500 hp", value: 500 },
      { label: "> 600 hp", value: 600 },
      { label: "> 700 hp", value: 700 },
      { label: "> 1000 hp", value: 1000 },
    ],
    ">"
  );

  const torqueThresholds = getTorqueThresholdCounts(db, [
    { label: "> 100 lb-ft", value: 100 },
    { label: "> 200 lb-ft", value: 200 },
    { label: "> 300 lb-ft", value: 300 },
    { label: "> 400 lb-ft", value: 400 },
    { label: "> 500 lb-ft", value: 500 },
    { label: "> 600 lb-ft", value: 600 },
  ]);

  const weightThresholds = getThresholdCounts(
    db,
    "curb_weight_lb",
    [
      { label: "< 5000 lbs", value: 5000 },
      { label: "< 4000 lbs", value: 4000 },
      { label: "< 3500 lbs", value: 3500 },
      { label: "< 3000 lbs", value: 3000 },
      { label: "< 2500 lbs", value: 2500 },
      { label: "< 2000 lbs", value: 2000 },
    ],
    "<"
  );

  const powerToWeightThresholds = getPowerToWeightThresholdCounts(db, [
    { label: "< 15 lb/hp", value: 15 },
    { label: "< 10 lb/hp", value: 10 },
    { label: "< 8 lb/hp", value: 8 },
    { label: "< 6 lb/hp", value: 6 },
    { label: "< 5 lb/hp", value: 5 },
    { label: "< 4 lb/hp", value: 4 },
    { label: "< 3 lb/hp", value: 3 },
  ]);

  const accel060Thresholds = getThresholdCounts(
    db,
    '"0_60_mph_sec"',
    [
      { label: "< 10 sec", value: 10 },
      { label: "< 8 sec", value: 8 },
      { label: "< 6 sec", value: 6 },
      { label: "< 5 sec", value: 5 },
      { label: "< 4 sec", value: 4 },
      { label: "< 3 sec", value: 3 },
      { label: "< 2.5 sec", value: 2.5 },
    ],
    "<"
  );

  const quarterMileThresholds = getThresholdCounts(
    db,
    "quarter_mile_sec",
    [
      { label: "< 16 sec", value: 16 },
      { label: "< 14 sec", value: 14 },
      { label: "< 13 sec", value: 13 },
      { label: "< 12 sec", value: 12 },
      { label: "< 11 sec", value: 11 },
      { label: "< 10 sec", value: 10 },
    ],
    "<"
  );

  const topSpeedThresholds = getThresholdCounts(
    db,
    "top_speed_mph",
    [
      { label: "> 100 mph", value: 100 },
      { label: "> 150 mph", value: 150 },
      { label: "> 175 mph", value: 175 },
      { label: "> 200 mph", value: 200 },
      { label: "> 250 mph", value: 250 },
    ],
    ">"
  );

  return {
    manufacturers,
    countries,
    sources,
    yearRange: {
      min: yearRange.min ?? 1900,
      max: yearRange.max ?? new Date().getFullYear(),
    },
    bodyStyles,
    propulsions,
    engineTypes,
    engineAspirations,
    enginePlacements,
    drivetrains,
    displacementThresholds,
    powerThresholds,
    torqueThresholds,
    weightThresholds,
    powerToWeightThresholds,
    accel060Thresholds,
    quarterMileThresholds,
    topSpeedThresholds,
  };
}
