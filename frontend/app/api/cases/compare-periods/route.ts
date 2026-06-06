import { NextResponse } from "next/server";
import {
  listCasesBetween,
  summarizePeriod,
} from "@/lib/backend/case-repository";
import { jsonError } from "@/lib/backend/api-helpers";

function toTsRange(start: string, end: string): [string, string] {
  const startDt = new Date(`${start}T00:00:00.000Z`);
  const endDt = new Date(`${end}T00:00:00.000Z`);
  endDt.setUTCDate(endDt.getUTCDate() + 1);
  return [startDt.toISOString(), endDt.toISOString()];
}

export async function GET(request: Request) {
  const url = new URL(request.url);
  const periodAStart = url.searchParams.get("period_a_start");
  const periodAEnd = url.searchParams.get("period_a_end");
  const periodBStart = url.searchParams.get("period_b_start");
  const periodBEnd = url.searchParams.get("period_b_end");

  if (!periodAStart || !periodAEnd || !periodBStart || !periodBEnd) {
    return jsonError(
      "period_a_start, period_a_end, period_b_start, period_b_end are required",
      422
    );
  }

  if (periodAEnd < periodAStart || periodBEnd < periodBStart) {
    return jsonError("end date must be on or after start date", 422);
  }

  const [aStart, aEnd] = toTsRange(periodAStart, periodAEnd);
  const [bStart, bEnd] = toTsRange(periodBStart, periodBEnd);

  const casesA = await listCasesBetween(aStart, aEnd);
  const casesB = await listCasesBetween(bStart, bEnd);

  const summaryA = summarizePeriod(casesA, periodAStart, periodAEnd);
  const summaryB = summarizePeriod(casesB, periodBStart, periodBEnd);

  return NextResponse.json({
    period_a: summaryA,
    period_b: summaryB,
    delta: {
      total_cases: summaryB.total_cases - summaryA.total_cases,
      approve_rate:
        Math.round(
          (summaryB.decision_rates.APPROVE - summaryA.decision_rates.APPROVE) *
            10000
        ) / 10000,
      refer_rate:
        Math.round(
          (summaryB.decision_rates.REFER - summaryA.decision_rates.REFER) *
            10000
        ) / 10000,
      reject_rate:
        Math.round(
          (summaryB.decision_rates.REJECT - summaryA.decision_rates.REJECT) *
            10000
        ) / 10000,
      human_review_rate:
        Math.round(
          (summaryB.human_review_rate - summaryA.human_review_rate) * 10000
        ) / 10000,
    },
  });
}
