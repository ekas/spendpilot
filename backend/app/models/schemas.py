from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class SpendProfile(BaseModel):
    company_name: str
    monthly_revenue: float
    monthly_spend: float
    planned_budget: float
    cash_reserve: float
    budget_variance_ratio: float = Field(ge=0, le=1)
    anomalous_transactions_30d: int = 0
    runway_months: int = 0
    late_payments_90d: int = 0
    invoice_match_rate: float = Field(ge=0, le=1)
    books_verified: bool = False
    documents: List[str] = Field(default_factory=list)
    document_text: str = ""
    document_signals: Dict[str, Any] = Field(default_factory=dict)

class CaseCreate(BaseModel):
    profile: SpendProfile

class Contributor(BaseModel):
    feature: str
    impact: float
    direction: str
    explanation: str

class AgentReport(BaseModel):
    agent_name: str
    score: float
    model_version: str
    top_contributors: List[Contributor]
    monotonicity_checks: str = "passed"
    evidence_refs: List[str]
    reason_codes: List[str]
    confidence_status: str
    recommendation: str
    summary: str

class ManagerReport(BaseModel):
    recommendation: str
    disagreements: List[str]
    requested_reanalysis: List[str]
    reviewer_summary: str
    readable_explanation: str

class PolicyDecision(BaseModel):
    final_decision: str
    final_authority: str = "Deterministic spend policy engine + finance reviewer"
    policy_flags: List[str]
    requires_finance_review: bool
    reason: str

class CaseResult(BaseModel):
    case_id: str
    profile: SpendProfile
    status: str
    specialist_reports: List[AgentReport]
    manager_report: ManagerReport
    policy_decision: PolicyDecision
