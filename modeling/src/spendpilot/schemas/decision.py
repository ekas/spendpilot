"""Authoritative decision records emitted by the policy engine."""

from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class DecisionAction(StrEnum):
    """Actions that the deterministic policy engine can finalize."""

    APPROVE = "approve"
    DECLINE = "decline"
    REFER = "refer"
    REQUEST_MORE_DATA = "request_more_data"


class PolicyRuleHit(BaseModel):
    """A versioned policy rule that influenced a decision."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_id: str = Field(min_length=1)
    description: str = Field(min_length=1)


class DecisionRecord(BaseModel):
    """Append-only result created exclusively by the policy engine."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    decision_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    action: DecisionAction
    reason_codes: tuple[str, ...] = Field(min_length=1)
    report_ids: tuple[str, ...] = ()
    policy_rules: tuple[PolicyRuleHit, ...] = ()
    human_review_id: str | None = None
    finalized: bool = False
    decided_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
