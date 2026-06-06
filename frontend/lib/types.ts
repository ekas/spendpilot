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
  reportId: string | null;
  analysisRoundId: string | null;
  adverseRisk: number;
  calibratedProbability: number | null;
  confidence: number | null;
  recommendation: "APPROVE" | "REFER" | "REJECT";
  summary: string;
  reasonCodes: string[];
  evidenceRefs: string[];
  contributions: ModelContribution[];
  modelName: string;
  modelVersion: string;
  modelSource: string | null;
  limitations: string[];
}

export interface ModelContribution {
  feature: string;
  label: string;
  value: number | string | boolean | null;
  impact: number;
  direction: "increases risk" | "reduces risk" | "neutral";
  explanation: string;
  reasonCode: string | null;
  evidenceRefs: string[];
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
  caseContext: {
    snapshotId: string;
    snapshotHash: string;
    analysisRoundId: string;
    decisionId: string;
    applicantRef: string;
    currency: "EUR";
    createdAt: string;
  };
  applicantName: string;
  submittedData: {
    monthlyIncome: number | null;
    monthlyExpenses: number | null;
    requestedAmount: number | null;
    existingDebt: number | null;
    creditUtilization: number | null;
    delinquencies12m: number | null;
    employmentMonths: number | null;
    overdrafts90d: number | null;
    incomeVerified: boolean | null;
  };
  derivedFeatures: {
    effectiveMonthlyIncome: number | null;
    effectiveMonthlyExpenses: number | null;
    effectiveExistingDebt: number | null;
    effectiveCreditUtilization: number | null;
    effectiveDelinquencies12m: number | null;
    effectiveEmploymentMonths: number | null;
    freeCashFlow: number | null;
    expenseRatio: number | null;
    debtToMonthlyIncome: number | null;
    estimatedInstallment36m: number | null;
    installmentBurden: number | null;
  };
  evidence: {
    documentCount: number;
    evidenceRefs: string[];
    coverageScore: number | null;
    missingDocuments: string[];
    consistencyFindings: string[];
    consistencyFlagCount: number;
    unreadableDocumentCount: number;
    verificationState: "verified" | "unverified";
    incomeVerified: boolean;
  };
  agentReports: AgentReport[];
  policyChecks: PolicyCheck[];
  manager: {
    recommendation: "APPROVE" | "REFER" | "REJECT";
    disagreement: boolean;
    disagreements: string[];
    requestedReanalysis: string[];
    summary: string;
    explanation: string;
    assistantStatus: string | null;
    requiresHumanReview: boolean;
    reasonCodes: string[];
  };
  decision: {
    outcome: DecisionOutcome;
    label: "APPROVE" | "REFER" | "REJECT";
    reason: string;
    finalAuthority: string;
    requiresHumanReview: boolean;
    reviewId: string | null;
    finalized: boolean;
    policyVersion: string | null;
    ruleHits: Array<{ ruleId: string; description: string }>;
    reasonCodes: string[];
  };
  counterfactuals: CounterfactualScenario[];
  modelRuntime: {
    source: string;
    scoreSemantics: "adverse_risk";
  };
  auditBundle: Record<string, unknown>;
  pipelineStage: "human-review" | "complete";
}

export interface CounterfactualScenario {
  scenarioId: string;
  label: string;
  hypothetical: true;
  persisted: false;
  assumption: string;
  changedFields: Array<{
    field: string;
    originalValue: number | boolean | string | null;
    hypotheticalValue: number | boolean | string | null;
  }>;
  specialistDeltas: Array<{
    agentId: string;
    originalRisk: number;
    hypotheticalRisk: number;
    riskDelta: number;
  }>;
  originalAverageRisk: number;
  hypotheticalAverageRisk: number;
  overallRiskDelta: number;
  riskReduction: number;
  originalPolicyOutcome: string;
  hypotheticalPolicyOutcome: string;
  originalRequiresReview: boolean;
  hypotheticalRequiresReview: boolean;
}
