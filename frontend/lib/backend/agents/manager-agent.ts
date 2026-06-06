import type { AgentReport, ManagerReport } from "../schemas";

export function runManagerAgent(reports: AgentReport[]): ManagerReport {
  const recs = Object.fromEntries(
    reports.map((r) => [r.agent_name, r.recommendation])
  );
  const scores = Object.fromEntries(
    reports.map((r) => [r.agent_name, r.score])
  );
  const disagreements: string[] = [];

  if (new Set(Object.values(recs)).size > 1) {
    disagreements.push(`Agents disagree: ${JSON.stringify(recs)}`);
  }

  const scoreValues = Object.values(scores);
  if (Math.max(...scoreValues) - Math.min(...scoreValues) > 0.35) {
    disagreements.push("Large confidence gap between specialist scores.");
  }

  const requested: string[] = [];
  for (const r of reports) {
    if (r.recommendation === "REFER" && r.score < 0.55) {
      requested.push(`Request targeted re-analysis from ${r.agent_name}`);
    }
  }

  let recommendation: string;
  if (reports.some((r) => r.recommendation === "REJECT")) {
    recommendation = "REFER";
  } else if (
    disagreements.length ||
    reports.some((r) => r.recommendation === "REFER")
  ) {
    recommendation = "REFER";
  } else {
    recommendation = "APPROVE";
  }

  const allReasons = reports.flatMap((r) => r.reason_codes);
  const reviewerSummary = reports
    .map((r) => `${r.agent_name}: ${r.recommendation} (${r.score})`)
    .join(" | ");

  return {
    recommendation,
    disagreements,
    requested_reanalysis: requested,
    reviewer_summary: reviewerSummary,
    readable_explanation:
      "Manager summarizes specialist outputs only. It does not change scores or approve credit. Main reason codes: " +
      [...new Set(allReasons)].sort().join(", "),
  };
}
