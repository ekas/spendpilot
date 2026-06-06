import { NextResponse } from "next/server";
import { setHumanDecision } from "@/lib/backend/case-repository";
import { jsonError } from "@/lib/backend/api-helpers";

const VALID = new Set(["APPROVE", "REJECT", "REFER"]);

export async function POST(
  request: Request,
  { params }: { params: Promise<{ caseId: string }> }
) {
  const { caseId } = await params;
  const url = new URL(request.url);
  let decision = url.searchParams.get("decision")?.toUpperCase();

  if (!decision) {
    try {
      const body = await request.json();
      const raw = body.decision as string;
      decision = mapFrontendDecision(raw)?.toUpperCase() ?? raw?.toUpperCase();
    } catch {
      // query param only
    }
  }

  if (!decision || !VALID.has(decision)) {
    return jsonError("decision must be one of APPROVE, REJECT, REFER", 422);
  }

  const updated = await setHumanDecision(caseId, decision);
  if (!updated) {
    return jsonError("Case not found", 404);
  }

  return NextResponse.json({
    case_id: caseId,
    human_decision: decision,
    message: "Human reviewer decision recorded.",
    case: updated,
  });
}

function mapFrontendDecision(
  decision: string
): "APPROVE" | "REJECT" | "REFER" | null {
  switch (decision?.toLowerCase()) {
    case "approve":
      return "APPROVE";
    case "override":
    case "challenge":
      return "REFER";
    case "reject":
    case "decline":
      return "REJECT";
    default:
      return null;
  }
}
