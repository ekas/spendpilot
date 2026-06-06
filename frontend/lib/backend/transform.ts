import type { CaseResult, AgentReport as BackendAgentReport } from "./schemas";
import type {
  AnalysisResult,
  AgentId,
  AgentReport,
  AgentMessage,
  ConflictItem,
  PolicyCheck,
  SpendCategory,
  RecurringBill,
  SavingsOpportunity,
  DecisionOutcome,
  RiskLevel,
  UploadedDocument,
  DocumentType,
} from "@/lib/types";
import { inferDocumentType } from "@/lib/utils";

const AGENT_ID_MAP: Record<string, AgentId> = {
  "Data Credibility Agent": "evidence",
  "Affordability Agent": "affordability",
  "Credit Risk Agent": "credit-risk",
};

function agentIdFromName(name: string): AgentId {
  return AGENT_ID_MAP[name] ?? "manager";
}

function scoreTo100(score: number): number {
  return Math.round(score * 100);
}

function mapSeverity(reason: string): RiskLevel {
  if (
    reason.includes("FRAUD") ||
    reason.includes("REJECT") ||
    reason.includes("INVALID")
  )
    return "critical";
  if (
    reason.includes("HIGH") ||
    reason.includes("MISSING") ||
    reason.includes("UNVERIFIED") ||
    reason.includes("MISMATCH")
  )
    return "medium";
  return "low";
}

function mapDecision(status: string): DecisionOutcome {
  switch (status.toUpperCase()) {
    case "APPROVE":
      return "approved";
    case "REFER":
      return "review-required";
    case "REJECT":
      return "declined";
    default:
      return "pending";
  }
}

function transformAgentReport(report: BackendAgentReport): AgentReport {
  const agentId = agentIdFromName(report.agent_name);

  return {
    agentId,
    agentName: report.agent_name,
    status: "complete",
    completedAt: new Date().toISOString(),
    score: scoreTo100(report.score),
    confidence: 0.85,
    summary: report.summary,
    findings: report.top_contributors.map((c, i) => ({
      id: `${agentId}-f-${i}`,
      category: c.feature.replace(/_/g, " "),
      severity: c.direction.includes("increases") ? "medium" : "low",
      title: c.feature.replace(/_/g, " "),
      description: c.explanation,
      evidence: report.evidence_refs,
      confidence: 0.8,
    })),
    metrics: Object.fromEntries(
      report.top_contributors.map((c) => [c.feature, c.impact])
    ),
    reasoning: [
      ...report.reason_codes.map((r) => `Reason code: ${r}`),
      `Recommendation: ${report.recommendation}`,
      `Model: ${report.model_version}`,
    ],
  };
}

function buildAgentMessages(caseResult: CaseResult): AgentMessage[] {
  const messages: AgentMessage[] = [];
  let i = 0;

  for (const report of caseResult.specialist_reports) {
    messages.push({
      id: `msg-${i++}`,
      from: agentIdFromName(report.agent_name),
      to: "broadcast",
      timestamp: new Date().toISOString(),
      type: "analysis",
      content: `${report.agent_name}: ${report.summary} (score: ${report.score}, rec: ${report.recommendation})`,
    });
  }

  for (const disagreement of caseResult.manager_report.disagreements) {
    messages.push({
      id: `msg-${i++}`,
      from: "manager",
      to: "broadcast",
      timestamp: new Date().toISOString(),
      type: "conflict",
      content: disagreement,
    });
  }

  messages.push({
    id: `msg-${i++}`,
    from: "manager",
    to: "broadcast",
    timestamp: new Date().toISOString(),
    type: "resolution",
    content: caseResult.manager_report.readable_explanation,
  });

  return messages;
}

function buildConflicts(caseResult: CaseResult): ConflictItem[] {
  return caseResult.manager_report.disagreements.map((d, i) => ({
    id: `conf-${i}`,
    agents: caseResult.specialist_reports.map((r) =>
      agentIdFromName(r.agent_name)
    ),
    topic: "Agent disagreement",
    description: d,
    severity: "medium" as RiskLevel,
    resolution: caseResult.policy_decision.requires_human_review
      ? undefined
      : "Resolved by Manager Agent aggregation",
    resolved: !caseResult.policy_decision.requires_human_review,
  }));
}

