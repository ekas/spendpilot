import type { AnalysisResult, AgentReport, PolicyCheck } from "./types";

export const CATEGORY_COLORS = [
  "#8b5cf6",
  "#3b82f6",
  "#14b8a6",
  "#f43f5e",
  "#f97316",
  "#6b7280",
  "#d1d5db",
  "#a855f7",
  "#06b6d4",
];

export function getSpendByCategory(analysis: AnalysisResult) {
  return analysis.spendCategories.map((cat, i) => ({
    name: cat.name,
    value: cat.amount,
    percentage: cat.percentage,
    color: CATEGORY_COLORS[i % CATEGORY_COLORS.length],
  }));
}

export function getSpendOverTime(analysis: AnalysisResult) {
  const months = ["Nov '23", "Dec '23", "Jan '24", "Feb '24", "Mar '24", "Apr '24"];
  const topCategories = analysis.spendCategories.slice(0, 5);

  return months.map((month, mi) => {
    const row: Record<string, string | number> = { month };
    topCategories.forEach((cat, ci) => {
      const growth = cat.trend === "up" ? 1 + mi * 0.04 : cat.trend === "down" ? 1 - mi * 0.02 : 1;
      const base = cat.amount * (0.85 + ci * 0.03);
      row[cat.name] = Math.round(base * growth);
    });
    if (analysis.spendCategories.length > 5) {
      const other = analysis.spendCategories.slice(5).reduce((s, c) => s + c.amount, 0);
      row["Other"] = Math.round(other * (0.9 + mi * 0.01));
    }
    return row;
  });
}

export function getAgentRecommendation(score: number): "APPROVE" | "REFER" | "REJECT" {
  if (score >= 70) return "APPROVE";
  if (score >= 45) return "REFER";
  return "REJECT";
}

export function getDecisionEvolution(analysis: AnalysisResult) {
  const evidence = analysis.agentReports.find((r) => r.agentId === "evidence");
  const affordability = analysis.agentReports.find((r) => r.agentId === "affordability");
  const credit = analysis.agentReports.find((r) => r.agentId === "credit-risk");
  const overall = analysis.credibility.overallScore;

  return [
    { stage: "Application Received", value: Math.min(95, overall + 15) },
    { stage: "After Credibility", value: evidence?.score ?? overall },
    { stage: "After Affordability", value: affordability?.score ?? overall - 10 },
    { stage: "After Risk Assessment", value: credit?.score ?? overall - 20 },
    { stage: "Policy Engine", value: overall },
  ];
}

export function getCounterfactualImpact(analysis: AnalysisResult) {
  const base = analysis.credibility.overallScore;
  const savings = analysis.savingsOpportunities.reduce(
    (s, o) => s + o.potentialSavings,
    0
  );

  return [
    { scenario: "Current", value: base, isCurrent: true },
    {
      scenario: "Provide Missing Docs",
      value: Math.min(95, base + 18),
    },
    {
      scenario: "Reduce Utilization",
      value: Math.min(95, base + 34),
    },
    {
      scenario: "Increase Income",
      value: Math.min(95, base + 53),
    },
    {
      scenario: "Increase Savings",
      value: Math.min(95, base + Math.round(savings / 10) + 20),
    },
  ];
}

export function getRiskDrivers(analysis: AnalysisResult) {
  return analysis.agentReports
    .flatMap((r) =>
      r.findings.map((f) => ({
        name: f.title.length > 28 ? f.title.slice(0, 28) + "…" : f.title,
        impact:
          f.severity === "critical"
            ? 0.32
            : f.severity === "high"
              ? 0.24
              : f.severity === "medium"
                ? 0.15
                : -0.09,
        positive: f.severity === "low",
      }))
    )
    .slice(0, 6);
}

