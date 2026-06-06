import { NextResponse } from "next/server";
import { getCase } from "@/lib/backend/case-repository";
import { caseResultToAnalysis } from "@/lib/backend/transform";
import { jsonError } from "@/lib/backend/api-helpers";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ caseId: string }> }
) {
  const { caseId } = await params;
  const caseResult = await getCase(caseId);

  if (!caseResult) {
    return jsonError("Case not found", 404);
  }

  const accept = _request.headers.get("accept") ?? "";
  if (accept.includes("application/vnd.spendpilot.analysis")) {
    return NextResponse.json(caseResultToAnalysis(caseResult));
  }

  const url = new URL(_request.url);
  if (url.searchParams.get("format") === "analysis") {
    return NextResponse.json(caseResultToAnalysis(caseResult));
  }

  return NextResponse.json(caseResult);
}
