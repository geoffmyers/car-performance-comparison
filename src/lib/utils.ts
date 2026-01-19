export function formatValue(value: string | undefined | null, unit?: string): string {
  if (value === undefined || value === null || value === "") {
    return "—";
  }
  if (unit) {
    return `${value} ${unit}`;
  }
  return value;
}

export function formatLapTime(seconds: string | undefined | null): string {
  if (!seconds || seconds === "") return "—";

  const totalSeconds = parseFloat(seconds);
  if (isNaN(totalSeconds)) return seconds;

  const minutes = Math.floor(totalSeconds / 60);
  const remainingSeconds = (totalSeconds % 60).toFixed(1);

  if (minutes > 0) {
    return `${minutes}:${remainingSeconds.padStart(4, "0")}`;
  }
  return `${remainingSeconds}s`;
}

export function parseNumericValue(value: string | undefined | null): number | null {
  if (!value || value === "") return null;
  const parsed = parseFloat(value);
  return isNaN(parsed) ? null : parsed;
}
