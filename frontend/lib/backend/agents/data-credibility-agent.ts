import type { AgentReport, Applicant, Contributor } from "../schemas";

export function runDataCredibilityAgent(applicant: Applicant): AgentReport {
  let score = 0.85;
  const reasons: string[] = [];
  const contributors: Contributor[] = [];
  const refs = applicant.documents.length ? applicant.documents : ["application_form"];
  const signals = applicant.document_signals ?? {};
  const numericHints = signals.numeric_hints ?? {};
  const consistencyFlags = signals.consistency_flags ?? [];
  const coverageScore = signals.coverage_score ?? 0;

  const required = ["bank_statement", "id_document", "income_proof"];
  const missing = required.filter(
    (d) => !applicant.documents.some((x) => x.toLowerCase().includes(d))
  );

  if (missing.length) {
    score -= 0.12 * missing.length;
    reasons.push("MISSING_DOCUMENTS");
    contributors.push({
      feature: "missing_documents",
      impact: 0.12 * missing.length,
      direction: "increases risk",
      explanation: `Missing: ${missing.join(", ")}`,
    });
  }

  if (!applicant.income_verified) {
    score -= 0.18;
    reasons.push("UNVERIFIED_INCOME");
    contributors.push({
      feature: "income_verified",
      impact: 0.18,
      direction: "increases risk",
      explanation: "Income has not been verified by supplied documents.",
    });
  }

  if (applicant.monthly_income <= 0 || applicant.requested_amount <= 0) {
    score -= 0.25;
    reasons.push("INVALID_FIELDS");
    contributors.push({
      feature: "field_validation",
      impact: 0.25,
      direction: "increases risk",
      explanation: "Application contains invalid financial fields.",
    });
  }

  if (coverageScore < 0.25 && applicant.documents.length) {
    score -= 0.1;
    reasons.push("LOW_DOCUMENT_COVERAGE");
    contributors.push({
      feature: "document_coverage",
      impact: 0.1,
      direction: "increases risk",
      explanation:
        "Uploaded documents provided limited machine-readable financial signals.",
    });
  }

  if (consistencyFlags.length) {
    const impact = Math.min(0.2, 0.08 * consistencyFlags.length);
    score -= impact;
    reasons.push(...consistencyFlags);
    contributors.push({
      feature: "document_consistency",
      impact,
      direction: "increases risk",
      explanation: "Detected potential inconsistencies in uploaded documents.",
    });
  }

  const hintedIncome = numericHints.monthly_income;
  if (hintedIncome && applicant.monthly_income > 0) {
    const deltaRatio =
      Math.abs(hintedIncome - applicant.monthly_income) /
      applicant.monthly_income;
    if (deltaRatio > 0.2) {
      score -= 0.12;
      reasons.push("INCOME_MISMATCH_WITH_DOCUMENTS");
      contributors.push({
        feature: "income_mismatch",
        impact: 0.12,
        direction: "increases risk",
        explanation:
          "Document-extracted income materially differs from provided application income.",
      });
    }
  }

  score = Math.max(0, Math.min(1, score));
  const recommendation =
    score >= 0.7 ? "PASS" : score >= 0.45 ? "REFER" : "REJECT";

  if (!contributors.length) {
    contributors.push({
      feature: "complete_evidence",
      impact: -0.1,
      direction: "decreases risk",
      explanation: "Required documents are present and internally consistent.",
    });
    reasons.push("EVIDENCE_COMPLETE");
  }

  return {
    agent_name: "Data Credibility Agent",
    score: Math.round(score * 100) / 100,
    model_version: "data-credibility-rules-xgb-v1",
    top_contributors: contributors.slice(0, 3),
    evidence_refs: refs,
    reason_codes: reasons,
    confidence_status: "demo_calibrated",
    recommendation,
    summary:
      "Validates missing documents, inconsistent fields, and basic fraud/inconsistency indicators.",
  };
}
