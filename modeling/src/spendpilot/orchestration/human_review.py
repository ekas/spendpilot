"""Typed human-review tasks and resolutions."""

from datetime import datetime, timezone
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from spendpilot.agents.manager import ManagerReport
from spendpilot.schemas.decision import DecisionAction


class HumanReviewAction(StrEnum):
    """Controlled actions available to an authorized reviewer."""

    APPROVE_RECOMMENDATION = "approve_recommendation"
    REQUEST_MORE_DATA = "request_more_data"
    CHALLENGE_AGENT = "challenge_agent"
    REQUEST_REANALYSIS = "request_reanalysis"
    OVERRIDE_DECISION = "override_decision"
    ESCALATE = "escalate"


class HumanReviewStatus(StrEnum):
    """Lifecycle state of a human-review task."""

    PENDING = "pending"
    RESOLVED = "resolved"


class HumanReviewResolution(BaseModel):
    """Signed reviewer instruction consumed by the policy engine."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    review_id: str = Field(min_length=1)
    reviewer_id: str = Field(min_length=1)
    action: HumanReviewAction
    rationale: str = Field(min_length=1)
    override_action: DecisionAction | None = None
    resolved_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @model_validator(mode="after")
    def validate_override(self) -> "HumanReviewResolution":
        has_override = self.override_action is not None
        expects_override = self.action is HumanReviewAction.OVERRIDE_DECISION
        if has_override != expects_override:
            raise ValueError(
                "override_action is required only for override_decision"
            )
        return self


class HumanReviewTask(BaseModel):
    """Review package presented to an authorized human."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    review_id: str = Field(min_length=1)
    decision_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    manager_report: ManagerReport
    status: HumanReviewStatus = HumanReviewStatus.PENDING
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    resolution: HumanReviewResolution | None = None


class HumanReviewQueue:
    """Small in-memory review queue for the architecture scaffold."""

    def __init__(self) -> None:
        self._tasks: dict[str, HumanReviewTask] = {}

    def create(
        self,
        *,
        manager_report: ManagerReport,
        decision_id: str,
    ) -> HumanReviewTask:
        task = HumanReviewTask(
            review_id=f"review_{uuid4().hex}",
            decision_id=decision_id,
            case_id=manager_report.case_id,
            snapshot_id=manager_report.snapshot_id,
            manager_report=manager_report,
        )
        self._tasks[task.review_id] = task
        return task

    def get(self, review_id: str) -> HumanReviewTask:
        try:
            return self._tasks[review_id]
        except KeyError as exc:
            raise LookupError(f"review task {review_id} was not found") from exc

    def resolve(
        self,
        resolution: HumanReviewResolution,
    ) -> HumanReviewTask:
        task = self.get(resolution.review_id)
        if task.status is HumanReviewStatus.RESOLVED:
            raise ValueError("review task is already resolved")
        resolved_task = task.model_copy(
            update={
                "status": HumanReviewStatus.RESOLVED,
                "resolution": resolution,
            }
        )
        self._tasks[task.review_id] = resolved_task
        return resolved_task
