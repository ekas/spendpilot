import type { CaseResult, AgentReport as BackendAgentReport } from "./schemas";
import type {
  AnalysisResult,
  AgentId,
  AgentReport,
  DecisionOutcome,
  HumanReviewItem,
  RiskLevel,
} from "@/lib/types";

const AGENT_ID_MAP: Record<string, AgentId> = {
  credibility: "evidence",
  affordability: "affordability",
  credit_risk: "credit-risk",
};

function recommendation(value: string): "APPROVE" | "REFER" | "REJECT" {
  if (value === "APPROVE") return "APPROVE";
  if (value === "REJECT" || value === "DECLINE") return "REJECT";
  return "REFER";
}

function decisionOutcome(value: string): DecisionOutcome {
  if (value === "APPROVE") return "approved";
  if (value === "REJECT") return "declined";
  return "review-required";
}

function transformAgentReport(report: BackendAgentReport): AgentReport {
  const agentId =
    AGENT_ID_MAP[report.agent_id ?? ""] ??
    (report.agent_name === "Data Credibility Agent"
      ? "evidence"
      : report.agent_name === "Affordability Agent"
        ? "affordability"
        : "credit-risk");

  return {
    agentId,
    agentName: report.agent_name,
    status: "complete",
    reportId: report.report_id ?? null,
    analysisRoundId: report.analysis_round_id ?? null,
    adverseRisk: report.score,
    calibratedProbability: report.calibrated_probability ?? null,
    confidence: report.confidence ?? null,
    recommendation: recommendation(report.recommendation),
    summary: report.summary,
    reasonCodes: report.reason_codes,
    evidenceRefs: report.evidence_refs,
    contributions: report.top_contributors.map((contribution) => ({
      feature: contribution.feature,
      label:
        contribution.feature_label ??
        contribution.feature.replaceAll("_", " "),
      value: contribution.value ?? null,
      impact: contribution.impact,
      direction:
        contribution.impact > 0
          ? "increases risk"
          : contribution.impact < 0
            ? "reduces risk"
            : "neutral",
      explanation: contribution.explanation,
      reasonCode: contribution.reason_code ?? null,
      evidenceRefs: contribution.evidence_refs ?? report.evidence_refs,
    })),
    modelName: report.model_name ?? report.agent_name,
    modelVersion: report.model_version,
    modelSource: report.model_source ?? null,
    limitations: report.limitations ?? [],
  };
}

function requireUnderwriting(caseResult: CaseResult) {
  if (
    !caseResult.case_context ||
    !caseResult.submitted_data ||
    !caseResult.derived_features ||
    !caseResult.evidence ||
    !caseResult.audit_bundle
  ) {
    throw new Error(
      "The modeling API returned a legacy response without underwriting data."
    );
  }
  return {
    context: caseResult.case_context,
    submitted: caseResult.submitted_data,
    derived: caseResult.derived_features,
    evidence: caseResult.evidence,
    audit: caseResult.audit_bundle,
  };
}

