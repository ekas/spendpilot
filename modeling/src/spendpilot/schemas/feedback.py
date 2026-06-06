"""Contracts for governed feedback and immutable analysis rounds."""

from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from spendpilot.schemas.agent_report import (
    AgentId,
    AgentReport,
    Recommendation,
)
from spendpilot.schemas.case import CaseSnapshot


class FeedbackSource(StrEnum):
    """Authorized sources of case-level feedback."""

    REVIEWER = "reviewer"
    APPLICANT = "applicant"


class FeedbackType(StrEnum):
    """Feedback categories accepted by the manager."""

    DATA_CORRECTION = "data_correction"
    NEW_EVIDENCE = "new_evidence"
    MODEL_CHALLENGE = "model_challenge"
    APPEAL = "appeal"


class VerificationStatus(StrEnum):
    """Evidence-verification state for a feedback event."""

    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class FeedbackEvent(BaseModel):
    """Immutable feedback submitted for manager validation and routing."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    feedback_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    source: FeedbackSource
    feedback_type: FeedbackType
    rationale: str = Field(min_length=1)
    evidence_refs: tuple[str, ...] = ()
    related_report_ids: tuple[str, ...] = ()
    submitter_ref: str = Field(min_length=1)
    verification_status: VerificationStatus = VerificationStatus.PENDING
    verified_by: str | None = None
    selected_targets: tuple[AgentId, ...] = ()
    parent_feedback_id: str | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    verified_at: datetime | None = None

    @model_validator(mode="after")
    def validate_verification(self) -> "FeedbackEvent":
        verified = self.verification_status is VerificationStatus.VERIFIED
        if verified and (self.verified_by is None or self.verified_at is None):
            raise ValueError(
                "verified feedback requires verified_by and verified_at"
            )
        if not verified and (
            self.verified_by is not None or self.verified_at is not None
        ):
            raise ValueError(
                "verification metadata is allowed only for verified feedback"
            )
        if len(self.selected_targets) != len(set(self.selected_targets)):
            raise ValueError("selected_targets must be unique")
        return self


class AnalysisRound(BaseModel):
    """One immutable execution round for a case snapshot."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    round_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    sequence_number: int = Field(ge=1)
    parent_round_id: str | None = None
    triggering_feedback_ids: tuple[str, ...] = ()
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @model_validator(mode="after")
    def validate_parent(self) -> "AnalysisRound":
        if self.sequence_number == 1 and self.parent_round_id is not None:
            raise ValueError("the first analysis round cannot have a parent")
        if self.sequence_number > 1 and self.parent_round_id is None:
            raise ValueError("re-analysis rounds require a parent round")
        if len(self.triggering_feedback_ids) != len(
            set(self.triggering_feedback_ids)
        ):
            raise ValueError("triggering_feedback_ids must be unique")
        return self


class AgentAssessmentRequest(BaseModel):
    """Validated input supplied to one specialist agent."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    agent_id: AgentId
    case: CaseSnapshot
    analysis_round: AnalysisRound
    targeted_feedback: tuple[FeedbackEvent, ...] = ()

    @model_validator(mode="after")
    def validate_request(self) -> "AgentAssessmentRequest":
        if self.case.case_id != self.analysis_round.case_id:
            raise ValueError("case and analysis round case identifiers differ")
        if self.case.snapshot_id != self.analysis_round.snapshot_id:
            raise ValueError(
                "case and analysis round snapshot identifiers differ"
            )
        round_feedback = set(self.analysis_round.triggering_feedback_ids)
        for feedback in self.targeted_feedback:
            if feedback.case_id != self.case.case_id:
                raise ValueError("feedback belongs to another case")
            if feedback.verification_status is not VerificationStatus.VERIFIED:
                raise ValueError("only verified feedback may reach an agent")
            if self.agent_id not in feedback.selected_targets:
                raise ValueError("feedback was not routed to this agent")
            if feedback.feedback_id not in round_feedback:
                raise ValueError("feedback is not linked to the analysis round")
        return self


class AgentReportDelta(BaseModel):
    """Auditable difference between two reports from the same specialist."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    agent_id: AgentId
    previous_report_id: str = Field(min_length=1)
    current_report_id: str = Field(min_length=1)
    previous_round_id: str = Field(min_length=1)
    current_round_id: str = Field(min_length=1)
    score_delta: float
    previous_recommendation: Recommendation
    current_recommendation: Recommendation
    added_reason_codes: tuple[str, ...] = ()
    removed_reason_codes: tuple[str, ...] = ()
    changed_features: tuple[str, ...] = ()

    @classmethod
    def compare(
        cls,
        previous: AgentReport,
        current: AgentReport,
    ) -> "AgentReportDelta":
        if previous.agent_id is not current.agent_id:
            raise ValueError("reports must come from the same specialist")
        previous_reasons = set(previous.reason_codes)
        current_reasons = set(current.reason_codes)
        previous_features = {
            contribution.feature: contribution
            for contribution in previous.top_contributors
        }
        current_features = {
            contribution.feature: contribution
            for contribution in current.top_contributors
        }
        changed_features = tuple(
            sorted(
                feature
                for feature in previous_features.keys() | current_features.keys()
                if previous_features.get(feature) != current_features.get(feature)
            )
        )
        return cls(
            agent_id=current.agent_id,
            previous_report_id=previous.report_id,
            current_report_id=current.report_id,
            previous_round_id=previous.analysis_round_id,
            current_round_id=current.analysis_round_id,
            score_delta=current.score - previous.score,
            previous_recommendation=previous.recommendation,
            current_recommendation=current.recommendation,
            added_reason_codes=tuple(sorted(current_reasons - previous_reasons)),
            removed_reason_codes=tuple(
                sorted(previous_reasons - current_reasons)
            ),
            changed_features=changed_features,
        )
