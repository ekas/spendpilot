import { NextResponse } from "next/server";
import { listCases, caseCount } from "@/lib/backend/case-repository";
import { runCase } from "@/lib/backend/case-runner";
import { SAMPLE_CASES } from "@/lib/backend/sample-cases";

export async function GET() {
  const count = await caseCount();
  if (count === 0) {
    for (const sample of SAMPLE_CASES) {
      await runCase(sample);
    }
  }

  const cases = await listCases();
  return NextResponse.json(cases);
}
