"use client";

import { useMemo } from "react";

interface ManufacturerLogoProps {
  manufacturer: string;
  size?: number;
  className?: string;
}

// Color palette for manufacturers (brand colors where applicable)
const manufacturerColors: Record<string, string> = {
  "Alfa Romeo": "#B2001B",
  "Alpine": "#0055A4",
  "Aston Martin": "#006847",
  "Audi": "#BB0A30",
  "Bentley": "#333333",
  "BMW": "#0066B1",
  "Bugatti": "#BE0030",
  "Cadillac": "#9D8B6E",
  "Chevrolet": "#D4AF37",
  "Dodge": "#BA0C2F",
  "Ferrari": "#DC0000",
  "Fiat": "#8B0000",
  "Ford": "#003478",
  "Honda": "#CC0000",
  "Hyundai": "#002C5F",
  "Jaguar": "#1A472A",
  "Kia": "#05141F",
  "Koenigsegg": "#CCAA00",
  "Lamborghini": "#DAA520",
  "Lexus": "#1A1A1A",
  "Lotus": "#FFD700",
  "Maserati": "#0C2340",
  "Mazda": "#8B0000",
  "McLaren": "#FF8000",
  "Mercedes-Benz": "#00ADEF",
  "Mercedes-AMG": "#00ADEF",
  "Mini": "#000000",
  "Mitsubishi": "#ED1C24",
  "Nissan": "#C3002F",
  "Pagani": "#1C1C1C",
  "Porsche": "#9B0E0E",
  "Renault": "#FFD100",
  "Rimac": "#00A0E3",
  "Subaru": "#013C74",
  "Suzuki": "#E21836",
  "Tesla": "#CC0000",
  "Toyota": "#EB0A1E",
  "Volkswagen": "#001E50",
  "Volvo": "#003057",
};

// Get initials from manufacturer name
function getInitials(name: string): string {
  const words = name.split(/[\s-]+/);
  if (words.length === 1) {
    return name.slice(0, 2).toUpperCase();
  }
  return words
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();
}

// Generate a consistent color from string
function stringToColor(str: string): string {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  const hue = hash % 360;
  return `hsl(${hue}, 65%, 45%)`;
}

export default function ManufacturerLogo({
  manufacturer,
  size = 24,
  className = "",
}: ManufacturerLogoProps) {
  const { initials, bgColor, textColor } = useMemo(() => {
    const initials = getInitials(manufacturer);
    const bgColor = manufacturerColors[manufacturer] || stringToColor(manufacturer);

    // Determine text color based on background luminance
    const isLightBg = ["#FFD700", "#FFD100", "#DAA520", "#D4AF37", "#CCAA00"].includes(bgColor);
    const textColor = isLightBg ? "#1a1a1a" : "#ffffff";

    return { initials, bgColor, textColor };
  }, [manufacturer]);

  return (
    <div
      className={`inline-flex items-center justify-center rounded-md font-bold ${className}`}
      style={{
        width: size,
        height: size,
        backgroundColor: bgColor,
        color: textColor,
        fontSize: size * 0.4,
        flexShrink: 0,
      }}
      title={manufacturer}
    >
      {initials}
    </div>
  );
}
