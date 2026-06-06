"""Parallel specialist workflow with policy-controlled review."""

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from spendpilot.agents.base import SpecialistAgent
from spendpilot.agents.manager import ManagerAgent, ManagerReport
from spendpilot.orchestration.human_review import (
    HumanReviewQueue,
    HumanReviewResolution,
    HumanReviewTask,
)
from spendpilot.orchestration.feedback import FeedbackQueue
from spendpilot.orchestration.policy_engine import PolicyEngine
from spendpilot.schemas.agent_report import AgentId, AgentReport
from spendpilot.schemas.case import CaseSnapshot
from spendpilot.schemas.decision import DecisionRecord
from spendpilot.schemas.feedback import (
    AgentAssessmentRequest,
    AnalysisRound,
    FeedbackEvent,
)


class WorkflowResult(BaseModel):
    """Complete result of one workflow evaluation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    reports: tuple[AgentReport, ...]
    analysis_round: AnalysisRound
    manager_report: ManagerReport
    decision: DecisionRecord
    review_task: HumanReviewTask | None = None


class DecisionWorkflow:
    """Runs specialists in parallel and routes results through policy."""

    def __init__(
        self,
        *,
        specialists: tuple[SpecialistAgent, ...],
        manager: ManagerAgent,
        policy_engine: PolicyEngine,
        review_queue: HumanReviewQueue,
        feedback_queue: FeedbackQueue | None = None,
    ) -> None:
        if not specialists:
            raise ValueError("at least one specialist is required")
        self._specialists = specialists
        self._manager = manager
        self._policy_engine = policy_engine
        self._review_queue = review_queue
        self._feedback_queue = feedback_queue or FeedbackQueue()

    def run(self, case: CaseSnapshot) -> WorkflowResult:
        analysis_round = AnalysisRound(
            round_id=f"round_{uuid4().hex}",
            case_id=case.case_id,
            snapshot_id=case.snapshot_id,
            sequence_number=1,
        )
        return self._run_round(
            case=case,
            analysis_round=analysis_round,
        )

    def submit_feedback(self, feedback: FeedbackEvent) -> FeedbackEvent:
        return self._feedback_queue.submit(feedback)

    def reanalyze(
        self,
        *,
        previous_result: WorkflowResult,
        feedback_id: str,
        revised_case: CaseSnapshot,
        verifier_id: str,
    ) -> WorkflowResult:
        specialist_ids = {specialist.agent_id for specialist in self._specialists}
        if specialist_ids != set(AgentId):
            raise ValueError("feedback re-analysis requires all three specialists")
        if revised_case.case_id != previous_result.analysis_round.case_id:
            raise ValueError("revised snapshot belongs to another case")
        if revised_case.snapshot_id == previous_result.analysis_round.snapshot_id:
            raise ValueError("feedback requires a new immutable case snapshot")

        feedback = self._feedback_queue.verify_and_route(
            feedback_id=feedback_id,
            verifier_id=verifier_id,
            manager=self._manager,
            previous_reports=previous_result.reports,
            revised_case=revised_case,
        )
        analysis_round = AnalysisRound(
            round_id=f"round_{uuid4().hex}",
            case_id=revised_case.case_id,
            snapshot_id=revised_case.snapshot_id,
            sequence_number=previous_result.analysis_round.sequence_number + 1,
            parent_round_id=previous_result.analysis_round.round_id,
            triggering_feedback_ids=(feedback.feedback_id,),
        )
        return self._run_round(
            case=revised_case,
            analysis_round=analysis_round,
            feedback=(feedback,),
            previous_reports=previous_result.reports,
        )

    def _run_round(
        self,
        *,
        case: CaseSnapshot,
        analysis_round: AnalysisRound,
        feedback: tuple[FeedbackEvent, ...] = (),
        previous_reports: tuple[AgentReport, ...] = (),
    ) -> WorkflowResult:
        feedback_by_target = {
            specialist.agent_id: tuple(
                event
                for event in feedback
                if specialist.agent_id in event.selected_targets
            )
            for specialist in self._specialists
        }
        requests = tuple(
            AgentAssessmentRequest(
                agent_id=specialist.agent_id,
                case=case,
                analysis_round=analysis_round,
                targeted_feedback=feedback_by_target[specialist.agent_id],
            )
            for specialist in self._specialists
        )
        with ThreadPoolExecutor(max_workers=len(self._specialists)) as executor:
            reports = tuple(
                executor.map(
                    lambda pair: pair[0].assess(pair[1]),
                    zip(self._specialists, requests, strict=True),
                )
            )
        ordered_reports = tuple(
            sorted(reports, key=lambda report: report.agent_id.value)
        )
        manager_report = self._manager.consolidate(
            ordered_reports,
            previous_reports=previous_reports,
            feedback_ids=analysis_round.triggering_feedback_ids,
        )
        decision = self._policy_engine.evaluate(manager_report)
        review_task = None
        if not decision.finalized:
            review_task = self._review_queue.create(
                manager_report=manager_report,
                decision_id=decision.decision_id,
            )
        return WorkflowResult(
            reports=ordered_reports,
            analysis_round=analysis_round,
            manager_report=manager_report,
            decision=decision,
            review_task=review_task,
        )

    def resolve_review(
        self,
        resolution: HumanReviewResolution,
    ) -> DecisionRecord:
        task = self._review_queue.get(resolution.review_id)
        resolved_task = self._review_queue.resolve(resolution)
        return self._policy_engine.evaluate(
            task.manager_report,
            resolved_task.resolution,
        )
