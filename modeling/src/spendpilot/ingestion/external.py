"""Validated JSON-file intake for cases supplied outside the demo."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from spendpilot.ingestion.backend import BackendApplicant, BackendInputAdapter
from spendpilot.schemas import CaseSnapshot, CreditProduct


class ExternalCaseRequest(BaseModel):
    """One external applicant request plus non-PII workflow metadata."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    snapshot_id: str = Field(default="snapshot_1", min_length=1)
    applicant_ref: str | None = Field(default=None, min_length=1)
    product: CreditProduct = CreditProduct.PERSONAL_LOAN
    currency: str = Field(default="EUR", pattern=r"^[A-Z]{3}$")
    applicant: BackendApplicant

    def to_snapshot(self) -> CaseSnapshot:
        """Validate and remove direct applicant data before assessment."""

        return BackendInputAdapter().to_snapshot(
            self.applicant,
            case_id=self.case_id,
            snapshot_id=self.snapshot_id,
            applicant_ref=self.applicant_ref,
            product=self.product,
            currency=self.currency,
        )


class ExternalCaseBatch(BaseModel):
    """A bounded collection of externally supplied cases."""

    model_config = ConfigDict(extra="forbid")

    cases: tuple[ExternalCaseRequest, ...] = Field(min_length=1, max_length=100)


def load_external_cases(path: Path | str) -> tuple[ExternalCaseRequest, ...]:
    """Load a single request, a list, or a ``{"cases": [...]}`` batch."""

    payload = json.loads(Path(path).read_text())
    if isinstance(payload, list):
        payload = {"cases": payload}
    elif isinstance(payload, dict) and "cases" not in payload:
        payload = {"cases": [payload]}
    return ExternalCaseBatch.model_validate(payload).cases