function buildPolicyChecks(caseResult: CaseResult): PolicyCheck[] {
  const { policy_decision: policy, specialist_reports: reports } = caseResult;

  const checks: PolicyCheck[] = [
    {
      id: "pol-evidence",
      rule: "Evidence credibility above 45%",
      status:
        (reports.find((r) => r.agent_name === "Data Credibility Agent")?.score ??
          0) >= 0.45
          ? "pass"
          : "fail",
      details: `Score: ${scoreTo100(reports[0]?.score ?? 0)}`,
    },
    {
      id: "pol-affordability",
      rule: "Affordability above 35%",
      status:
        (reports.find((r) => r.agent_name === "Affordability Agent")?.score ??
          0) >= 0.35
          ? "pass"
          : "fail",
      details: `Score: ${scoreTo100(reports[1]?.score ?? 0)}`,
    },
    {
      id: "pol-credit",
      rule: "Credit risk above 35%",
      status:
        (reports.find((r) => r.agent_name === "Credit Risk Agent")?.score ??
          0) >= 0.35
          ? "pass"
          : "fail",
      details: `Score: ${scoreTo100(reports[2]?.score ?? 0)}`,
    },
  ];

  for (const flag of policy.policy_flags) {
    checks.push({
      id: `pol-${flag}`,
      rule: flag.replace(/POLICY_/g, "").replace(/_/g, " "),
      status: flag.includes("APPROVE")
        ? "pass"
        : flag.includes("REFER")
          ? "warning"
          : "fail",
      details: policy.reason,
    });
  }

  return checks;
}

function deriveSpendCategories(applicant: CaseResult["applicant"]): SpendCategory[] {
  const housing = applicant.monthly_expenses * 0.35;
  const food = applicant.monthly_expenses * 0.15;
  const transport = applicant.monthly_expenses * 0.1;
  const debt = applicant.existing_debt / 12;
  const other = applicant.monthly_expenses - housing - food - transport;

  const cats = [
    { name: "Housing", amount: housing, trend: "stable" as const },
    { name: "Food & Dining", amount: food, trend: "stable" as const },
    { name: "Transportation", amount: transport, trend: "stable" as const },
    { name: "Debt Payments", amount: debt, trend: "stable" as const },
    { name: "Other", amount: Math.max(0, other), trend: "stable" as const },
  ];

  const total = cats.reduce((s, c) => s + c.amount, 0);
  return cats.map((c) => ({
    ...c,
    percentage: total > 0 ? (c.amount / total) * 100 : 0,
    riskFlag: c.name === "Debt Payments" && debt > applicant.monthly_income * 0.15,
  }));
}

function deriveRecurringBills(applicant: CaseResult["applicant"]): RecurringBill[] {
  return [
    {
      vendor: "Estimated Housing/Rent",
      amount: Math.round(applicant.monthly_expenses * 0.35),
      frequency: "monthly",
      nextDue: new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10),
      verified: applicant.income_verified,
      duplicateRisk: false,
    },
    {
      vendor: "Debt Service",
      amount: Math.round(applicant.existing_debt / 12),
      frequency: "monthly",
      nextDue: new Date(Date.now() + 15 * 86400000).toISOString().slice(0, 10),
      verified: true,
      duplicateRisk: false,
    },
  ];
}

function deriveSavings(caseResult: CaseResult): SavingsOpportunity[] {
  const { applicant, specialist_reports: reports } = caseResult;
  const opportunities: SavingsOpportunity[] = [];
  const freeCash = applicant.monthly_income - applicant.monthly_expenses;

  if (applicant.credit_utilization > 0.5) {
    opportunities.push({
      id: "sav-util",
      title: "Reduce credit utilization",
      potentialSavings: Math.round(applicant.monthly_expenses * 0.05),
      category: "Credit",
      confidence: 0.75,
      action: `Utilization at ${(applicant.credit_utilization * 100).toFixed(0)}% — pay down balances`,
    });
  }

  if (freeCash < applicant.requested_amount / 36) {
    opportunities.push({
      id: "sav-budget",
      title: "Improve affordability buffer",
      potentialSavings: Math.round(applicant.monthly_expenses * 0.1),
      category: "Budget",
      confidence: 0.7,
      action: "Reduce discretionary spend to improve installment coverage",
    });
  }

  const missingDocs = reports[0]?.reason_codes.includes("MISSING_DOCUMENTS");
  if (missingDocs) {
    opportunities.push({
      id: "sav-docs",
      title: "Complete document submission",
      potentialSavings: 0,
      category: "Compliance",
      confidence: 0.95,
      action: "Submit missing bank statement, ID, and income proof",
    });
  }

  return opportunities;
}

function overallRiskLevel(caseResult: CaseResult): RiskLevel {
  const avg =
    caseResult.specialist_reports.reduce((s, r) => s + r.score, 0) /
    caseResult.specialist_reports.length;

  if (caseResult.status === "REJECT" || avg < 0.4) return "critical";
  if (caseResult.status === "REFER" || avg < 0.6) return "medium";
  return "low";
}

