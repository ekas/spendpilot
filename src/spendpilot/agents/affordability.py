"""Affordability specialist agent."""

from spendpilot.agents.base import SpecialistAgent
from spendpilot.schemas.agent_report import AgentId


class AffordabilityAgent(SpecialistAgent):
    """Assesses repayment capacity from income and cash-flow features."""

    agent_id = AgentId.AFFORDABILITY