export function caseResultToAnalysis(caseResult: CaseResult): AnalysisResult {
  const { context, submitted, derived, evidence, audit } =
    requireUnderwriting(caseResult);
  const policy = caseResult.policy_decision;
  const manager = caseResult.manager_report;
  const label = recommendation(policy.final_decision);

  return {
    caseId: caseResult.case_id,
    caseContext: {
      snapshotId: context.snapshot_id,
      snapshotHash: context.snapshot_hash,
      analysisRoundId: context.analysis_round_id,
      decisionId: context.decision_id,
      applicantRef: context.applicant_ref,
      currency: "EUR",
      createdAt: context.created_at,
    },
    applicantName: caseResult.applicant.name,
    submittedData: {
      monthlyIncome: submitted.monthly_income,
      monthlyExpenses: submitted.monthly_expenses,
      requestedAmount: submitted.requested_amount,
      existingDebt: submitted.existing_debt,
      creditUtilization: submitted.credit_utilization,
      delinquencies12m: submitted.delinquencies_12m,
      employmentMonths: submitted.employment_months,
      overdrafts90d: submitted.overdrafts_90d,
      incomeVerified: submitted.income_verified,
    },
    derivedFeatures: {
      effectiveMonthlyIncome: derived.effective_monthly_income,
      effectiveMonthlyExpenses: derived.effective_monthly_expenses,
      effectiveExistingDebt: derived.effective_existing_debt,
      effectiveCreditUtilization: derived.effective_credit_utilization,
      effectiveDelinquencies12m: derived.effective_delinquencies_12m,
      effectiveEmploymentMonths: derived.effective_employment_months,
      freeCashFlow: derived.free_cash_flow,
      expenseRatio: derived.expense_ratio,
      debtToMonthlyIncome: derived.debt_to_monthly_income,
      estimatedInstallment36m: derived.estimated_installment_36m,
      installmentBurden: derived.installment_burden,
    },
    evidence: {
      documentCount: evidence.document_count,
      evidenceRefs: evidence.evidence_refs,
      coverageScore: evidence.coverage_score,
      missingDocuments: evidence.missing_documents,
      consistencyFindings: evidence.consistency_findings,
      consistencyFlagCount: evidence.consistency_flag_count,
      unreadableDocumentCount: evidence.unreadable_document_count,
      verificationState: evidence.verification_state,
      incomeVerified: evidence.income_verified,
    },
    agentReports: caseResult.specialist_reports.map(transformAgentReport),
    policyChecks: (policy.policy_rules ?? []).map((rule) => ({
      id: rule.rule_id,
      rule: rule.rule_id.replaceAll("_", " "),
      status:
        rule.rule_id === "UNANIMOUS_AUTOMATIC_APPROVAL"
          ? "pass"
          : policy.requires_human_review
            ? "warning"
            : label === "REJECT"
              ? "fail"
              : "pass",
      details: rule.description,
    })),
    manager: {
      recommendation: recommendation(manager.recommendation),
      disagreement:
        manager.disagreement ?? manager.disagreements.length > 0,
      disagreements: manager.disagreements,
      requestedReanalysis: manager.requested_reanalysis,
      summary: manager.reviewer_summary,
      explanation: manager.readable_explanation,
      assistantStatus: manager.assistant_status ?? null,
      requiresHumanReview:
        manager.requires_human_review ?? policy.requires_human_review,
      reasonCodes: manager.reason_codes ?? [],
    },
    decision: {
      outcome: decisionOutcome(policy.final_decision),
      label,
      reason: policy.reason,
      finalAuthority:
        policy.final_authority ?? "Deterministic policy engine",
      requiresHumanReview: policy.requires_human_review,
      reviewId: policy.review_id ?? null,
      finalized: policy.finalized ?? false,
      policyVersion: policy.policy_version ?? null,
      ruleHits: (policy.policy_rules ?? []).map((rule) => ({
        ruleId: rule.rule_id,
        description: rule.description,
      })),
      reasonCodes: policy.policy_flags,
    },
    counterfactuals: (caseResult.counterfactuals ?? []).map((scenario) => ({
      scenarioId: scenario.scenario_id,
      label: scenario.label,
      hypothetical: true,
      persisted: false,
      assumption: scenario.assumption,
      changedFields: scenario.changed_fields.map((change) => ({
        field: change.field,
        originalValue: change.original_value,
        hypotheticalValue: change.hypothetical_value,
      })),
      specialistDeltas: scenario.specialist_deltas.map((delta) => ({
        agentId: delta.agent_id,
        originalRisk: delta.original_risk,
        hypotheticalRisk: delta.hypothetical_risk,
        riskDelta: delta.risk_delta,
      })),
      originalAverageRisk: scenario.original_average_risk,
      hypotheticalAverageRisk: scenario.hypothetical_average_risk,
      overallRiskDelta: scenario.overall_risk_delta,
      riskReduction: scenario.risk_reduction,
      originalPolicyOutcome: scenario.original_policy_outcome,
      hypotheticalPolicyOutcome: scenario.hypothetical_policy_outcome,
      originalRequiresReview: scenario.original_requires_review,
      hypotheticalRequiresReview: scenario.hypothetical_requires_review,
    })),
    modelRuntime: {
      source: caseResult.model_runtime?.source ?? "unavailable",
      scoreSemantics: "adverse_risk",
    },
    auditBundle: audit,
    pipelineStage: policy.requires_human_review ? "human-review" : "complete",
  };
}

export function caseResultToReviewItem(
  caseResult: CaseResult
): HumanReviewItem {
  const reports = caseResult.specialist_reports;
  const averageRisk =
    reports.length > 0
      ? reports.reduce((sum, report) => sum + report.score, 0) /
        reports.length
      : 1;
  const riskLevel: RiskLevel =
    averageRisk >= 0.7
      ? "critical"
      : averageRisk >= 0.55
        ? "high"
        : averageRisk >= 0.35
          ? "medium"
          : "low";

  return {
    id: `rev-${caseResult.case_id}`,
    caseId: caseResult.case_id,
    applicantName: caseResult.applicant.name,
    submittedAt: caseResult.created_at ?? new Date().toISOString(),
    priority:
      riskLevel === "critical"
        ? "urgent"
        : riskLevel === "high"
          ? "high"
          : caseResult.policy_decision.requires_human_review
            ? "medium"
            : "low",
    reason: caseResult.policy_decision.reason,
    credibilityScore: Math.round((1 - averageRisk) * 100),
    riskLevel,
    status: "pending",
  };
}
