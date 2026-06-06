"""Shared behavior for specialist model agents."""

from uuid import uuid4

from spendpilot.models.contracts import ModelAdapter
from spendpilot.schemas.agent_report import AgentId, AgentReport
from spendpilot.schemas.case import CaseSnapshot
from spendpilot.schemas.feedback import AgentAssessmentRequest


class SpecialistAgent:
    """Converts one model adapter output into the shared report contract."""

    agent_id: AgentId

    def __init__(self, model: ModelAdapter) -> None:
        self._model = model

    def assess(
        self,
        assessment: CaseSnapshot | AgentAssessmentRequest,
    ) -> AgentReport:
        if isinstance(assessment, AgentAssessmentRequest):
            if assessment.agent_id is not self.agent_id:
                raise ValueError("assessment request targets another agent")
            case = assessment.case
            analysis_round_id = assessment.analysis_round.round_id
            feedback_ids = assessment.analysis_round.triggering_feedback_ids
            responded_feedback_ids = tuple(
                feedback.feedback_id
                for feedback in assessment.targeted_feedback
            )
        else:
            case = assessment
            analysis_round_id = "round_initial"
            feedback_ids = ()
            responded_feedback_ids = ()

        output = self._model.predict(case)
        return AgentReport(
            report_id=f"report_{uuid4().hex}",
            case_id=case.case_id,
            snapshot_id=case.snapshot_id,
            analysis_round_id=analysis_round_id,
            feedback_ids=feedback_ids,
            responded_feedback_ids=responded_feedback_ids,
            agent_id=self.agent_id,
            model_name=self._model.model_name,
            model_version=self._model.model_version,
            **output.model_dump(),
        )
