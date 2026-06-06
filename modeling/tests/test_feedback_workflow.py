from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from spendpilot.agents import (
    AffordabilityAgent,
    CredibilityAgent,
    CreditRiskAgent,
    ManagerAgent,
)
from spendpilot.models import ModelOutput
from spendpilot.orchestration import (
    DecisionWorkflow,
    FeedbackQueue,
    HumanReviewQueue,
    PolicyEngine,
)
from spendpilot.schemas import (
    AgentAssessmentRequest,
    AgentId,
    AnalysisRound,
    CaseSnapshot,
    CheckStatus,
    CreditProduct,
    FeedbackEvent,
    FeedbackSource,
    FeedbackType,
    Recommendation,
)


class FeatureDrivenAdapter:
    def __init__(self, name: str) -> None:
        self.model_name = name
        self.model_version = "v1"
        self.call_count = 0

    def predict(self, case: CaseSnapshot) -> ModelOutput:
        self.call_count += 1
        score = float(case.features.get("risk_score", 0.2))
        return ModelOutput(
            score=score,
            calibrated_probability=score,
            confidence=0.9,
            recommendation=(
                Recommendation.APPROVE
                if score < 0.6
                else Recommendation.REFER
            ),
            reason_codes=(
                "LOW_RISK" if score < 0.6 else "ELEVATED_RISK",
            ),
            monotonicity_checks=CheckStatus.PASSED,
        )


def make_case(
    snapshot_id: str,
    *,
    evidence_refs: tuple[str, ...] = ("evidence_original",),
    risk_score: float = 0.2,
) -> CaseSnapshot:
    return CaseSnapshot(
        case_id="case_feedback",
        snapshot_id=snapshot_id,
        applicant_ref="applicant_token",
        product=CreditProduct.PERSONAL_LOAN,
        requested_amount=Decimal("5000"),
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        content_hash=f"sha256:{snapshot_id[-1] * 64}",
        features={"risk_score": risk_score},
        evidence_refs=evidence_refs,
    )


def make_workflow():
    adapters = {
        AgentId.CREDIBILITY: FeatureDrivenAdapter("credibility"),
        AgentId.AFFORDABILITY: FeatureDrivenAdapter("affordability"),
        AgentId.CREDIT_RISK: FeatureDrivenAdapter("credit-risk"),
    }
    feedback_queue = FeedbackQueue()
    workflow = DecisionWorkflow(
        specialists=(
            CredibilityAgent(adapters[AgentId.CREDIBILITY]),
            AffordabilityAgent(adapters[AgentId.AFFORDABILITY]),
            CreditRiskAgent(adapters[AgentId.CREDIT_RISK]),
        ),
        manager=ManagerAgent(),
        policy_engine=PolicyEngine(),
        review_queue=HumanReviewQueue(),
        feedback_queue=feedback_queue,
    )
    return workflow, feedback_queue, adapters


def test_reviewer_feedback_creates_immutable_round_and_reruns_all_agents() -> None:
    workflow, feedback_queue, adapters = make_workflow()
    first = workflow.run(make_case("snapshot_0"))
    affordability_report = next(
        report
        for report in first.reports
        if report.agent_id is AgentId.AFFORDABILITY
    )
    submitted = FeedbackEvent(
        feedback_id="feedback_1",
        case_id=first.analysis_round.case_id,
        source=FeedbackSource.REVIEWER,
        feedback_type=FeedbackType.DATA_CORRECTION,
        rationale="Verified income evidence changes the derived risk feature.",
        evidence_refs=("evidence_verified",),
        related_report_ids=(affordability_report.report_id,),
        submitter_ref="reviewer_1",
    )
    workflow.submit_feedback(submitted)

    second = workflow.reanalyze(
        previous_result=first,
        feedback_id=submitted.feedback_id,
        revised_case=make_case(
            "snapshot_1",
            evidence_refs=("evidence_original", "evidence_verified"),
            risk_score=0.7,
        ),
        verifier_id="verifier_1",
    )

    assert feedback_queue.get_submission(submitted.feedback_id) == submitted
    assert submitted.selected_targets == ()
    accepted = feedback_queue.get_accepted(submitted.feedback_id)
    assert set(accepted.selected_targets) == {
        AgentId.CREDIBILITY,
        AgentId.AFFORDABILITY,
    }
    assert second.analysis_round.sequence_number == 2
    assert second.analysis_round.parent_round_id == first.analysis_round.round_id
    assert first.analysis_round.snapshot_id == "snapshot_0"
    assert {report.snapshot_id for report in first.reports} == {"snapshot_0"}
    assert {report.snapshot_id for report in second.reports} == {"snapshot_1"}
    assert all(adapter.call_count == 2 for adapter in adapters.values())
    assert all(
        report.feedback_ids == (submitted.feedback_id,)
        for report in second.reports
    )
    responses = {
        report.agent_id: report.responded_feedback_ids
        for report in second.reports
    }
    assert responses[AgentId.CREDIBILITY] == (submitted.feedback_id,)
    assert responses[AgentId.AFFORDABILITY] == (submitted.feedback_id,)
    assert responses[AgentId.CREDIT_RISK] == ()
    assert len(second.manager_report.report_deltas) == 3
    assert all(
        delta.score_delta == pytest.approx(0.5)
        for delta in second.manager_report.report_deltas
    )
    assert second.review_task is not None
    assert second.decision.finalized is False
    assert any(
        rule.rule_id == "FEEDBACK_REANALYSIS_REQUIRES_REVIEW"
        for rule in second.decision.policy_rules
    )


