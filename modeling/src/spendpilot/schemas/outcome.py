"""Append-only repayment outcome contracts."""

from datetime import date, datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class PaymentStatus(StrEnum):
    """Observed repayment states."""

    CURRENT = "current"
    DELINQUENT = "delinquent"
    DEFAULTED = "defaulted"
    CHARGED_OFF = "charged_off"
    CLOSED = "closed"


class OutcomeSource(StrEnum):
    """Systems allowed to provide repayment observations."""

    LOAN_SERVICER = "loan_servicer"
    LEDGER = "ledger"
    CREDIT_BUREAU = "credit_bureau"


class OutcomeEvent(BaseModel):
    """One immutable repayment observation linked to a final decision."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    outcome_event_id: str = Field(min_length=1)
    decision_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    account_ref: str = Field(min_length=1)
    payment_status: PaymentStatus
    days_past_due: int = Field(ge=0)
    observation_date: date
    source: OutcomeSource
    source_event_ref: str = Field(min_length=1)
    recorded_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
