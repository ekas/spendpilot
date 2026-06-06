"""Parallel specialist workflow with policy-controlled review."""

from concurrent.futures import ThreadPoolExecutor

from pydantic import BaseModel, ConfigDict

from spendpilot.agents.base import SpecialistAgent
from spendpilot.agents.manager import ManagerAgent, ManagerReport
from spendpilot.orchestration.human_review import (
    HumanReviewQueue,
    HumanReviewResolution,
    HumanReviewTask,
)
from spendpilot.orchestration.policy_engine import PolicyEngine
from spendpilot.schemas.agent_report import AgentReport
from spendpilot.schemas.case import CaseSnapshot
from spendpilot.schemas.decision import DecisionRecord


class WorkflowResult(BaseModel):
    """Complete result of one workflow evaluation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    reports: tuple[AgentReport, ...]
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
    ) -> None:
        if not specialists:
            raise ValueError("at least one specialist is required")
        self._specialists = specialists
        self._manager = manager
        self._policy_engine = policy_engine
        self._review_queue = review_queue

    def run(self, case: CaseSnapshot) -> WorkflowResult:
        with ThreadPoolExecutor(max_workers=len(self._specialists)) as executor:
            reports = tuple(
                executor.map(
                    lambda specialist: specialist.assess(case),
                    self._specialists,
                )
            )
        ordered_reports = tuple(
            sorted(reports, key=lambda report: report.agent_id.value)
        )
        manager_report = self._manager.consolidate(ordered_reports)
        decision = self._policy_engine.evaluate(manager_report)
        review_task = None
        if not decision.finalized:
            review_task = self._review_queue.create(
                manager_report=manager_report,
                decision_id=decision.decision_id,
            )
        return WorkflowResult(
            reports=ordered_reports,
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
