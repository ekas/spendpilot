from decimal import Decimal

import pytest
from pydantic import ValidationError

from spendpilot.agents import (
    AffordabilityAgent,
    CredibilityAgent,
    CreditRiskAgent,
    ManagerAgent,
)
from spendpilot.models import ModelOutput, StaticModelAdapter
from spendpilot.schemas import (
    AgentId,
    AgentReport,
    CaseSnapshot,
    CheckStatus,
    CreditProduct,
    Recommendation,
)


def make_case() -> CaseSnapshot:
    return CaseSnapshot(
        case_id="case_123",
        snapshot_id="snapshot_1",
        applicant_ref="applicant_token_1",
        product=CreditProduct.PERSONAL_LOAN,
        requested_amount=Decimal("5000"),
        content_hash=f"sha256:{'0' * 64}",
        features={"debt_to_income": 0.28},
        evidence_refs=("bureau_1", "bank_1"),
    )


def make_adapter(
    name: str,
    recommendation: Recommendation = Recommendation.APPROVE,
    score: float = 0.20,
) -> StaticModelAdapter:
    return StaticModelAdapter(
        model_name=name,
        model_version="v1",
        output=ModelOutput(
            score=score,
            calibrated_probability=score,
            confidence=0.90,
            recommendation=recommendation,
            reason_codes=("STABLE_PROFILE",),
            evidence_refs=("bank_1",),
            monotonicity_checks=CheckStatus.PASSED,
        ),
    )


def test_specialists_emit_the_shared_agent_report_contract() -> None:
    case = make_case()
    agents = (
        CredibilityAgent(make_adapter("credibility-xgb")),
        AffordabilityAgent(make_adapter("affordability-xgb")),
        CreditRiskAgent(make_adapter("credit-risk-xgb")),
    )

    reports = tuple(agent.assess(case) for agent in agents)

    assert all(isinstance(report, AgentReport) for report in reports)
    assert {report.agent_id for report in reports} == set(AgentId)
    assert {report.case_id for report in reports} == {case.case_id}
    assert len({report.report_id for report in reports}) == 3


def test_agent_report_rejects_unknown_fields_and_invalid_scores() -> None:
    valid = {
        "report_id": "report_1",
        "case_id": "case_1",
        "snapshot_id": "snapshot_1",
        "agent_id": AgentId.CREDIT_RISK,
        "model_name": "credit-risk-xgb",
        "model_version": "v1",
        "score": 0.3,
        "recommendation": Recommendation.APPROVE,
        "reason_codes": ("LOW_DEFAULT_RISK",),
    }

    with pytest.raises(ValidationError):
        AgentReport(**{**valid, "score": 1.5})
    with pytest.raises(ValidationError):
        AgentReport(**valid, invented_explanation="not allowed")


def test_manager_preserves_reports_and_detects_disagreement() -> None:
    case = make_case()
    reports = (
        CredibilityAgent(make_adapter("credibility")).assess(case),
        AffordabilityAgent(
            make_adapter(
                "affordability",
                recommendation=Recommendation.REFER,
                score=0.65,
            )
        ).assess(case),
        CreditRiskAgent(make_adapter("credit-risk")).assess(case),
    )

    manager_report = ManagerAgent().consolidate(reports)

    assert manager_report.reports == reports
    assert tuple(report.score for report in manager_report.reports) == (
        0.20,
        0.65,
        0.20,
    )
    assert manager_report.disagreement is True
    assert manager_report.requires_human_review is True
    assert manager_report.proposed_action is Recommendation.REFER
    assert "MATERIAL_AGENT_DISAGREEMENT" in manager_report.reason_codes
