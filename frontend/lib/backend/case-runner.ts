import { runDataCredibilityAgent } from "./agents/data-credibility-agent";
import { runAffordabilityAgent } from "./agents/affordability-agent";
import { runCreditRiskAgent } from "./agents/credit-risk-agent";
import { runManagerAgent } from "./agents/manager-agent";
import { decide } from "./policy";
import { saveCase } from "./case-repository";
import type { Applicant, CaseResult } from "./schemas";

function generateCaseId(): string {
  return crypto.randomUUID().slice(0, 8);
}

export async function runCase(
  applicant: Applicant,
  caseId?: string
): Promise<CaseResult> {
  const id = caseId ?? generateCaseId();

  const reports = [
    runDataCredibilityAgent(applicant),
    runAffordabilityAgent(applicant),
    runCreditRiskAgent(applicant),
  ];

  const manager = runManagerAgent(reports);
  const policy = decide(reports, manager);

  const result: CaseResult = {
    case_id: id,
    applicant,
    status: policy.final_decision,
    specialist_reports: reports,
    manager_report: manager,
    policy_decision: policy,
    created_at: new Date().toISOString(),
  };

  await saveCase(result);
  return result;
}
