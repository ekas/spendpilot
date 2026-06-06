"""Interfaces that keep language models outside decision authority."""

from __future__ import annotations

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


class ManagerAssistant(Protocol):
    """Optional narrative and routing assistance used by the Manager."""

    def narrate(
        self,
        manager_report: ManagerReport,
        benchmark_context: BenchmarkContext | None,
    ) -> ManagerNarrative:
        """Explain an already-computed deterministic manager report."""

    def propose_feedback_routing(
        self,
        *,
        feedback: FeedbackEvent,
        previous_reports: tuple[AgentReport, ...],
        allowed_targets: frozenset[AgentId],
    ) -> FeedbackRoutingProposal:
        """Propose targets without changing feedback, reports, or scores."""