export function caseResultToAnalysis(
  caseResult: CaseResult,
  uploadedDocs?: UploadedDocument[]
): AnalysisResult {
  const { applicant } = caseResult;
  const evidence = caseResult.specialist_reports.find(
    (r) => r.agent_name === "Data Credibility Agent"
  );
  const affordability = caseResult.specialist_reports.find(
    (r) => r.agent_name === "Affordability Agent"
  );
  const credit = caseResult.specialist_reports.find(
    (r) => r.agent_name === "Credit Risk Agent"
  );

  const agentReports: AgentReport[] = [
    ...caseResult.specialist_reports.map(transformAgentReport),
    {
      agentId: "manager",
      agentName: "Manager Agent",
      status: "complete",
      completedAt: new Date().toISOString(),
      score: scoreTo100(
        caseResult.specialist_reports.reduce((s, r) => s + r.score, 0) /
          caseResult.specialist_reports.length
      ),
      confidence: 0.86,
      summary: caseResult.manager_report.reviewer_summary,
      findings: caseResult.manager_report.disagreements.map((d, i) => ({
        id: `mgr-f-${i}`,
        category: "Aggregation",
        severity: mapSeverity(d),
        title: "Agent disagreement",
        description: d,
        evidence: [],
        confidence: 0.8,
      })),
      metrics: {
        disagreements: caseResult.manager_report.disagreements.length,
        reanalysisRequests:
          caseResult.manager_report.requested_reanalysis.length,
      },
      reasoning: [
        caseResult.manager_report.reviewer_summary,
        caseResult.manager_report.readable_explanation,
        `Recommendation: ${caseResult.manager_report.recommendation}`,
      ],
    },
  ];

  const documents: UploadedDocument[] =
    uploadedDocs ??
    applicant.documents.map((name, i) => ({
      id: `doc-${i}`,
      name,
      type: inferDocumentType(name) as DocumentType,
      size: 0,
      uploadedAt: caseResult.created_at ?? new Date().toISOString(),
      status: "ready" as const,
    }));

  const savingsRate =
    applicant.monthly_income > 0
      ? (applicant.monthly_income - applicant.monthly_expenses) /
        applicant.monthly_income
      : 0;

  const dti = applicant.existing_debt / Math.max(applicant.monthly_income, 1);

  const outcome = mapDecision(caseResult.status);
  const conditions: string[] = [];

  if (caseResult.policy_decision.requires_human_review) {
    conditions.push("Human review required before final approval");
  }
  if (caseResult.manager_report.requested_reanalysis.length) {
    conditions.push(...caseResult.manager_report.requested_reanalysis);
  }

  return {
    caseId: caseResult.case_id,
    snapshot: {
      id: caseResult.case_id,
      applicantName: applicant.name,
      applicationDate: caseResult.created_at ?? new Date().toISOString(),
      documents,
      monthlyIncome: applicant.monthly_income,
      monthlyExpenses: applicant.monthly_expenses,
      debtToIncome: dti,
      savingsRate: Math.max(0, savingsRate),
      validationStatus:
        evidence?.reason_codes.includes("MISSING_DOCUMENTS") ||
        evidence?.reason_codes.includes("INVALID_FIELDS")
          ? "partial"
          : "valid",
      validationIssues: evidence?.reason_codes.filter(
        (r) => r.includes("MISSING") || r.includes("INVALID") || r.includes("MISMATCH")
      ) ?? [],
    },
    agentReports,
    agentMessages: buildAgentMessages(caseResult),
    conflicts: buildConflicts(caseResult),
    policyChecks: buildPolicyChecks(caseResult),
    credibility: {
      evidenceScore: scoreTo100(evidence?.score ?? 0),
      affordabilityScore: scoreTo100(affordability?.score ?? 0),
      creditRiskScore: scoreTo100(credit?.score ?? 0),
      overallScore: scoreTo100(
        ((evidence?.score ?? 0) +
          (affordability?.score ?? 0) +
          (credit?.score ?? 0)) /
          3
      ),
      riskLevel: overallRiskLevel(caseResult),
      confidence: 0.86,
    },
    spendCategories: deriveSpendCategories(applicant),
    recurringBills: deriveRecurringBills(applicant),
    savingsOpportunities: deriveSavings(caseResult),
    decision: {
      outcome,
      rationale: [
        caseResult.policy_decision.reason,
        caseResult.manager_report.readable_explanation,
        ...caseResult.policy_decision.policy_flags.map((f) => `Policy: ${f}`),
      ],
      conditions: conditions.length ? conditions : undefined,
      reviewedBy: "Manager Agent",
      decidedAt: caseResult.created_at ?? new Date().toISOString(),
    },
    pipelineStage: "complete",
  };
}

export function caseResultToReviewItem(caseResult: CaseResult) {
  const analysis = caseResultToAnalysis(caseResult);
  const priority =
    analysis.credibility.riskLevel === "critical"
      ? "urgent"
      : analysis.credibility.riskLevel === "high"
        ? "high"
        : caseResult.status === "REFER"
          ? "medium"
          : "low";

  return {
    id: `rev-${caseResult.case_id}`,
    caseId: caseResult.case_id,
    applicantName: caseResult.applicant.name,
    submittedAt: caseResult.created_at ?? new Date().toISOString(),
    priority: priority as "low" | "medium" | "high" | "urgent",
    reason: caseResult.policy_decision.reason,
    credibilityScore: analysis.credibility.overallScore,
    riskLevel: analysis.credibility.riskLevel,
    status: "pending" as const,
  };
}
