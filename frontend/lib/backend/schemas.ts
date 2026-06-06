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
}

export interface AgentReport {
  agent_name: string;
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
  disagreements: string[];
  requested_reanalysis: string[];
  reviewer_summary: string;
  readable_explanation: string;
  analysis_round_id?: string;
  assistant_status?: string;
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
  created_at?: string;
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
