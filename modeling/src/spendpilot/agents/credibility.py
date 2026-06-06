"""Data credibility specialist agent."""

from spendpilot.agents.base import SpecialistAgent
from spendpilot.schemas.agent_report import AgentId


class CredibilityAgent(SpecialistAgent):
    """Assesses data completeness, consistency, and source reliability."""

    agent_id = AgentId.CREDIBILITY
