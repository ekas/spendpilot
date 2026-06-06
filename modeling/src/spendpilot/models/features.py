"""Stable feature engineering shared by training and inference."""

from __future__ import annotations

from decimal import Decimal

from spendpilot.schemas.agent_report import AgentId
from spendpilot.schemas.case import CaseSnapshot


AFFORDABILITY_FEATURES = (
    "debt_to_income",
    "installment_burden",
    "expense_ratio",
    "overdrafts_90d",
    "income_unverified",
)

CREDIT_RISK_FEATURES = (
    "credit_utilization",
    "delinquencies_12m",
    "employment_shortfall_months",
    "annual_debt_ratio",
    "overdrafts_90d",
)

MODEL_FEATURES = {
    AgentId.AFFORDABILITY: AFFORDABILITY_FEATURES,
    AgentId.CREDIT_RISK: CREDIT_RISK_FEATURES,
}


def engineer_features(
    case: CaseSnapshot,
    agent_id: AgentId,
) -> dict[str, float]:
    """Create monotonic adverse-risk features for one specialist."""

    features = case.features
    income = max(_float(features.get("monthly_income")), 1.0)
    expenses = max(_float(features.get("monthly_expenses")), 0.0)
    debt = max(_float(features.get("existing_debt")), 0.0)
    overdrafts = max(_float(features.get("overdrafts_90d")), 0.0)

    if agent_id is AgentId.AFFORDABILITY:
        free_cash_flow = max(income - expenses, 1.0)
        installment = float(Decimal(case.requested_amount) / Decimal("36"))
        return {
            "debt_to_income": debt / income,
            "installment_burden": installment / free_cash_flow,
            "expense_ratio": expenses / income,
            "overdrafts_90d": overdrafts,
            "income_unverified": float(
                not bool(features.get("income_verified", False))
            ),
        }
    if agent_id is AgentId.CREDIT_RISK:
        employment_months = max(
            _float(features.get("employment_months")),
            0.0,
        )
        return {
            "credit_utilization": min(
                max(_float(features.get("credit_utilization")), 0.0),
                1.0,
            ),
            "delinquencies_12m": max(
                _float(features.get("delinquencies_12m")),
                0.0,
            ),
            "employment_shortfall_months": max(
                12.0 - employment_months,
                0.0,
            ),
            "annual_debt_ratio": debt / (income * 12.0),
            "overdrafts_90d": overdrafts,
        }
    raise ValueError(f"no model features configured for {agent_id}")


def _float(value: object) -> float:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0
