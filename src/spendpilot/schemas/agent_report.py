"""Shared output contract for all specialist model agents."""

import math
from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AgentId(StrEnum):
    """Stable identifiers for the three specialist agents."""

    CREDIBILITY = "credibility"
    AFFORDABILITY = "affordability"
    CREDIT_RISK = "credit_risk"


class Recommendation(StrEnum):
    """Non-authoritative recommendations emitted by specialist agents."""

    APPROVE = "approve"
    DECLINE = "decline"
    REFER = "refer"
    REQUEST_MORE_DATA = "request_more_data"


class CheckStatus(StrEnum):
    """Result of model-specific validation checks."""

    PASSED = "passed"
    FAILED = "failed"
    NOT_APPLICABLE = "not_applicable"


class FeatureContribution(BaseModel):
    """One local model contribution with links to supporting evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    feature: str = Field(min_length=1)
    value: float | int | str | bool | None
    contribution: float
    reason_code: str = Field(min_length=1)
    evidence_refs: tuple[str, ...] = ()

    @field_validator("contribution")
    @classmethod
    def contribution_must_be_finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("contribution must be finite")
        return value


class AgentReport(BaseModel):
    """Immutable, auditable output shared by every specialist agent."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    report_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    agent_id: AgentId
    model_name: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    score: float = Field(ge=0, le=1)
    calibrated_probability: float | None = Field(default=None, ge=0, le=1)
    confidence: float | None = Field(default=None, ge=0, le=1)
    recommendation: Recommendation
    reason_codes: tuple[str, ...] = Field(min_length=1)
    top_contributors: tuple[FeatureContribution, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    monotonicity_checks: CheckStatus = CheckStatus.NOT_APPLICABLE
    limitations: tuple[str, ...] = ()
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @field_validator("reason_codes")
    @classmethod
    def reason_codes_must_be_unique(
        cls, values: tuple[str, ...]
    ) -> tuple[str, ...]:
        if len(values) != len(set(values)):
            raise ValueError("reason_codes must be unique")
        return values
