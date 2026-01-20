"use client";

import { useMemo, useState } from "react";
import Image from "next/image";

interface ManufacturerLogoProps {
  manufacturer: string;
  size?: number;
  className?: string;
}

// Manufacturers that have SVG logos available (filename = lowercase with hyphens)
const manufacturersWithLogos = new Set([
  "Acura",
  "Alfa Romeo",
  "AM General",
  "Aston Martin",
  "Audi",
  "Bentley",
  "BMW",
  "Bugatti",
  "Buick",
  "Cadillac",
  "Chery",
  "Chevrolet",
  "Chrysler",
  "Citroën",
  "Cupra",
  "Dacia",
  "Daewoo",
  "Dodge",
  "Eagle",
  "Ferrari",
  "Fiat",
  "Fisker",
  "Ford",
  "Genesis",
  "Geo",
  "GMC",
  "Honda",
  "Hummer",
  "Hyundai",
  "Infiniti",
  "Isuzu",
  "Jaguar",
  "Jeep",
  "Kia",
  "Koenigsegg",
  "Lamborghini",
  "Land Rover",
  "Lexus",
  "Lincoln",
  "Lotus",
  "Lucid",
  "Maserati",
  "Maybach",
  "Mazda",
  "McLaren",
  "Mercedes-AMG",
  "Mercedes-Benz",
  "Mercury",
  "Mini",
  "Mitsubishi",
  "NIO",
  "Nissan",
  "Oldsmobile",
  "Opel",
  "Panoz",
  "Peugeot",
  "Plymouth",
  "Pontiac",
  "Porsche",
  "Ram",
  "Renault",
  "Rimac",
  "Rolls-Royce",
  "Saab",
  "Saturn",
  "Scion",
  "SEAT",
  "Skoda",
  "Smart",
  "Spyker",
  "Subaru",
  "Suzuki",
  "Tesla",
  "Toyota",
  "TVR",
  "Volkswagen",
  "Volvo",
  "Yangwang",
]);

// Map manufacturer names to logo filenames
// Default: lowercase with spaces replaced by hyphens
// Only include special cases where the default doesn't work
function getLogoFilename(manufacturer: string): string {
  const mapping: Record<string, string> = {
    // Special characters that need mapping
    "Citroën": "citroen",
    // Hyphens preserved in name but not in filename
    "Mercedes-AMG": "mercedes-amg",
    "Mercedes-Benz": "mercedes-benz",
    "Rolls-Royce": "rolls-royce",
  };

  return (
    mapping[manufacturer] ||
    manufacturer.toLowerCase().replace(/\s+/g, "-")
  );
}

// Color palette for manufacturers (used for fallback badges)
const manufacturerColors: Record<string, string> = {
  "Acura": "#1C1C1C",
  "Alfa Romeo": "#B2001B",
  "Alpine": "#0055A4",
  "AM General": "#2E4A1F",
  "Aston Martin": "#006847",
  "Audi": "#BB0A30",
  "Bentley": "#333333",
  "BMW": "#0066B1",
  "Bugatti": "#BE0030",
  "Buick": "#C0C0C0",
  "Cadillac": "#9D8B6E",
  "Chevrolet": "#D4AF37",
  "Daewoo": "#1E3A8A",
  "Dodge": "#BA0C2F",
  "Eagle": "#1E3A8A",
  "Ferrari": "#DC0000",
  "Fiat": "#8B0000",
  "Fisker": "#FF6B00",
  "Ford": "#003478",
  "Genesis": "#1C1C1C",
  "Geo": "#0055A4",
  "GMC": "#CC0000",
  "Honda": "#CC0000",
  "Hummer": "#4A4A4A",
  "Hyundai": "#002C5F",
  "Infiniti": "#1A1A1A",
  "Isuzu": "#CC0000",
  "Jaguar": "#1A472A",
  "Jeep": "#2E4A1F",
  "Kia": "#05141F",
  "Koenigsegg": "#CCAA00",
  "Lamborghini": "#DAA520",
  "Land Rover": "#005A2B",
  "Lexus": "#1A1A1A",
  "Lincoln": "#1A1A1A",
  "Lotus": "#FFD700",
  "Maserati": "#0C2340",
  "Maybach": "#1A1A1A",
  "Mazda": "#8B0000",
  "McLaren": "#FF8000",
  "Mercedes-Benz": "#00ADEF",
  "Mercedes-AMG": "#00ADEF",
  "Mini": "#000000",
  "Mitsubishi": "#ED1C24",
  "Nissan": "#C3002F",
  "Oldsmobile": "#CC0000",
  "Pagani": "#1C1C1C",
  "Panoz": "#CC0000",
  "Plymouth": "#0055A4",
  "Pontiac": "#CC0000",
  "Porsche": "#9B0E0E",
  "RAM": "#1A1A1A",
  "Renault": "#FFD100",
  "Rimac": "#00A0E3",
  "Saturn": "#4A4A4A",
  "Scion": "#1A1A1A",
  "Skoda": "#4BA82E",
  "Spyker": "#1A1A1A",
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

function FallbackBadge({
  manufacturer,
  size,
}: {
  manufacturer: string;
  size: number;
}) {
  const { initials, bgColor, textColor } = useMemo(() => {
    const initials = getInitials(manufacturer);
    const bgColor =
      manufacturerColors[manufacturer] || stringToColor(manufacturer);

    const isLightBg = [
      "#FFD700",
      "#FFD100",
      "#DAA520",
      "#D4AF37",
      "#CCAA00",
    ].includes(bgColor);
    const textColor = isLightBg ? "#1a1a1a" : "#ffffff";

    return { initials, bgColor, textColor };
  }, [manufacturer]);

  return (
    <div
      className="inline-flex items-center justify-center rounded-md font-bold"
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

export default function ManufacturerLogo({
  manufacturer,
  size = 24,
  className = "",
}: ManufacturerLogoProps) {
  const [imageError, setImageError] = useState(false);
  const hasLogo = manufacturersWithLogos.has(manufacturer);

  if (!hasLogo || imageError) {
    return <FallbackBadge manufacturer={manufacturer} size={size} />;
  }

  const logoFilename = getLogoFilename(manufacturer);

  // Logos that need to be inverted (white in light mode, black in dark mode)
  const needsInvert = ["Lucid", "Mercedes-AMG"].includes(manufacturer);

  return (
    <div
      className={`inline-flex items-center justify-center ${className}`}
      style={{ width: size, height: size, flexShrink: 0 }}
      title={manufacturer}
    >
      <Image
        src={`/logos/${logoFilename}.svg`}
        alt={`${manufacturer} logo`}
        width={size}
        height={size}
        className={`object-contain ${needsInvert ? "invert dark:invert-0" : "dark:invert"}`}
        onError={() => setImageError(true)}
      />
    </div>
  );
}
