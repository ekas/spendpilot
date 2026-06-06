import assert from "node:assert/strict";
import test from "node:test";

import { caseResultToAnalysis } from "../lib/backend/transform.ts";
import type { CaseResult } from "../lib/backend/schemas.ts";

function fixture(): CaseResult {
  return {
    case_id: "case-1",
    applicant: {
      name: "Presentation Name",
      monthly_income: 3000,
      monthly_expenses: 2200,
      requested_amount: 8000,
      existing_debt: 1000,
      credit_utilization: 0.4,
      delinquencies_12m: 1,
      employment_months: 10,
      overdrafts_90d: 1,
      income_verified: false,
      documents: [],
    },
    status: "REFER",
    case_context: {
      case_id: "case-1",
      snapshot_id: "snapshot-1",
      snapshot_hash: `sha256:${"a".repeat(64)}`,
      analysis_round_id: "round-1",
      decision_id: "decision-1",
      applicant_ref: "applicant:hashed",
      currency: "EUR",
      created_at: "2026-06-06T10:00:00Z",
    },
    submitted_data: {
      monthly_income: 3000,
      monthly_expenses: 2200,
      requested_amount: 8000,
      existing_debt: 1000,
      credit_utilization: 0.4,
      delinquencies_12m: 1,
      employment_months: 10,
      overdrafts_90d: 1,
      income_verified: false,
    },
    derived_features: {
      effective_monthly_income: 3000,
      effective_monthly_expenses: 2200,
      effective_existing_debt: 1000,
      effective_credit_utilization: 0.4,
      effective_delinquencies_12m: 1,
      effective_employment_months: 10,
      free_cash_flow: 800,
      expense_ratio: 0.7333333333,
      debt_to_monthly_income: 0.3333333333,
      estimated_installment_36m: 222.2222222,
      installment_burden: 0.2777777777,
    },
    evidence: {
      document_count: 0,
      evidence_refs: [],
      coverage_score: null,
      missing_documents: ["bank_statement"],
      consistency_findings: [],
      consistency_flag_count: 0,
      unreadable_document_count: 0,
      verification_state: "unverified",
      income_verified: false,
    },
    specialist_reports: [
      {
        agent_name: "Affordability Agent",
        agent_id: "affordability",
        score: 0.4321,
        score_semantics: "adverse_risk",
        calibrated_probability: 0.4321,
        confidence: null,
        model_name: "affordability-model",
        model_version: "v1",
        top_contributors: [
          {
            feature: "expense_ratio",
            feature_label: "Monthly income used for expenses",
            value: 0.7333333333,
            impact: 0.123456,
            direction: "increases risk",
            explanation: "Raised risk.",
            reason_code: "HIGH_EXPENSE_RATIO",
            evidence_refs: ["document:abc"],
          },
        ],
        evidence_refs: ["document:abc"],
        reason_codes: ["HIGH_EXPENSE_RATIO"],
        confidence_status: "Unavailable",
        recommendation: "REFER",
        summary: "Measured result.",
      },
    ],
    manager_report: {
      recommendation: "REFER",
      disagreement: false,
      disagreements: [],
      requested_reanalysis: [],
      reviewer_summary: "Review required.",
      readable_explanation: "Policy routed the case.",
      requires_human_review: true,
    },
    policy_decision: {
      final_decision: "REFER",
      final_authority: "Deterministic policy engine",
      policy_flags: ["HUMAN_REVIEW_REQUIRED"],
      policy_rules: [
        {
          rule_id: "HUMAN_REVIEW_REQUIRED",
          description: "An authorized reviewer must decide.",
        },
      ],
      requires_human_review: true,
      reason: "Review required.",
      review_id: "review-1",
      finalized: false,
    },
    counterfactuals: [],
    model_runtime: {
      source: "trained_synthetic_xgboost",
      score_semantics: "adverse_risk",
      snapshot_id: "snapshot-1",
      snapshot_hash: `sha256:${"a".repeat(64)}`,
      pii_minimized: true,
    },
    audit_bundle: { schema_version: "audit-v1" },
  };
}

test("preserves exact model outputs and unavailable values", () => {
  const result = caseResultToAnalysis(fixture());
  const report = result.agentReports[0];

  assert.equal(report.adverseRisk, 0.4321);
  assert.equal(report.calibratedProbability, 0.4321);
  assert.equal(report.confidence, null);
  assert.equal(report.recommendation, "REFER");
  assert.equal(report.contributions[0].impact, 0.123456);
  assert.equal(report.contributions[0].value, 0.7333333333);
  assert.equal(result.evidence.coverageScore, null);
  assert.equal(result.decision.label, "REFER");
});

test("rejects legacy responses instead of inventing dashboard values", () => {
  const legacy = fixture();
  delete legacy.derived_features;

  assert.throws(
    () => caseResultToAnalysis(legacy),
    /legacy response without underwriting data/
  );
});
