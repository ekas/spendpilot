export interface Applicant {
  name: string;
  monthly_income: number;
  monthly_expenses: number;
  requested_amount: number;
  existing_debt: number;
  credit_utilization: number;
  delinquencies_12m: number;
  employment_months: number;
  overdrafts_90d: number;
  income_verified: boolean;
  documents: string[];
  document_text?: string;
  document_signals?: DocumentSignals;
}

export interface DocumentSignals {
  numeric_hints?: Record<string, number>;
  consistency_flags?: string[];
  coverage_score?: number;
  income_verified_from_docs?: boolean;
  unreadable_files?: string[];
  stored_paths?: string[];
}

export interface Contributor {
  feature: string;
  feature_label?: string;
  value?: number | string | boolean | null;
  impact: number;
  direction: string;
  explanation: string;
  reason_code?: string;
  evidence_refs?: string[];
}

export interface AgentReport {
  agent_name: string;
  agent_id?: "credibility" | "affordability" | "credit_risk";
  score: number;
  score_semantics?: "adverse_risk" | "readiness";
  calibrated_probability?: number | null;
  confidence?: number | null;
  model_name?: string;
  model_source?: string;
  model_version: string;
  top_contributors: Contributor[];
  monotonicity_checks?: string;
  evidence_refs: string[];
  reason_codes: string[];
  confidence_status: string;
  recommendation: string;
  summary: string;
  limitations?: string[];
  report_id?: string;
  analysis_round_id?: string;
}

export interface ManagerReport {
  recommendation: string;
  disagreement?: boolean;
  disagreements: string[];
  requested_reanalysis: string[];
  reviewer_summary: string;
  readable_explanation: string;
  analysis_round_id?: string;
  assistant_status?: string;
  requires_human_review?: boolean;
  reason_codes?: string[];
}

export interface PolicyDecision {
  final_decision: string;
  final_authority?: string;
  policy_flags: string[];
  policy_rules?: Array<{
    rule_id: string;
    description: string;
  }>;
  requires_human_review: boolean;
  reason: string;
  decision_id?: string;
  review_id?: string | null;
  finalized?: boolean;
  policy_version?: string;
}

export interface CaseResult {
  case_id: string;
  applicant: Applicant;
  status: string;
  case_context?: CaseContext;
  submitted_data?: SubmittedData;
  derived_features?: DerivedFeatures;
  evidence?: EvidenceSummary;
  specialist_reports: AgentReport[];
  manager_report: ManagerReport;
  policy_decision: PolicyDecision;
  model_runtime?: {
    source: string;
    score_semantics: "adverse_risk";
    snapshot_id: string;
    snapshot_hash: string;
    pii_minimized: boolean;
  };
  counterfactuals?: CounterfactualScenario[];
  audit_bundle?: Record<string, unknown>;
  created_at?: string;
}

export interface CaseContext {
  case_id: string;
  snapshot_id: string;
  snapshot_hash: string;
  analysis_round_id: string;
  decision_id: string;
  applicant_ref: string;
  currency: "EUR";
  created_at: string;
}

export interface SubmittedData {
  monthly_income: number | null;
  monthly_expenses: number | null;
  requested_amount: number | null;
  existing_debt: number | null;
  credit_utilization: number | null;
  delinquencies_12m: number | null;
  employment_months: number | null;
  overdrafts_90d: number | null;
  income_verified: boolean | null;
}

export interface DerivedFeatures {
  effective_monthly_income: number | null;
  effective_monthly_expenses: number | null;
  effective_existing_debt: number | null;
  effective_credit_utilization: number | null;
  effective_delinquencies_12m: number | null;
  effective_employment_months: number | null;
  free_cash_flow: number | null;
  expense_ratio: number | null;
  debt_to_monthly_income: number | null;
  estimated_installment_36m: number | null;
  installment_burden: number | null;
}

export interface EvidenceSummary {
  document_count: number;
  evidence_refs: string[];
  coverage_score: number | null;
  missing_documents: string[];
  consistency_findings: string[];
  consistency_flag_count: number;
  unreadable_document_count: number;
  verification_state: "verified" | "unverified";
  income_verified: boolean;
}

export interface CounterfactualScenario {
  scenario_id: string;
  label: string;
  hypothetical: true;
  persisted: false;
  assumption: string;
  changed_fields: Array<{
    field: string;
    original_value: number | boolean | string | null;
    hypothetical_value: number | boolean | string | null;
  }>;
  specialist_deltas: Array<{
    agent_id: string;
    original_risk: number;
    hypothetical_risk: number;
    risk_delta: number;
  }>;
  original_average_risk: number;
  hypothetical_average_risk: number;
  overall_risk_delta: number;
  risk_reduction: number;
  original_policy_outcome: string;
  hypothetical_policy_outcome: string;
  original_requires_review: boolean;
  hypothetical_requires_review: boolean;
  model_source: string;
}

export interface CaseCreatePayload {
  applicant: Applicant;
}

export interface PeriodSummary {
  start_date: string;
  end_date: string;
  total_cases: number;
  decision_counts: Record<string, number>;
  decision_rates: Record<string, number>;
  human_review_rate: number;
  avg_specialist_scores: Record<string, number>;
}
