/**
 * Format a numeric value with thousands separator.
 * If the value is a decimal, it preserves the decimal places.
 */
function formatWithThousandsSeparator(value: string): string {
  const num = parseFloat(value);
  if (isNaN(num)) return value;

  // Check if it's an integer or has decimals
  if (Number.isInteger(num)) {
    return num.toLocaleString("en-US");
  }

  // For decimals, preserve original precision
  const parts = value.split(".");
  const integerPart = parseInt(parts[0], 10).toLocaleString("en-US");
  const decimalPart = parts[1] || "";

  return decimalPart ? `${integerPart}.${decimalPart}` : integerPart;
}

export function formatValue(value: string | undefined | null, unit?: string): string {
  if (value === undefined || value === null || value === "") {
    return "—";
  }

  // Check if the value looks like a number
  const trimmedValue = value.trim();
  const isNumeric = /^-?\d+(\.\d+)?$/.test(trimmedValue);

  if (isNumeric) {
    const formattedValue = formatWithThousandsSeparator(trimmedValue);
    if (unit) {
      return `${formattedValue} ${unit}`;
    }
    return formattedValue;
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
