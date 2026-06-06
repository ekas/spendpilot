"""Immutable case data supplied to specialist agents."""

from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import TypeAlias

from pydantic import BaseModel, ConfigDict, Field


FeatureValue: TypeAlias = bool | int | float | str | None


class CreditProduct(StrEnum):
    """Credit products supported by the initial decision workflow."""

    PERSONAL_LOAN = "personal_loan"
    CREDIT_CARD = "credit_card"


class CaseSnapshot(BaseModel):
    """A frozen, versioned view of the data used for one assessment."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    applicant_ref: str = Field(min_length=1)
    product: CreditProduct
    requested_amount: Decimal = Field(gt=0)
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    content_hash: str = Field(pattern=r"^sha256:[a-fA-F0-9]{64}$")
    features: dict[str, FeatureValue] = Field(default_factory=dict)
    evidence_refs: tuple[str, ...] = ()
    missing_fields: tuple[str, ...] = ()
