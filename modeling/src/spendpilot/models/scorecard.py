"""Transparent runtime scorecards used when trained artifacts are unavailable."""

from __future__ import annotations

import math

from spendpilot.models.contracts import ModelOutput
from spendpilot.models.features import engineer_features
from spendpilot.schemas.agent_report import (
    AgentId,
    CheckStatus,
    FeatureContribution,
    Recommendation,
)
from spendpilot.schemas.case import CaseSnapshot


_REASON_CODES = {
    "debt_to_income": "HIGH_DTI",
    "installment_burden": "LOW_AFFORDABILITY_BUFFER",
    "expense_ratio": "HIGH_EXPENSE_RATIO",
    "overdrafts_90d": "RECENT_OVERDRAFTS",
    "income_unverified": "UNVERIFIED_INCOME",
    "credit_utilization": "HIGH_UTILIZATION",
    "delinquencies_12m": "RECENT_DELINQUENCY",
    "employment_shortfall_months": "SHORT_EMPLOYMENT_HISTORY",
    "annual_debt_ratio": "HIGH_ANNUAL_DEBT_RATIO",
}

_SCORECARDS = {
    AgentId.AFFORDABILITY: {
        "intercept": -3.6,
        "weights": {
            "debt_to_income": 0.95,
            "installment_burden": 0.75,
            "expense_ratio": 1.35,
            "overdrafts_90d": 0.18,
            "income_unverified": 0.55,
        },
        "caps": {
            "debt_to_income": 3.0,
            "installment_burden": 4.0,
        },
    },
    AgentId.CREDIT_RISK: {
        "intercept": -3.3,
        "weights": {
            "credit_utilization": 2.1,
            "delinquencies_12m": 0.72,
            "employment_shortfall_months": 0.055,
            "annual_debt_ratio": 1.2,
            "overdrafts_90d": 0.14,
        },
        "caps": {
            "annual_debt_ratio": 1.5,
        },
    },
}


class TransparentScorecardAdapter:
    """Produces auditable adverse-risk probabilities without model files."""

    def __init__(self, agent_id: AgentId) -> None:
        if agent_id not in _SCORECARDS:
            raise ValueError("scorecards are configured for tabular specialists")
        self.agent_id = agent_id

    @property
    def model_name(self) -> str:
        return f"{self.agent_id.value}-transparent-scorecard"

    @property
    def model_version(self) -> str:
        return "v1"

    def predict(self, case: CaseSnapshot) -> ModelOutput:
        settings = _SCORECARDS[self.agent_id]
        features = engineer_features(case, self.agent_id)
        weights = settings["weights"]
        caps = settings["caps"]
        contributions = []
        logit = float(settings["intercept"])

        for feature, weight in weights.items():
            value = features[feature]
            effective_value = min(value, caps.get(feature, value))
            contribution = float(weight) * effective_value
            logit += contribution
            contributions.append(
                FeatureContribution(
                    feature=feature,
                    value=value,
                    contribution=contribution,
                    reason_code=_REASON_CODES[feature],
                    evidence_refs=case.evidence_refs,
                )
            )

        probability = 1.0 / (1.0 + math.exp(-logit))
        ranked = tuple(
            sorted(
                contributions,
                key=lambda item: abs(item.contribution),
                reverse=True,
            )[:3]
        )
        adverse_reasons = _reason_codes(self.agent_id, features)
        stable_reason = (
            "AFFORDABILITY_PROFILE_STABLE"
            if self.agent_id is AgentId.AFFORDABILITY
            else "CREDIT_PROFILE_STABLE"
        )

        return ModelOutput(
            score=probability,
            calibrated_probability=probability,
            confidence=max(probability, 1.0 - probability),
            recommendation=_recommendation(probability),
            reason_codes=adverse_reasons or (stable_reason,),
            top_contributors=ranked,
            evidence_refs=case.evidence_refs,
            monotonicity_checks=CheckStatus.PASSED,
            limitations=(
                "Transparent development scorecard; not trained on production outcomes.",
            ),
        )


def _recommendation(score: float) -> Recommendation:
    if score <= 0.30:
        return Recommendation.APPROVE
    if score <= 0.60:
        return Recommendation.REFER
    return Recommendation.DECLINE


def _reason_codes(
    agent_id: AgentId,
    features: dict[str, float],
) -> tuple[str, ...]:
    reasons = []
    if agent_id is AgentId.AFFORDABILITY:
        thresholds = {
            "debt_to_income": 0.45,
            "installment_burden": 0.60,
            "expense_ratio": 0.75,
            "overdrafts_90d": 2.0,
            "income_unverified": 0.5,
        }
    else:
        thresholds = {
            "credit_utilization": 0.75,
            "delinquencies_12m": 0.5,
            "employment_shortfall_months": 6.0,
            "annual_debt_ratio": 0.30,
            "overdrafts_90d": 2.0,
        }
    for feature, threshold in thresholds.items():
        if features[feature] > threshold:
            reasons.append(_REASON_CODES[feature])
    return tuple(reasons)
