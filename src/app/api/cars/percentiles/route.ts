import { NextResponse } from "next/server";
import { getPercentiles } from "@/lib/db";

export async function GET() {
  try {
    const percentiles = getPercentiles();
    return NextResponse.json(percentiles);
  } catch (error) {
    console.error("Error fetching percentiles:", error);
    return NextResponse.json(
      { error: "Failed to fetch percentile data" },
      { status: 500 }
    );
  }
}
