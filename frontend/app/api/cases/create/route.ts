import { NextResponse } from "next/server";
import { runCase } from "@/lib/backend/case-runner";
import { jsonError } from "@/lib/backend/api-helpers";
import type { CaseCreatePayload } from "@/lib/backend/schemas";

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as CaseCreatePayload;
    if (!body?.applicant?.name) {
      return jsonError("applicant.name is required", 422);
    }

    const result = await runCase(body.applicant);
    return NextResponse.json(result);
  } catch {
    return jsonError("Invalid request body", 400);
  }
}
