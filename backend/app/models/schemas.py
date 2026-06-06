from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class Applicant(BaseModel):
    name: str
    monthly_income: float
    monthly_expenses: float
    requested_amount: float
    existing_debt: float
    credit_utilization: float = Field(ge=0, le=1)
    delinquencies_12m: int = 0
    employment_months: int = 0
    overdrafts_90d: int = 0
    income_verified: bool = False
    documents: List[str] = Field(default_factory=list)
    document_text: str = ""
    document_signals: Dict[str, Any] = Field(default_factory=dict)

class CaseCreate(BaseModel):
    applicant: Applicant

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
    final_authority: str = "Deterministic policy engine + human reviewer"
    policy_flags: List[str]
    requires_human_review: bool
    reason: str

class CaseResult(BaseModel):
    case_id: str
    applicant: Applicant
    status: str
    specialist_reports: List[AgentReport]
    manager_report: ManagerReport
    policy_decision: PolicyDecision
