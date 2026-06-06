from typing import Any

from pydantic import BaseModel, Field


class ModelingApplicant(BaseModel):
    name: str = Field(default="Applicant", min_length=1)
    monthly_income: float = Field(gt=0)
    monthly_expenses: float = Field(ge=0)
    requested_amount: float = Field(gt=0)
    existing_debt: float = Field(ge=0)
    credit_utilization: float = Field(ge=0, le=1)
    delinquencies_12m: int = Field(default=0, ge=0)
    employment_months: int = Field(default=0, ge=0)
    overdrafts_90d: int = Field(default=0, ge=0)
    income_verified: bool = False
    documents: list[str] = Field(default_factory=list)
    document_text: str = ""
    document_signals: dict[str, Any] = Field(default_factory=dict)


class ModelingAnalysisRequest(BaseModel):
    applicant: ModelingApplicant
    case_id: str | None = None
    snapshot_id: str = "snapshot_1"
