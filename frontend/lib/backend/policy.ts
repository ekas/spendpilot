import type { AgentReport, ManagerReport, PolicyDecision } from "./schemas";

export function decide(
  reports: AgentReport[],
  manager: ManagerReport
): PolicyDecision {
  const flags: string[] = [];
  const byName = Object.fromEntries(reports.map((r) => [r.agent_name, r]));

  const data = byName["Data Credibility Agent"];
  const aff = byName["Affordability Agent"];
  const credit = byName["Credit Risk Agent"];

  if (data.score < 0.45) {
    flags.push("POLICY_REJECT_EVIDENCE_CREDIBILITY_TOO_LOW");
    return {
      final_decision: "REJECT",
      policy_flags: flags,
      requires_human_review: false,
      reason: "Evidence credibility below minimum policy threshold.",
    };
  }

  if (aff.score < 0.35) {
    flags.push("POLICY_REJECT_AFFORDABILITY_TOO_LOW");
    return {
      final_decision: "REJECT",
      policy_flags: flags,
      requires_human_review: false,
      reason: "Affordability score below minimum policy threshold.",
    };
  }

  if (credit.score < 0.35) {
    flags.push("POLICY_REJECT_CREDIT_RISK_TOO_HIGH");
    return {
      final_decision: "REJECT",
      policy_flags: flags,
      requires_human_review: false,
      reason: "Credit risk below minimum acceptance threshold.",
    };
  }

  if (
    manager.disagreements.length ||
    manager.recommendation === "REFER" ||
    reports.some((r) => r.recommendation === "REFER")
  ) {
    flags.push("POLICY_REFER_HUMAN_REVIEW_REQUIRED");
    return {
      final_decision: "REFER",
      policy_flags: flags,
      requires_human_review: true,
      reason:
        "Case requires human review due to disagreement, borderline scores, or adverse indicators.",
    };
  }

  flags.push("POLICY_APPROVE_LOW_RISK");
  return {
    final_decision: "APPROVE",
    policy_flags: flags,
    requires_human_review: false,
    reason:
      "All specialist agents passed and deterministic policy thresholds are satisfied.",
  };
}
