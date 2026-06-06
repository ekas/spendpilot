"""Structured language-model assistance with strict JSON-only interfaces."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from spendpilot.schemas.agent_report import AgentId, AgentReport
from spendpilot.schemas.feedback import FeedbackEvent
from spendpilot.schemas.modeling import (
    BenchmarkContext,
    FeedbackRoutingProposal,
    ManagerNarrative,
)

if TYPE_CHECKING:
    from spendpilot.agents.manager import ManagerReport


MAX_INPUT_CHARACTERS = 12_000
MAX_OUTPUT_TOKENS = 256


@dataclass(frozen=True)
class JSONCompletionResult:
    """Content and provider provenance returned by a hosted model."""

    content: str
    provider: str
    model: str
    request_id: str | None = None


class JSONCompletionClient(Protocol):
    """Minimum completion behavior required by the Manager assistant."""

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        max_output_tokens: int,
    ) -> JSONCompletionResult:
        """Return one JSON object plus immutable provider metadata."""


class StructuredManagerAssistant:
    """Produces bounded explanations and feedback-routing proposals."""

    def __init__(self, client: JSONCompletionClient) -> None:
        self._client = client

    def narrate(
        self,
        manager_report: ManagerReport,
        benchmark_context: BenchmarkContext | None,
    ) -> ManagerNarrative:
        payload = {
            "proposed_action": manager_report.proposed_action.value,
            "disagreement": manager_report.disagreement,
            "requires_human_review": manager_report.requires_human_review,
            "reason_codes": manager_report.reason_codes,
            "reports": [
                {
                    "agent_id": report.agent_id.value,
                    "score": report.score,
                    "recommendation": report.recommendation.value,
                    "reason_codes": report.reason_codes,
                    "top_contributors": [
                        {
                            "feature": contribution.feature,
                            "contribution": contribution.contribution,
                            "reason_code": contribution.reason_code,
                            "evidence_refs": contribution.evidence_refs,
                        }
                        for contribution in report.top_contributors
                    ],
                    "limitations": report.limitations,
                }
                for report in manager_report.reports
            ],
            "report_deltas": [
                delta.model_dump(mode="json")
                for delta in manager_report.report_deltas
            ],
            "benchmark_context": (
                benchmark_context.model_dump(mode="json")
                if benchmark_context
                else None
            ),
        }
        response = self._complete(
            system=(
                "You explain already-computed credit model reports to a human "
                "reviewer. Do not make a credit decision, change scores, or "
                "invent evidence. Return only JSON with keys summary, "
                "disagreement_explanation, reviewer_focus, and limitations. "
                "Do not reveal hidden reasoning."
            ),
            payload=payload,
        )
        narrative = ManagerNarrative.model_validate(
            _parse_json_object(response.content)
        )
        return narrative.model_copy(
            update={
                "assistant_provider": response.provider,
                "assistant_model": response.model,
                "assistant_request_id": response.request_id,
            }
        )

    def propose_feedback_routing(
        self,
        *,
        feedback: FeedbackEvent,
        previous_reports: tuple[AgentReport, ...],
        allowed_targets: frozenset[AgentId],
    ) -> FeedbackRoutingProposal:
        payload = {
            "feedback_id": feedback.feedback_id,
            "feedback_type": feedback.feedback_type.value,
            "evidence_refs": feedback.evidence_refs,
            "related_report_ids": feedback.related_report_ids,
            "allowed_targets": sorted(target.value for target in allowed_targets),
            "reports": [
                {
                    "report_id": report.report_id,
                    "agent_id": report.agent_id.value,
                    "recommendation": report.recommendation.value,
                    "reason_codes": report.reason_codes,
                }
                for report in previous_reports
            ],
        }
        response = self._complete(
            system=(
                "Route verified credit-case feedback to relevant specialist "
                "agents. Use only allowed_targets. Do not make a decision, "
                "change a score, or infer facts from free text. Return only "
                "JSON with feedback_id, proposed_targets, and rationale_codes."
            ),
            payload=payload,
        )
        proposal = FeedbackRoutingProposal.model_validate(
            _parse_json_object(response.content)
        )
        return proposal.model_copy(
            update={
                "assistant_provider": response.provider,
                "assistant_model": response.model,
                "assistant_request_id": response.request_id,
            }
        )

    def _complete(
        self,
        *,
        system: str,
        payload: dict[str, object],
    ) -> JSONCompletionResult:
        user = json.dumps(payload, separators=(",", ":"))
        if len(system) + len(user) > MAX_INPUT_CHARACTERS:
            raise ValueError("Manager assistant input exceeds the safe limit")
        return self._client.complete_json(
            system=system,
            user=user,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )


def _parse_json_object(text: str) -> dict[str, object]:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines)
    parsed = json.loads(stripped)
    if not isinstance(parsed, dict):
        raise ValueError("Manager assistant response must be one JSON object")
    return parsed
