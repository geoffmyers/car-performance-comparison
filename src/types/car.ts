export interface CarData {
  car_name: string;
  year: string;
  propulsion: string;
  "0_60_mph_sec": string;
  "0_100_kmh_sec": string;
  "0_100_mph_sec": string;
  "0_200_kmh_sec": string;
  quarter_mile_sec: string;
  top_speed_mph: string;
  top_speed_kmh: string;
  power_hp: string;
  power_kw: string;
  torque: string;
  engine: string;
  nurburgring_lap_sec: string;
  nurburgring_date: string;
  nurburgring_driver: string;
  top_gear_lap_sec: string;
  top_gear_episode: string;
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
  { id: "car_name", header: "Car Name", category: "General" },
  { id: "year", header: "Year", category: "General", isNumeric: true },
  { id: "propulsion", header: "Propulsion", category: "General" },
  { id: "0_60_mph_sec", header: "0-60 mph", category: "Acceleration", unit: "sec", isNumeric: true },
  { id: "0_100_kmh_sec", header: "0-100 km/h", category: "Acceleration", unit: "sec", isNumeric: true },
  { id: "0_100_mph_sec", header: "0-100 mph", category: "Acceleration", unit: "sec", isNumeric: true },
  { id: "0_200_kmh_sec", header: "0-200 km/h", category: "Acceleration", unit: "sec", isNumeric: true },
  { id: "quarter_mile_sec", header: "1/4 Mile", category: "Acceleration", unit: "sec", isNumeric: true },
  { id: "top_speed_mph", header: "Top Speed (mph)", category: "Speed", unit: "mph", isNumeric: true },
  { id: "top_speed_kmh", header: "Top Speed (km/h)", category: "Speed", unit: "km/h", isNumeric: true },
  { id: "power_hp", header: "Power (hp)", category: "Power", unit: "hp", isNumeric: true },
  { id: "power_kw", header: "Power (kW)", category: "Power", unit: "kW", isNumeric: true },
  { id: "torque", header: "Torque", category: "Power" },
  { id: "engine", header: "Engine", category: "Specs" },
  { id: "nurburgring_lap_sec", header: "Nürburgring Lap", category: "Lap Times", unit: "sec", isNumeric: true },
  { id: "nurburgring_date", header: "Nürburgring Date", category: "Lap Times" },
  { id: "nurburgring_driver", header: "Nürburgring Driver", category: "Lap Times" },
  { id: "top_gear_lap_sec", header: "Top Gear Lap", category: "Lap Times", unit: "sec", isNumeric: true },
  { id: "top_gear_episode", header: "Top Gear Episode", category: "Lap Times" },
  { id: "sources", header: "Sources", category: "Meta" },
];

export const columnCategories = ["General", "Acceleration", "Speed", "Power", "Specs", "Lap Times", "Meta"] as const;
