"""In-memory submission, verification, and routing of case feedback."""

from datetime import datetime, timezone

from spendpilot.agents.manager import ManagerAgent
from spendpilot.schemas.agent_report import AgentReport
from spendpilot.schemas.case import CaseSnapshot
from spendpilot.schemas.feedback import (
    FeedbackEvent,
    FeedbackSource,
    VerificationStatus,
)


class FeedbackQueue:
    """Retains immutable submissions and separately accepted routed events."""

    def __init__(self) -> None:
        self._submissions: dict[str, FeedbackEvent] = {}
        self._accepted: dict[str, FeedbackEvent] = {}

    def submit(self, feedback: FeedbackEvent) -> FeedbackEvent:
        if feedback.feedback_id in self._submissions:
            raise ValueError(f"feedback {feedback.feedback_id} already exists")
        if feedback.selected_targets:
            raise ValueError("targets are assigned only by the manager")
        self._submissions[feedback.feedback_id] = feedback
        return feedback

    def get_submission(self, feedback_id: str) -> FeedbackEvent:
        try:
            return self._submissions[feedback_id]
        except KeyError as exc:
            raise LookupError(f"feedback {feedback_id} was not found") from exc

    def get_accepted(self, feedback_id: str) -> FeedbackEvent:
        try:
            return self._accepted[feedback_id]
        except KeyError as exc:
            raise LookupError(
                f"feedback {feedback_id} has not been accepted"
            ) from exc

    def verify_and_route(
        self,
        *,
        feedback_id: str,
        verifier_id: str,
        manager: ManagerAgent,
        previous_reports: tuple[AgentReport, ...],
        revised_case: CaseSnapshot,
    ) -> FeedbackEvent:
        submission = self.get_submission(feedback_id)
        if feedback_id in self._accepted:
            raise ValueError(f"feedback {feedback_id} is already accepted")
        if submission.verification_status is VerificationStatus.REJECTED:
            raise ValueError("rejected feedback cannot be accepted")
        if (
            submission.source is FeedbackSource.APPLICANT
            and not submission.evidence_refs
        ):
            raise ValueError(
                "applicant feedback requires verifiable evidence references"
            )

        verified = submission.model_copy(
            update={
                "verification_status": VerificationStatus.VERIFIED,
                "verified_by": verifier_id,
                "verified_at": datetime.now(timezone.utc),
            }
        )
        routed = manager.route_feedback(
            feedback=verified,
            previous_reports=previous_reports,
            revised_case=revised_case,
        )
        self._accepted[feedback_id] = routed
        return routed

    def submissions(self) -> tuple[FeedbackEvent, ...]:
        return tuple(self._submissions.values())

    def accepted(self) -> tuple[FeedbackEvent, ...]:
        return tuple(self._accepted.values())