export function getReasonCodes(analysis: AnalysisResult) {
  const codes = new Map<string, number>();
  for (const report of analysis.agentReports) {
    for (const finding of report.findings) {
      const code = finding.category
        .toUpperCase()
        .replace(/\s+/g, "_")
        .replace(/[^A-Z0-9_]/g, "");
      if (code) codes.set(code, (codes.get(code) ?? 0) + 1);
    }
    for (const step of report.reasoning) {
      const match = step.match(/Reason code: (\w+)/i);
      if (match) codes.set(match[1].toUpperCase(), (codes.get(match[1].toUpperCase()) ?? 0) + 1);
    }
  }

  if (analysis.policyChecks) {
    for (const check of analysis.policyChecks) {
      if (check.status === "fail") {
        const code = check.rule.toUpperCase().replace(/\s+/g, "_").slice(0, 24);
        codes.set(code, (codes.get(code) ?? 0) + 1);
      }
    }
  }

  const entries = Array.from(codes.entries()).map(([name, value]) => ({
    name,
    value,
  }));

  if (!entries.length) {
    return [
      { name: "STABLE_PROFILE", value: 1 },
      { name: "VERIFIED_INCOME", value: 1 },
    ];
  }

  return entries.slice(0, 8);
}

export function getManagerSummary(analysis: AnalysisResult) {
  const manager = analysis.agentReports.find((r) => r.agentId === "manager");
  const specialist = analysis.agentReports.filter((r) => r.agentId !== "manager");
  const recs = specialist.map((r) => getAgentRecommendation(r.score));
  const uniqueRecs = new Set(recs);
  const disagreement =
    uniqueRecs.size > 1
      ? Math.min(95, 50 + analysis.conflicts.length * 15 + (uniqueRecs.size - 1) * 20)
      : analysis.conflicts.length * 20;

  const recommendation =
    analysis.decision.outcome === "approved"
      ? "APPROVE"
      : analysis.decision.outcome === "declined"
        ? "REJECT"
        : "REFER";

  return {
    recommendation,
    confidence: Math.round(analysis.credibility.confidence * 100),
    summary:
      manager?.summary ??
      analysis.decision.rationale[0] ??
      "Aggregated specialist agent outputs.",
    disagreementScore: disagreement,
  };
}

export function mapAgentDisplay(report: AgentReport) {
  const configs: Record<
    string,
    { title: string; description: string; color: string; barColor: string }
  > = {
    evidence: {
      title: "Data Credibility Agent",
      description: "Validates documents, consistency, and fraud signals.",
      color: "text-violet-600 dark:text-violet-500",
      barColor: "bg-violet-500",
    },
    affordability: {
      title: "Affordability Agent",
      description: "Assesses ability to repay and cash flow stability.",
      color: "text-emerald-600 dark:text-emerald-500",
      barColor: "bg-emerald-500",
    },
    "credit-risk": {
      title: "Credit Risk Agent",
      description: "Evaluates default risk and credit behavior.",
      color: "text-amber-600 dark:text-amber-500",
      barColor: "bg-amber-500",
    },
  };

  const config = configs[report.agentId] ?? {
    title: report.agentName,
    description: report.summary,
    color: "text-accent",
    barColor: "bg-accent",
  };

  const issues = report.findings.slice(0, 3).map((f) => ({
    label: f.title,
    impact:
      f.severity === "critical"
        ? 0.24
        : f.severity === "high"
          ? 0.18
          : f.severity === "medium"
            ? 0.12
            : 0.08,
  }));

  const tags = report.findings
    .map((f) =>
      f.category.toUpperCase().replace(/\s+/g, "_").slice(0, 28)
    )
    .slice(0, 3);

  return {
    ...config,
    score: report.score,
    recommendation: getAgentRecommendation(report.score),
    issues,
    tags,
  };
}

export function formatPolicyResult(check: PolicyCheck): "Pass" | "Fail" | "Warning" {
  if (check.status === "pass") return "Pass";
  if (check.status === "warning") return "Warning";
  return "Fail";
}
