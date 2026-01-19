export interface CarData {
  manufacturer: string;
  country: string;
  model: string;
  year: string;
  propulsion: string;
  body_style: string;
  engine_type: string;
  engine_displacement: string;
  engine_aspiration: string;
  engine_placement: string;
  drivetrain: string;
  "0_60_mph_sec": string;
  "0_100_kmh_sec": string;
  "0_100_mph_sec": string;
  "0_200_kmh_sec": string;
  quarter_mile_sec: string;
  quarter_mile_speed_mph: string;
  top_speed_mph: string;
  top_speed_kmh: string;
  power_hp: string;
  power_kw: string;
  torque: string;
  engine: string;
  braking_70_0_ft: string;
  braking_100_0_ft: string;
  skidpad_g: string;
  curb_weight_lb: string;
  nurburgring_lap_sec: string;
  nurburgring_date: string;
  nurburgring_driver: string;
  top_gear_lap_sec: string;
  top_gear_episode: string;
  lightning_lap_sec: string;
  sources: string;
}

export interface ColumnConfig {
  id: keyof CarData;
  header: string;
  category: string;
  unit?: string;
  isNumeric?: boolean;
}

export const columnConfigs: ColumnConfig[] = [
  // Default visible columns in order
  { id: "country", header: "Country", category: "General" },
  { id: "year", header: "Year", category: "General" },
  { id: "manufacturer", header: "Make", category: "General" },
  { id: "model", header: "Model", category: "General" },
  { id: "body_style", header: "Body Style", category: "General" },
  { id: "propulsion", header: "Powertrain", category: "General" },
  { id: "engine_type", header: "Engine Type", category: "Specs" },
  { id: "engine_displacement", header: "Displacement", category: "Specs", unit: "L", isNumeric: true },
  { id: "engine_aspiration", header: "Aspiration", category: "Specs" },
  { id: "engine_placement", header: "Engine Placement", category: "Specs" },
  { id: "drivetrain", header: "Drivetrain", category: "Specs" },
  { id: "power_hp", header: "Power", category: "Power", unit: "hp", isNumeric: true },
  { id: "torque", header: "Torque", category: "Power", unit: "lb-ft" },
  { id: "curb_weight_lb", header: "Curb Weight", category: "Specs", unit: "lb", isNumeric: true },
  { id: "0_60_mph_sec", header: "0-60 mph", category: "Acceleration", unit: "sec", isNumeric: true },
  { id: "quarter_mile_sec", header: "1/4 Mile", category: "Acceleration", unit: "sec", isNumeric: true },
  { id: "top_speed_mph", header: "Top Speed", category: "Speed", unit: "mph", isNumeric: true },
  { id: "sources", header: "Sources", category: "Meta" },
  // Hidden by default
  { id: "0_100_kmh_sec", header: "0-100 km/h", category: "Acceleration", unit: "sec", isNumeric: true },
  { id: "0_100_mph_sec", header: "0-100 mph", category: "Acceleration", unit: "sec", isNumeric: true },
  { id: "0_200_kmh_sec", header: "0-200 km/h", category: "Acceleration", unit: "sec", isNumeric: true },
  { id: "quarter_mile_speed_mph", header: "1/4 Mile Speed", category: "Acceleration", unit: "mph", isNumeric: true },
  { id: "top_speed_kmh", header: "Top Speed (km/h)", category: "Speed", unit: "km/h", isNumeric: true },
  { id: "power_kw", header: "Power (kW)", category: "Power", unit: "kW", isNumeric: true },
  { id: "engine", header: "Engine", category: "Specs" },
  { id: "braking_70_0_ft", header: "70-0 Braking", category: "Braking", unit: "ft", isNumeric: true },
  { id: "braking_100_0_ft", header: "100-0 Braking", category: "Braking", unit: "ft", isNumeric: true },
  { id: "skidpad_g", header: "Skidpad", category: "Handling", unit: "g", isNumeric: true },
  { id: "nurburgring_lap_sec", header: "Nürburgring Lap", category: "Lap Times", unit: "sec", isNumeric: true },
  { id: "nurburgring_date", header: "Nürburgring Date", category: "Lap Times" },
  { id: "nurburgring_driver", header: "Nürburgring Driver", category: "Lap Times" },
  { id: "top_gear_lap_sec", header: "Top Gear Lap", category: "Lap Times", unit: "sec", isNumeric: true },
  { id: "top_gear_episode", header: "Top Gear Episode", category: "Lap Times" },
  { id: "lightning_lap_sec", header: "Lightning Lap", category: "Lap Times", unit: "sec", isNumeric: true },
];

export const columnCategories = ["General", "Acceleration", "Speed", "Power", "Braking", "Handling", "Specs", "Lap Times", "Meta"] as const;

// Country code to name mapping
export const countryNames: Record<string, string> = {
  AE: "United Arab Emirates",
  AT: "Austria",
  AU: "Australia",
  CN: "China",
  CZ: "Czech Republic",
  DE: "Germany",
  DK: "Denmark",
  ES: "Spain",
  FR: "France",
  GB: "United Kingdom",
  HR: "Croatia",
  IT: "Italy",
  JP: "Japan",
  KR: "South Korea",
  NL: "Netherlands",
  RO: "Romania",
  RU: "Russia",
  SE: "Sweden",
  US: "United States",
};

// Source code to display name mapping
export const sourceNames: Record<string, string> = {
  acceleration: "Wikipedia - Fastest Acceleration",
  caranddriver: "Car and Driver",
  caranddriver_lightning_lap: "Car and Driver - Lightning Lap",
  nurburgring: "Nürburgring Lap Times",
  power_output: "Wikipedia - Power Output",
  speed_records: "Wikipedia - Speed Records",
  top_gear: "Top Gear Test Track",
};