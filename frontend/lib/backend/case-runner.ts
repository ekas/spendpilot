import { runDataCredibilityAgent } from "./agents/data-credibility-agent";
import { runAffordabilityAgent } from "./agents/affordability-agent";
import { runCreditRiskAgent } from "./agents/credit-risk-agent";
import { runManagerAgent } from "./agents/manager-agent";
import { decide } from "./policy";
import { saveCase } from "./case-repository";
import { runPythonModelingCase } from "./modeling-client";
import type { Applicant, CaseResult } from "./schemas";

function generateCaseId(): string {
  return crypto.randomUUID().slice(0, 8);
}

export async function runCase(
  applicant: Applicant,
  caseId?: string
): Promise<CaseResult> {
  const id = caseId ?? generateCaseId();

  let result: CaseResult;
  try {
    result = await runPythonModelingCase(applicant, id);
  } catch (error) {
    if (process.env.SPENDPILOT_ALLOW_TYPESCRIPT_FALLBACK !== "true") {
      const message =
        error instanceof Error ? error.message : "Modeling API unavailable";
      throw new Error(
        `${message} Start the FastAPI backend on port 8000, or set ` +
          "SPENDPILOT_ALLOW_TYPESCRIPT_FALLBACK=true for the demo fallback."
      );
    }
    console.warn("Using TypeScript agent fallback:", error);
    result = runTypeScriptFallback(applicant, id);
  }

  await saveCase(result);
  return result;
}

function runTypeScriptFallback(
  applicant: Applicant,
  caseId: string
): CaseResult {
  const reports = [
    runDataCredibilityAgent(applicant),
    runAffordabilityAgent(applicant),
    runCreditRiskAgent(applicant),
  ];
  const manager = runManagerAgent(reports);
  const policy = decide(reports, manager);

  return {
    case_id: caseId,
    applicant,
    status: policy.final_decision,
    specialist_reports: reports,
    manager_report: manager,
    policy_decision: policy,
    created_at: new Date().toISOString(),
  };
}
