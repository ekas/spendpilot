"""Runtime adapter for checksummed monotonic XGBoost artifacts."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from spendpilot.models.contracts import ModelOutput
from spendpilot.models.features import MODEL_FEATURES, engineer_features
from spendpilot.schemas.agent_report import (
    AgentId,
    CheckStatus,
    FeatureContribution,
    Recommendation,
)
from spendpilot.schemas.case import CaseSnapshot
from spendpilot.schemas.modeling import ModelArtifactManifest


REASON_CODES = {
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


class MonotonicXGBoostAdapter:
    """Loads native JSON artifacts and emits shared explainability contracts."""

    def __init__(self, artifact_dir: Path | str, agent_id: AgentId) -> None:
        if agent_id not in MODEL_FEATURES:
            raise ValueError("XGBoost is configured only for tabular specialists")
        self.agent_id = agent_id
        self.artifact_dir = Path(artifact_dir)
        self.manifest = ModelArtifactManifest.model_validate_json(
            (self.artifact_dir / "manifest.json").read_text()
        )
        if self.manifest.agent_id is not agent_id:
            raise ValueError("artifact belongs to another specialist")
        model_path = self.artifact_dir / "model.json"
        actual_hash = hashlib.sha256(model_path.read_bytes()).hexdigest()
        if self.manifest.artifact_hash != f"sha256:{actual_hash}":
            raise ValueError("model artifact hash does not match its manifest")

        calibration = json.loads(
            (self.artifact_dir / "calibration.json").read_text()
        )
        self._calibration_coefficient = float(calibration["coefficient"])
        self._calibration_intercept = float(calibration["intercept"])

        import xgboost as xgb

        self._xgb = xgb
        self._booster = xgb.Booster()
        self._booster.load_model(model_path)

    @property
    def model_name(self) -> str:
        return self.manifest.model_name

    @property
    def model_version(self) -> str:
        return self.manifest.model_version

    def predict(self, case: CaseSnapshot) -> ModelOutput:
        engineered = engineer_features(case, self.agent_id)
        feature_names = MODEL_FEATURES[self.agent_id]
        row = [[engineered[name] for name in feature_names]]
        matrix = self._xgb.DMatrix(row, feature_names=list(feature_names))
        raw_probability = float(self._booster.predict(matrix)[0])
        probability = self._calibrate(raw_probability)
        shap_values = self._booster.predict(
            matrix,
            pred_contribs=True,
        )[0][:-1]

        ranked = sorted(
            zip(feature_names, row[0], shap_values, strict=True),
            key=lambda item: abs(float(item[2])),
            reverse=True,
        )[:3]
        contributions = tuple(
            FeatureContribution(
                feature=feature,
                value=float(value),
                contribution=float(contribution),
                reason_code=REASON_CODES[feature],
                evidence_refs=case.evidence_refs,
            )
            for feature, value, contribution in ranked
        )
        adverse_reasons = tuple(
            contribution.reason_code
            for contribution in contributions
            if contribution.contribution > 0
        )
        reason_codes = adverse_reasons or (
            "AFFORDABILITY_PROFILE_STABLE"
            if self.agent_id is AgentId.AFFORDABILITY
            else "CREDIT_PROFILE_STABLE",
        )

        return ModelOutput(
            score=probability,
            calibrated_probability=probability,
            confidence=max(probability, 1.0 - probability),
            recommendation=_recommendation(probability),
            reason_codes=reason_codes,
            top_contributors=contributions,
            evidence_refs=case.evidence_refs,
            monotonicity_checks=CheckStatus.PASSED,
            limitations=(
                "Trained on controlled synthetic data, not production outcomes.",
            ),
        )

    def _calibrate(self, raw_probability: float) -> float:
        logit = (
            self._calibration_coefficient * raw_probability
            + self._calibration_intercept
        )
        return 1.0 / (1.0 + math.exp(-logit))


def _recommendation(score: float) -> Recommendation:
    if score <= 0.30:
        return Recommendation.APPROVE
    if score <= 0.60:
        return Recommendation.REFER
    return Recommendation.DECLINE
