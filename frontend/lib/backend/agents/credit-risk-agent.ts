import type { AgentReport, Applicant, Contributor } from "../schemas";

export function runCreditRiskAgent(applicant: Applicant): AgentReport {
  const signals = applicant.document_signals ?? {};
  const numericHints = signals.numeric_hints ?? {};

  const effectiveUtilization = Math.max(
    applicant.credit_utilization,
    numericHints.credit_utilization ?? applicant.credit_utilization
  );
  const effectiveDelinquencies = Math.max(
    applicant.delinquencies_12m,
    numericHints.delinquencies_12m ?? applicant.delinquencies_12m
  );
  const effectiveEmploymentMonths = Math.min(
    applicant.employment_months,
    numericHints.employment_months ?? applicant.employment_months
  );

  let risk = 0.1;
  risk += effectiveUtilization * 0.35;
  risk += Math.min(effectiveDelinquencies, 4) * 0.12;
  risk +=
    effectiveEmploymentMonths < 6
      ? 0.15
      : effectiveEmploymentMonths < 12
        ? 0.07
        : -0.05;
  risk +=
    Math.min(
      applicant.existing_debt / Math.max(applicant.monthly_income * 12, 1),
      1.5
    ) * 0.15;

  const score = Math.max(0, Math.min(1, 1 - risk));

  const contributors: Contributor[] = [
    {
      feature: "credit_utilization",
      impact: Math.round(effectiveUtilization * 0.35 * 100) / 100,
      direction: "increases risk",
      explanation: `Credit utilization is ${(effectiveUtilization * 100).toFixed(0)}%.`,
    },
    {
      feature: "delinquencies_12m",
      impact: Math.round(Math.min(effectiveDelinquencies, 4) * 0.12 * 100) / 100,
      direction: "increases risk",
      explanation: `Recent delinquencies: ${effectiveDelinquencies}.`,
    },
    {
      feature: "employment_stability",
      impact: effectiveEmploymentMonths >= 12 ? -0.05 : 0.15,
      direction:
        effectiveEmploymentMonths >= 12 ? "decreases risk" : "increases risk",
      explanation: `Employment history: ${effectiveEmploymentMonths} months.`,
    },
  ];

  const reasons: string[] = [];
  if (effectiveUtilization > 0.75) reasons.push("HIGH_UTILIZATION");
  if (effectiveDelinquencies > 0) reasons.push("RECENT_DELINQUENCY");
  if (effectiveEmploymentMonths < 6) reasons.push("SHORT_EMPLOYMENT_HISTORY");
  if (Object.keys(numericHints).length) reasons.push("DOC_HINTS_APPLIED");
  if (!reasons.length) reasons.push("STABLE_CREDIT_PROFILE");

  const recommendation =
    score >= 0.74 ? "PASS" : score >= 0.45 ? "REFER" : "REJECT";

  return {
    agent_name: "Credit Risk Agent",
    score: Math.round(score * 100) / 100,
    model_version: "credit-risk-monotonic-xgb-v1",
    top_contributors: contributors,
    evidence_refs: ["credit_bureau_snapshot"],
    reason_codes: reasons,
    confidence_status: "demo_calibrated",
    recommendation,
    summary:
      "Probability-of-default style model with TreeSHAP-like reason contributions.",
  };
}
