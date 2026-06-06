"""Interfaces between specialist agents and model implementations."""

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from spendpilot.schemas.agent_report import (
    CheckStatus,
    FeatureContribution,
    Recommendation,
)
from spendpilot.schemas.case import CaseSnapshot


class ModelOutput(BaseModel):
    """Normalized output returned by a model adapter."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    score: float = Field(ge=0, le=1)
    calibrated_probability: float | None = Field(default=None, ge=0, le=1)
    confidence: float | None = Field(default=None, ge=0, le=1)
    recommendation: Recommendation
    reason_codes: tuple[str, ...] = Field(min_length=1)
    top_contributors: tuple[FeatureContribution, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    monotonicity_checks: CheckStatus = CheckStatus.NOT_APPLICABLE
    limitations: tuple[str, ...] = ()


class ModelAdapter(Protocol):
    """Behavior required from mock and production model implementations."""

    @property
    def model_name(self) -> str:
        """Return the stable registered model name."""

    @property
    def model_version(self) -> str:
        """Return the immutable model artifact version."""

    def predict(self, case: CaseSnapshot) -> ModelOutput:
        """Evaluate one immutable case snapshot."""
