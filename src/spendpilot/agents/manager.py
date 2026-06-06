"""Deterministic manager scaffold for specialist communication."""

from pydantic import BaseModel, ConfigDict, Field

from spendpilot.schemas.agent_report import (
    AgentId,
    AgentReport,
    Recommendation,
)


REQUIRED_AGENTS = frozenset(AgentId)


class ManagerReport(BaseModel):
    """Consolidation that preserves specialist reports unchanged."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    reports: tuple[AgentReport, ...]
    missing_agents: tuple[AgentId, ...] = ()
    disagreement: bool
    requires_human_review: bool
    proposed_action: Recommendation
    reason_codes: tuple[str, ...] = Field(min_length=1)
    summary: str = Field(min_length=1)


class ManagerAgent:
    """Validates, compares, and summarizes specialist reports."""

    def consolidate(self, reports: tuple[AgentReport, ...]) -> ManagerReport:
        if not reports:
            raise ValueError("at least one specialist report is required")

        case_ids = {report.case_id for report in reports}
        snapshot_ids = {report.snapshot_id for report in reports}
        if len(case_ids) != 1 or len(snapshot_ids) != 1:
            raise ValueError("all reports must refer to the same case snapshot")

        reports_by_agent = {report.agent_id: report for report in reports}
        if len(reports_by_agent) != len(reports):
            raise ValueError("only one report per specialist agent is allowed")

        missing_agents = tuple(sorted(REQUIRED_AGENTS - reports_by_agent, key=str))
        recommendations = {report.recommendation for report in reports}
        disagreement = len(recommendations) > 1

        proposed_action = self._proposed_action(
            recommendations=recommendations,
            missing_agents=missing_agents,
        )
        adverse = bool(
            recommendations & {Recommendation.DECLINE, Recommendation.REFER}
        )
        requires_human_review = bool(
            missing_agents
            or disagreement
            or adverse
            or Recommendation.REQUEST_MORE_DATA in recommendations
        )

        reason_codes = self._reason_codes(
            reports=reports,
            missing_agents=missing_agents,
            disagreement=disagreement,
        )
        return ManagerReport(
            case_id=reports[0].case_id,
            snapshot_id=reports[0].snapshot_id,
            reports=reports,
            missing_agents=missing_agents,
            disagreement=disagreement,
            requires_human_review=requires_human_review,
            proposed_action=proposed_action,
            reason_codes=reason_codes,
            summary=self._summary(
                reports=reports,
                proposed_action=proposed_action,
                missing_agents=missing_agents,
                disagreement=disagreement,
            ),
        )

    @staticmethod
    def _proposed_action(
        recommendations: set[Recommendation],
        missing_agents: tuple[AgentId, ...],
    ) -> Recommendation:
        if missing_agents or Recommendation.REQUEST_MORE_DATA in recommendations:
            return Recommendation.REQUEST_MORE_DATA
        if len(recommendations) > 1:
            return Recommendation.REFER
        return next(iter(recommendations))

    @staticmethod
    def _reason_codes(
        reports: tuple[AgentReport, ...],
        missing_agents: tuple[AgentId, ...],
        disagreement: bool,
    ) -> tuple[str, ...]:
        reasons: list[str] = []
        if missing_agents:
            reasons.append("MISSING_SPECIALIST_REPORT")
        if disagreement:
            reasons.append("MATERIAL_AGENT_DISAGREEMENT")
        for report in reports:
            for reason_code in report.reason_codes:
                if reason_code not in reasons:
                    reasons.append(reason_code)
        return tuple(reasons)

    @staticmethod
    def _summary(
        reports: tuple[AgentReport, ...],
        proposed_action: Recommendation,
        missing_agents: tuple[AgentId, ...],
        disagreement: bool,
    ) -> str:
        assessments = ", ".join(
            f"{report.agent_id.value}={report.recommendation.value}"
            for report in sorted(reports, key=lambda item: item.agent_id.value)
        )
        qualifiers: list[str] = []
        if missing_agents:
            qualifiers.append(
                "missing " + ", ".join(agent.value for agent in missing_agents)
            )
        if disagreement:
            qualifiers.append("specialists disagree")
        suffix = f"; {'; '.join(qualifiers)}" if qualifiers else ""
        return f"Proposed {proposed_action.value}: {assessments}{suffix}."
