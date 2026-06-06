"""References to evidence stored outside the decision payload."""

from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class EvidenceKind(StrEnum):
    """Source categories used by the initial consumer-credit workflow."""

    IDENTITY = "identity"
    BANK_TRANSACTION = "bank_transaction"
    INCOME = "income"
    CREDIT_BUREAU = "credit_bureau"
    APPLICANT_DOCUMENT = "applicant_document"


class EvidenceReference(BaseModel):
    """Metadata that links a decision factor to immutable source evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evidence_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    kind: EvidenceKind
    source_system: str = Field(min_length=1)
    content_hash: str = Field(pattern=r"^sha256:[a-fA-F0-9]{64}$")
    collected_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    consent_ref: str = Field(min_length=1)
