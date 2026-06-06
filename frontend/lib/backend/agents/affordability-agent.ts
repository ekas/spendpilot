import type { AgentReport, Applicant, Contributor } from "../schemas";

export function runAffordabilityAgent(applicant: Applicant): AgentReport {
  const signals = applicant.document_signals ?? {};
  const numericHints = signals.numeric_hints ?? {};

  const effectiveIncome = Math.min(
    applicant.monthly_income,
    numericHints.monthly_income ?? applicant.monthly_income
  );
  const effectiveExpenses = Math.max(
    applicant.monthly_expenses,
    numericHints.monthly_expenses ?? applicant.monthly_expenses
  );
  const effectiveDebt = Math.max(
    applicant.existing_debt,
    numericHints.existing_debt ?? applicant.existing_debt
  );

  const freeCashFlow = effectiveIncome - effectiveExpenses;
  const dti = effectiveDebt / Math.max(effectiveIncome, 1);
  const installmentProxy = applicant.requested_amount / 36;
  const burden = installmentProxy / Math.max(freeCashFlow, 1);

  let risk =
    0.15 +
    Math.min(dti, 1.5) * 0.35 +
    Math.min(burden, 2.0) * 0.25 +
    Math.min(applicant.overdrafts_90d, 5) * 0.04;

  if (applicant.income_verified) risk -= 0.08;
  if (freeCashFlow > installmentProxy * 2) risk -= 0.1;

  const score = Math.max(0, Math.min(1, 1 - risk));

  const contributors: Contributor[] = [
    {
      feature: "debt_to_income_ratio",
      impact: Math.round(Math.min(dti, 1.5) * 0.35 * 100) / 100,
      direction: "increases risk",
      explanation: `Debt-to-income ratio is ${dti.toFixed(2)}.`,
    },
    {
      feature: "free_cash_flow",
      impact:
        freeCashFlow > installmentProxy * 2
          ? -0.1
          : 0.12,
      direction:
        freeCashFlow > installmentProxy * 2
          ? "decreases risk"
          : "increases risk",
      explanation: `Estimated free cash flow is $${freeCashFlow.toFixed(0)}.`,
    },
    {
      feature: "overdrafts_90d",
      impact: Math.round(Math.min(applicant.overdrafts_90d, 5) * 0.04 * 100) / 100,
      direction: "increases risk",
      explanation: `Overdraft count in last 90 days: ${applicant.overdrafts_90d}.`,
    },
  ];

  const reasons: string[] = [];
  if (dti > 0.45) reasons.push("HIGH_DTI");
  if (burden > 0.6) reasons.push("LOW_AFFORDABILITY_BUFFER");
  if (applicant.overdrafts_90d >= 2) reasons.push("RECENT_OVERDRAFTS");
  if (Object.keys(numericHints).length) reasons.push("DOC_HINTS_APPLIED");
  if (!reasons.length) reasons.push("AFFORDABILITY_BUFFER_OK");

  const recommendation =
    score >= 0.72 ? "PASS" : score >= 0.45 ? "REFER" : "REJECT";

  return {
    agent_name: "Affordability Agent",
    score: Math.round(score * 100) / 100,
    model_version: "affordability-monotonic-xgb-v1",
    top_contributors: contributors,
    evidence_refs: ["bank_statement", "income_proof"],
    reason_codes: reasons,
    confidence_status: "demo_calibrated",
    recommendation,
    summary:
      "Monotonic affordability model: risk rises with DTI, burden, overdrafts and falls with verified income/free cash flow.",
  };
}
