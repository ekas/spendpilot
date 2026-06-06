"""Deterministic manager scaffold for specialist communication."""

from pydantic import BaseModel, ConfigDict, Field

from spendpilot.schemas.agent_report import (
    AgentId,
    AgentReport,
    Recommendation,
)
from spendpilot.schemas.case import CaseSnapshot
from spendpilot.schemas.feedback import (
    AgentReportDelta,
    FeedbackEvent,
    FeedbackType,
    VerificationStatus,
)


REQUIRED_AGENTS = frozenset(AgentId)


class ManagerReport(BaseModel):
    """Consolidation that preserves specialist reports unchanged."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    analysis_round_id: str = Field(default="round_initial", min_length=1)
    previous_round_id: str | None = None
    feedback_ids: tuple[str, ...] = ()
    reports: tuple[AgentReport, ...]
    report_deltas: tuple[AgentReportDelta, ...] = ()
    missing_agents: tuple[AgentId, ...] = ()
    disagreement: bool
    requires_human_review: bool
    proposed_action: Recommendation
    reason_codes: tuple[str, ...] = Field(min_length=1)
    summary: str = Field(min_length=1)


class ManagerAgent:
    """Validates, compares, and summarizes specialist reports."""

    def consolidate(
        self,
        reports: tuple[AgentReport, ...],
        *,
        previous_reports: tuple[AgentReport, ...] = (),
        feedback_ids: tuple[str, ...] = (),
    ) -> ManagerReport:
        if not reports:
            raise ValueError("at least one specialist report is required")

        case_ids = {report.case_id for report in reports}
        snapshot_ids = {report.snapshot_id for report in reports}
        round_ids = {report.analysis_round_id for report in reports}
        if (
            len(case_ids) != 1
            or len(snapshot_ids) != 1
            or len(round_ids) != 1
        ):
            raise ValueError("all reports must refer to the same case snapshot")

        reports_by_agent = {report.agent_id: report for report in reports}
        if len(reports_by_agent) != len(reports):
            raise ValueError("only one report per specialist agent is allowed")

        missing_agents = tuple(
            sorted(REQUIRED_AGENTS - reports_by_agent.keys(), key=str)
        )
        recommendations = {report.recommendation for report in reports}
        disagreement = len(recommendations) > 1
        report_deltas = self._report_deltas(
            previous_reports=previous_reports,
            reports=reports,
        )

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
            or feedback_ids
        )

        reason_codes = self._reason_codes(
            reports=reports,
            missing_agents=missing_agents,
            disagreement=disagreement,
        )
        return ManagerReport(
            case_id=reports[0].case_id,
            snapshot_id=reports[0].snapshot_id,
            analysis_round_id=reports[0].analysis_round_id,
            previous_round_id=(
                previous_reports[0].analysis_round_id
                if previous_reports
                else None
            ),
            feedback_ids=feedback_ids,
            reports=reports,
            report_deltas=report_deltas,
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

    def route_feedback(
        self,
        *,
        feedback: FeedbackEvent,
        previous_reports: tuple[AgentReport, ...],
        revised_case: CaseSnapshot,
    ) -> FeedbackEvent:
        if feedback.verification_status is not VerificationStatus.VERIFIED:
            raise ValueError("only verified feedback can be routed")
        if feedback.case_id != revised_case.case_id:
            raise ValueError("feedback belongs to another case")
        if not set(feedback.evidence_refs).issubset(revised_case.evidence_refs):
            raise ValueError(
                "feedback evidence must exist in the revised case snapshot"
            )

        reports_by_id = {
            report.report_id: report for report in previous_reports
        }
        unknown_reports = set(feedback.related_report_ids) - reports_by_id.keys()
        if unknown_reports:
            raise ValueError("feedback references unknown specialist reports")

        targets: set[AgentId]
        if feedback.feedback_type is FeedbackType.APPEAL:
            targets = set(REQUIRED_AGENTS)
        elif feedback.feedback_type is FeedbackType.MODEL_CHALLENGE:
            if not feedback.related_report_ids:
                raise ValueError(
                    "model challenges require related specialist reports"
                )
            targets = {
                reports_by_id[report_id].agent_id
                for report_id in feedback.related_report_ids
            }
        else:
            targets = {AgentId.CREDIBILITY}
            targets.update(
                reports_by_id[report_id].agent_id
                for report_id in feedback.related_report_ids
            )

        return feedback.model_copy(
            update={
                "selected_targets": tuple(
                    sorted(targets, key=lambda target: target.value)
                )
            }
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
    def _report_deltas(
        *,
        previous_reports: tuple[AgentReport, ...],
        reports: tuple[AgentReport, ...],
    ) -> tuple[AgentReportDelta, ...]:
        if not previous_reports:
            return ()
        previous_by_agent = {
            report.agent_id: report for report in previous_reports
        }
        if set(previous_by_agent) != {report.agent_id for report in reports}:
            raise ValueError(
                "previous and current rounds require the same specialists"
            )
        return tuple(
            AgentReportDelta.compare(
                previous=previous_by_agent[report.agent_id],
                current=report,
            )
            for report in sorted(reports, key=lambda item: item.agent_id.value)
        )

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
