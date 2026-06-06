import { NextResponse } from "next/server";
import { runCase } from "@/lib/backend/case-runner";
import { SAMPLE_CASES } from "@/lib/backend/sample-cases";

export async function GET() {
  const results = await Promise.all(
    SAMPLE_CASES.map((sample) => runCase(sample))
  );
  return NextResponse.json(results);
}
