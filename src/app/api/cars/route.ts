import { NextRequest, NextResponse } from "next/server";
import { getCars } from "@/lib/db";
import { carsQuerySchema } from "@/lib/schemas";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);

    const rawParams = {
      page: searchParams.get("page") || undefined,
      pageSize: searchParams.get("pageSize") || undefined,
      sortBy: searchParams.get("sortBy") || undefined,
      sortOrder: searchParams.get("sortOrder") || undefined,
      manufacturer: searchParams.get("manufacturer") || undefined,
      country: searchParams.get("country") || undefined,
      yearMin: searchParams.get("yearMin") || undefined,
      yearMax: searchParams.get("yearMax") || undefined,
      search: searchParams.get("search") || undefined,
      source: searchParams.get("source") || undefined,
      // New categorical filters
      bodyStyle: searchParams.get("bodyStyle") || undefined,
      propulsion: searchParams.get("propulsion") || undefined,
      engineType: searchParams.get("engineType") || undefined,
      engineAspiration: searchParams.get("engineAspiration") || undefined,
      enginePlacement: searchParams.get("enginePlacement") || undefined,
      drivetrain: searchParams.get("drivetrain") || undefined,
      // Threshold filters
      displacementMin: searchParams.get("displacementMin") || undefined,
      powerMin: searchParams.get("powerMin") || undefined,
      torqueMin: searchParams.get("torqueMin") || undefined,
      weightMax: searchParams.get("weightMax") || undefined,
      powerToWeightMax: searchParams.get("powerToWeightMax") || undefined,
      accel060Max: searchParams.get("accel060Max") || undefined,
      quarterMileMax: searchParams.get("quarterMileMax") || undefined,
      topSpeedMin: searchParams.get("topSpeedMin") || undefined,
    };

    const params = carsQuerySchema.parse(rawParams);
    const result = getCars(params);

    return NextResponse.json(result);
  } catch (error) {
    console.error("Error fetching cars:", error);

    if (error instanceof Error && error.name === "ZodError") {
      return NextResponse.json(
        { error: "Invalid query parameters", details: error.message },
        { status: 400 }
      );
    }

    return NextResponse.json(
      { error: "Failed to fetch cars data" },
      { status: 500 }
    );
  }
}
