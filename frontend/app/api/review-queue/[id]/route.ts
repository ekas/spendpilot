import { NextResponse } from "next/server";
import { setHumanDecision } from "@/lib/backend/case-repository";
import { jsonError } from "@/lib/backend/api-helpers";

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const caseId = id.replace(/^rev-/, "");

  let decision = "REFER";
  let notes: string | undefined;

  try {
    const body = await request.json();
    notes = body.notes;

    switch (body.decision?.toLowerCase()) {
      case "approve":
        decision = "APPROVE";
        break;
      case "challenge":
        decision = "REFER";
        break;
      case "override":
        decision = "APPROVE";
        break;
      case "reject":
      case "decline":
        decision = "REJECT";
        break;
    }
  } catch {
    return jsonError("Invalid request body", 400);
  }

  const updated = await setHumanDecision(caseId, decision);
  if (!updated) {
    return jsonError("Case not found", 404);
  }

  return NextResponse.json({
    id,
    case_id: caseId,
    decision,
    notes,
    message: "Review decision recorded.",
  });
}