def test_applicant_appeal_requires_verified_snapshot_evidence() -> None:
    workflow, _, _ = make_workflow()
    first = workflow.run(make_case("snapshot_0"))
    appeal = FeedbackEvent(
        feedback_id="appeal_1",
        case_id=first.analysis_round.case_id,
        source=FeedbackSource.APPLICANT,
        feedback_type=FeedbackType.APPEAL,
        rationale="The income evidence used in the decision was incomplete.",
        submitter_ref="applicant_token",
    )
    workflow.submit_feedback(appeal)

    with pytest.raises(ValueError, match="requires verifiable evidence"):
        workflow.reanalyze(
            previous_result=first,
            feedback_id=appeal.feedback_id,
            revised_case=make_case("snapshot_1"),
            verifier_id="verifier_1",
        )


def test_feedback_with_unknown_evidence_is_rejected() -> None:
    workflow, _, _ = make_workflow()
    first = workflow.run(make_case("snapshot_0"))
    feedback = FeedbackEvent(
        feedback_id="feedback_unknown",
        case_id=first.analysis_round.case_id,
        source=FeedbackSource.REVIEWER,
        feedback_type=FeedbackType.NEW_EVIDENCE,
        rationale="Use a newly verified bank statement.",
        evidence_refs=("not_in_snapshot",),
        submitter_ref="reviewer_1",
    )
    workflow.submit_feedback(feedback)

    with pytest.raises(ValueError, match="evidence must exist"):
        workflow.reanalyze(
            previous_result=first,
            feedback_id=feedback.feedback_id,
            revised_case=make_case("snapshot_1"),
            verifier_id="verifier_1",
        )


def test_unverified_feedback_cannot_be_sent_directly_to_agent() -> None:
    case = make_case("snapshot_1")
    feedback = FeedbackEvent(
        feedback_id="feedback_pending",
        case_id=case.case_id,
        source=FeedbackSource.REVIEWER,
        feedback_type=FeedbackType.MODEL_CHALLENGE,
        rationale="Challenge the affordability result.",
        submitter_ref="reviewer_1",
        selected_targets=(AgentId.AFFORDABILITY,),
    )
    analysis_round = AnalysisRound(
        round_id="round_2",
        case_id=case.case_id,
        snapshot_id=case.snapshot_id,
        sequence_number=2,
        parent_round_id="round_1",
        triggering_feedback_ids=(feedback.feedback_id,),
    )

    with pytest.raises(ValidationError, match="only verified feedback"):
        AgentAssessmentRequest(
            agent_id=AgentId.AFFORDABILITY,
            case=case,
            analysis_round=analysis_round,
            targeted_feedback=(feedback,),
        )


def test_reanalysis_requires_a_new_snapshot() -> None:
    workflow, _, _ = make_workflow()
    case = make_case("snapshot_0")
    first = workflow.run(case)
    feedback = FeedbackEvent(
        feedback_id="feedback_same_snapshot",
        case_id=case.case_id,
        source=FeedbackSource.REVIEWER,
        feedback_type=FeedbackType.DATA_CORRECTION,
        rationale="Correction requires a new snapshot.",
        evidence_refs=("evidence_original",),
        submitter_ref="reviewer_1",
    )
    workflow.submit_feedback(feedback)

    with pytest.raises(ValueError, match="new immutable case snapshot"):
        workflow.reanalyze(
            previous_result=first,
            feedback_id=feedback.feedback_id,
            revised_case=case,
            verifier_id="verifier_1",
        )
