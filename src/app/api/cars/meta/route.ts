import { NextResponse } from "next/server";
import { getMeta } from "@/lib/db";

export async function GET() {
  try {
    const meta = getMeta();
    return NextResponse.json(meta);
  } catch (error) {
    console.error("Error fetching metadata:", error);
    return NextResponse.json(
      { error: "Failed to fetch metadata" },
      { status: 500 }
    );
  }
}
