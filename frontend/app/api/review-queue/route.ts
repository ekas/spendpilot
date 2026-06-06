import { NextResponse } from "next/server";
import { listReviewQueue, caseCount } from "@/lib/backend/case-repository";
import { runCase } from "@/lib/backend/case-runner";
import { SAMPLE_CASES } from "@/lib/backend/sample-cases";
import { caseResultToReviewItem } from "@/lib/backend/transform";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const format = url.searchParams.get("format");

  const count = await caseCount();
  if (count === 0) {
    for (const sample of SAMPLE_CASES) {
      await runCase(sample);
    }
  }

  const cases = await listReviewQueue();

  if (format === "backend") {
    return NextResponse.json(cases);
  }

  return NextResponse.json(cases.map(caseResultToReviewItem));
}
