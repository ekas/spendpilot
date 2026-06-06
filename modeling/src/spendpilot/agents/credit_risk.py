"""Credit-risk specialist agent."""

from spendpilot.agents.base import SpecialistAgent
from spendpilot.schemas.agent_report import AgentId


class CreditRiskAgent(SpecialistAgent):
    """Estimates default risk from repayment and utilization features."""

    agent_id = AgentId.CREDIT_RISK
