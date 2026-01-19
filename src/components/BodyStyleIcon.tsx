"use client";

import Image from "next/image";

// Map body style values to image file names
const bodyStyleImages: Record<string, string> = {
  Convertible: "convertible.png",
  Coupe: "coupe.png",
  Crossover: "crossover.png",
  Hatchback: "hatchback.png",
  Roadster: "sports-car.png",
  SUV: "suv.png",
  Sedan: "sedan.png",
  Targa: "sports-car.png",
  Truck: "truck.png",
  Van: "van.png",
  Wagon: "wagon.png",
};

interface BodyStyleIconProps {
  bodyStyle: string;
  size?: number;
  className?: string;
}

export default function BodyStyleIcon({
  bodyStyle,
  size = 24,
  className = "",
}: BodyStyleIconProps) {
  const imageName = bodyStyleImages[bodyStyle];

  if (!imageName) {
    return null;
  }

  return (
    <Image
      src={`/images/${imageName}`}
      alt={bodyStyle}
      width={size}
      height={size}
      className={`inline-block object-contain ${className}`}
      style={{ width: size, height: size }}
    />
  );
}
