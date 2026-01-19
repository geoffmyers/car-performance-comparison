"use client";

import { countryNames } from "@/types/car";

interface CountryFlagProps {
  countryCode: string;
  showName?: boolean;
  size?: "sm" | "md" | "lg";
  className?: string;
}

// Convert ISO 3166-1 alpha-2 country code to flag emoji
// Works by converting each letter to its regional indicator symbol
function countryCodeToEmoji(countryCode: string): string {
  if (!countryCode || countryCode.length !== 2) return "";

  const codePoints = countryCode
    .toUpperCase()
    .split("")
    .map((char) => 127397 + char.charCodeAt(0));

  return String.fromCodePoint(...codePoints);
}

const sizeClasses = {
  sm: "text-base",
  md: "text-xl",
  lg: "text-2xl",
};

export default function CountryFlag({
  countryCode,
  showName = false,
  size = "md",
  className = "",
}: CountryFlagProps) {
  if (!countryCode) {
    return <span className="text-zinc-400">—</span>;
  }

  const emoji = countryCodeToEmoji(countryCode);
  const name = countryNames[countryCode] || countryCode;

  return (
    <div className={`inline-flex items-center gap-1.5 ${className}`}>
      <span
        className={`${sizeClasses[size]} leading-none`}
        role="img"
        aria-label={name}
        title={name}
      >
        {emoji}
      </span>
      {showName && (
        <span className="text-sm text-zinc-700 dark:text-zinc-300">{name}</span>
      )}
    </div>
  );
}
