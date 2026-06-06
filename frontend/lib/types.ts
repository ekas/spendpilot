export type AgentId =
  | "evidence"
  | "affordability"
  | "credit-risk"
  | "manager";

export type AgentStatus =
  | "idle"
  | "processing"
  | "complete"
  | "error"
  | "waiting";

export type RiskLevel = "low" | "medium" | "high" | "critical";

export type DecisionOutcome =
  | "approved"
  | "approved-with-conditions"
  | "review-required"
  | "declined"
  | "pending";

export type DocumentType =
  | "invoice"
  | "quote"
  | "contract"
  | "bank-statement"
  | "spend-export"
  | "other";

export interface UploadedDocument {
  id: string;
  name: string;
  type: DocumentType;
  size: number;
  uploadedAt: string;
  extractedText?: string;
  status: "uploading" | "extracting" | "ready" | "error";
}

export interface AgentFinding {
  id: string;
  category: string;
  severity: RiskLevel;
  title: string;
  description: string;
  evidence: string[];
  confidence: number;
}

export interface AgentReport {
  agentId: AgentId;
  agentName: string;
  status: AgentStatus;
  startedAt?: string;
  completedAt?: string;
  score: number;
  confidence: number;
  summary: string;
  findings: AgentFinding[];
  metrics: Record<string, number | string>;
  reasoning: string[];
}

export interface AgentMessage {
  id: string;
  from: AgentId;
  to: AgentId | "broadcast";
  timestamp: string;
  type: "analysis" | "question" | "response" | "conflict" | "resolution";
  content: string;
  metadata?: Record<string, unknown>;
}

export interface ConflictItem {
  id: string;
  agents: AgentId[];
  topic: string;
  description: string;
  severity: RiskLevel;
  resolution?: string;
  resolved: boolean;
}

export interface PolicyCheck {
  id: string;
  rule: string;
  status: "pass" | "fail" | "warning" | "pending";
  details: string;
}

export interface SpendCategory {
  name: string;
  amount: number;
  percentage: number;
  trend: "up" | "down" | "stable";
  riskFlag?: boolean;
}

export interface RecurringBill {
  vendor: string;
  amount: number;
  frequency: "weekly" | "monthly" | "quarterly" | "annual";
  nextDue: string;
  verified: boolean;
  duplicateRisk: boolean;
}

export interface SavingsOpportunity {
  id: string;
  title: string;
  potentialSavings: number;
  category: string;
  confidence: number;
  action: string;
}

export interface CredibilityBreakdown {
  evidenceScore: number;
  affordabilityScore: number;
  creditRiskScore: number;
  overallScore: number;
  riskLevel: RiskLevel;
  confidence: number;
}

export interface CaseSnapshot {
  id: string;
  applicantName: string;
  applicationDate: string;
  documents: UploadedDocument[];
  monthlyIncome: number;
  monthlyExpenses: number;
  debtToIncome: number;
  savingsRate: number;
  validationStatus: "pending" | "valid" | "invalid" | "partial";
  validationIssues: string[];
}

export interface HumanReviewItem {
  id: string;
  caseId: string;
  applicantName: string;
  submittedAt: string;
  priority: "low" | "medium" | "high" | "urgent";
  reason: string;
  credibilityScore: number;
  riskLevel: RiskLevel;
  status: "pending" | "in-review" | "resolved";
  assignedTo?: string;
}

export interface AnalysisResult {
  caseId: string;
  snapshot: CaseSnapshot;
  agentReports: AgentReport[];
  agentMessages: AgentMessage[];
  conflicts: ConflictItem[];
  policyChecks: PolicyCheck[];
  credibility: CredibilityBreakdown;
  spendCategories: SpendCategory[];
  recurringBills: RecurringBill[];
  savingsOpportunities: SavingsOpportunity[];
  decision: {
    outcome: DecisionOutcome;
    rationale: string[];
    conditions?: string[];
    reviewedBy?: string;
    decidedAt?: string;
  };
  pipelineStage:
    | "upload"
    | "validation"
    | "agent-analysis"
    | "aggregation"
    | "conflict-detection"
    | "policy-validation"
    | "decision"
    | "human-review"
    | "complete";
}
