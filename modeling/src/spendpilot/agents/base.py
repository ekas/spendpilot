"""Shared behavior for specialist model agents."""

from uuid import uuid4

from spendpilot.models.contracts import ModelAdapter
from spendpilot.schemas.agent_report import AgentId, AgentReport
from spendpilot.schemas.case import CaseSnapshot


class SpecialistAgent:
    """Converts one model adapter output into the shared report contract."""

    agent_id: AgentId

    def __init__(self, model: ModelAdapter) -> None:
        self._model = model

    def assess(self, case: CaseSnapshot) -> AgentReport:
        output = self._model.predict(case)
        return AgentReport(
            report_id=f"report_{uuid4().hex}",
            case_id=case.case_id,
            snapshot_id=case.snapshot_id,
            agent_id=self.agent_id,
            model_name=self._model.model_name,
            model_version=self._model.model_version,
            **output.model_dump(),
        )
