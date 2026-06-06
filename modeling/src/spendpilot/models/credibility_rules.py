"""Deterministic credibility assessment with explicit reason codes."""

from spendpilot.models.contracts import ModelOutput
from spendpilot.schemas.agent_report import (
    CheckStatus,
    FeatureContribution,
    Recommendation,
)
from spendpilot.schemas.case import CaseSnapshot


class CredibilityRulesAdapter:
    """Scores evidence completeness and consistency without an ML model."""

    model_name = "credibility-rules"
    model_version = "v1"

    def predict(self, case: CaseSnapshot) -> ModelOutput:
        features = case.features
        risk = 0.08
        contributions: list[FeatureContribution] = []
        reasons: list[str] = []

        missing_count = len(case.missing_fields)
        if missing_count:
            impact = min(0.12 * missing_count, 0.36)
            risk += impact
            reasons.append("MISSING_DOCUMENTS")
            contributions.append(
                FeatureContribution(
                    feature="missing_documents",
                    value=missing_count,
                    contribution=impact,
                    reason_code="MISSING_DOCUMENTS",
                    evidence_refs=case.evidence_refs,
                )
            )
        if not bool(features.get("income_verified", False)):
            risk += 0.18
            reasons.append("UNVERIFIED_INCOME")
            contributions.append(
                FeatureContribution(
                    feature="income_verified",
                    value=False,
                    contribution=0.18,
                    reason_code="UNVERIFIED_INCOME",
                    evidence_refs=case.evidence_refs,
                )
            )

        coverage = _float(features.get("document_coverage_score"))
        document_count = int(_float(features.get("document_count")))
        if document_count and coverage < 0.25:
            risk += 0.10
            reasons.append("LOW_DOCUMENT_COVERAGE")
            contributions.append(
                FeatureContribution(
                    feature="document_coverage_score",
                    value=coverage,
                    contribution=0.10,
                    reason_code="LOW_DOCUMENT_COVERAGE",
                    evidence_refs=case.evidence_refs,
                )
            )

        flag_count = int(
            _float(features.get("document_consistency_flag_count"))
        )
        if flag_count:
            impact = min(flag_count * 0.08, 0.24)
            risk += impact
            reasons.append("DOCUMENT_INCONSISTENCY")
            contributions.append(
                FeatureContribution(
                    feature="document_consistency_flag_count",
                    value=flag_count,
                    contribution=impact,
                    reason_code="DOCUMENT_INCONSISTENCY",
                    evidence_refs=case.evidence_refs,
                )
            )

        if not reasons:
            reasons.append("EVIDENCE_COMPLETE")
            contributions.append(
                FeatureContribution(
                    feature="evidence_complete",
                    value=True,
                    contribution=-0.08,
                    reason_code="EVIDENCE_COMPLETE",
                    evidence_refs=case.evidence_refs,
                )
            )

        score = min(max(risk, 0.0), 1.0)
        return ModelOutput(
            score=score,
            calibrated_probability=score,
            confidence=max(score, 1.0 - score),
            recommendation=_recommendation(score),
            reason_codes=tuple(reasons),
            top_contributors=tuple(contributions[:3]),
            evidence_refs=case.evidence_refs,
            monotonicity_checks=CheckStatus.NOT_APPLICABLE,
            limitations=(
                "Deterministic checks do not perform identity or fraud verification.",
            ),
        )


def _recommendation(score: float) -> Recommendation:
    if score <= 0.30:
        return Recommendation.APPROVE
    if score <= 0.60:
        return Recommendation.REFER
    return Recommendation.DECLINE


def _float(value: object) -> float:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0
