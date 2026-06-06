from decimal import Decimal

from spendpilot.agents import (
    AffordabilityAgent,
    CredibilityAgent,
    CreditRiskAgent,
    ManagerAgent,
)
from spendpilot.models import ModelOutput, StaticModelAdapter
from spendpilot.orchestration import (
    DecisionWorkflow,
    HumanReviewAction,
    HumanReviewQueue,
    HumanReviewResolution,
    PolicyEngine,
)
from spendpilot.schemas import (
    CaseSnapshot,
    CheckStatus,
    CreditProduct,
    DecisionAction,
    Recommendation,
)


def make_case() -> CaseSnapshot:
    return CaseSnapshot(
        case_id="case_456",
        snapshot_id="snapshot_2",
        applicant_ref="applicant_token_2",
        product=CreditProduct.CREDIT_CARD,
        requested_amount=Decimal("2500"),
        content_hash=f"sha256:{'a' * 64}",
        features={"credit_utilization": 0.31},
        evidence_refs=("bureau_2",),
    )


def make_agent(agent_type, recommendation: Recommendation, score: float = 0.2):
    output = ModelOutput(
        score=score,
        calibrated_probability=score,
        confidence=0.90,
        recommendation=recommendation,
        reason_codes=(f"{agent_type.agent_id.value.upper()}_REASON",),
        monotonicity_checks=CheckStatus.PASSED,
    )
    return agent_type(
        StaticModelAdapter(
            model_name=f"{agent_type.agent_id.value}-xgb",
            model_version="v1",
            output=output,
        )
    )


def make_workflow(recommendations: tuple[Recommendation, ...]) -> DecisionWorkflow:
    agent_types = (CredibilityAgent, AffordabilityAgent, CreditRiskAgent)
    specialists = tuple(
        make_agent(agent_type, recommendation)
        for agent_type, recommendation in zip(
            agent_types, recommendations, strict=True
        )
    )
    return DecisionWorkflow(
        specialists=specialists,
        manager=ManagerAgent(),
        policy_engine=PolicyEngine(),
        review_queue=HumanReviewQueue(),
    )


def test_unanimous_approval_is_finalized_by_policy_engine() -> None:
    workflow = make_workflow((Recommendation.APPROVE,) * 3)

    result = workflow.run(make_case())

    assert result.manager_report.requires_human_review is False
    assert result.decision.action is DecisionAction.APPROVE
    assert result.decision.finalized is True
    assert result.review_task is None
    assert any(
        rule.rule_id == "UNANIMOUS_AUTOMATIC_APPROVAL"
        for rule in result.decision.policy_rules
    )


def test_disagreement_routes_to_human_review() -> None:
    workflow = make_workflow(
        (
            Recommendation.APPROVE,
            Recommendation.REFER,
            Recommendation.APPROVE,
        )
    )

    result = workflow.run(make_case())

    assert result.decision.action is DecisionAction.REFER
    assert result.decision.finalized is False
    assert result.review_task is not None
    assert result.manager_report.disagreement is True


def test_adverse_recommendation_requires_human_resolution() -> None:
    workflow = make_workflow((Recommendation.DECLINE,) * 3)
    result = workflow.run(make_case())
    assert result.review_task is not None
    assert result.decision.finalized is False

    final_decision = workflow.resolve_review(
        HumanReviewResolution(
            review_id=result.review_task.review_id,
            reviewer_id="reviewer_1",
            action=HumanReviewAction.APPROVE_RECOMMENDATION,
            rationale="Evidence and principal reason codes were verified.",
        )
    )

    assert final_decision.action is DecisionAction.DECLINE
    assert final_decision.finalized is True
    assert final_decision.human_review_id == result.review_task.review_id


def test_human_override_returns_to_policy_engine() -> None:
    workflow = make_workflow(
        (
            Recommendation.APPROVE,
            Recommendation.REFER,
            Recommendation.APPROVE,
        )
    )
    result = workflow.run(make_case())
    assert result.review_task is not None

    final_decision = workflow.resolve_review(
        HumanReviewResolution(
            review_id=result.review_task.review_id,
            reviewer_id="reviewer_2",
            action=HumanReviewAction.OVERRIDE_DECISION,
            override_action=DecisionAction.APPROVE,
            rationale="Verified income evidence resolves the affordability concern.",
        )
    )

    assert final_decision.action is DecisionAction.APPROVE
    assert final_decision.finalized is True
    assert any(
        rule.rule_id == "HUMAN_RESOLUTION_APPLIED"
        for rule in final_decision.policy_rules
    )


def test_missing_specialist_requests_more_data() -> None:
    case = make_case()
    reports = (
        make_agent(CredibilityAgent, Recommendation.APPROVE).assess(case),
        make_agent(AffordabilityAgent, Recommendation.APPROVE).assess(case),
    )
    manager_report = ManagerAgent().consolidate(reports)

    decision = PolicyEngine().evaluate(manager_report)

    assert decision.action is DecisionAction.REQUEST_MORE_DATA
    assert decision.finalized is False
    assert any(
        rule.rule_id == "INCOMPLETE_REPORT_SET"
        for rule in decision.policy_rules
    )
