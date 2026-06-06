from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from spendpilot.models import (
    ModelDescriptor,
    ModelOutput,
    ModelRegistry,
    ModelStatus,
    StaticModelAdapter,
)
from spendpilot.outcomes import (
    CandidateApproval,
    CandidateModelEvaluation,
    OutcomeLearningPipeline,
)
from spendpilot.schemas import (
    AgentId,
    CaseSnapshot,
    CreditProduct,
    DecisionAction,
    DecisionRecord,
    OutcomeEvent,
    OutcomeSource,
    PaymentStatus,
    Recommendation,
)


def make_snapshot(
    *,
    snapshot_id: str = "snapshot_original",
    created_at: datetime = datetime(2025, 1, 1, tzinfo=timezone.utc),
) -> CaseSnapshot:
    return CaseSnapshot(
        case_id="case_outcome",
        snapshot_id=snapshot_id,
        applicant_ref="applicant_token",
        product=CreditProduct.PERSONAL_LOAN,
        requested_amount=Decimal("7500"),
        created_at=created_at,
        content_hash=f"sha256:{'a' * 64}",
        features={"debt_to_income": 0.32},
    )


def make_decision(
    *,
    action: DecisionAction = DecisionAction.APPROVE,
    finalized: bool = True,
) -> DecisionRecord:
    return DecisionRecord(
        decision_id="decision_1",
        case_id="case_outcome",
        snapshot_id="snapshot_original",
        policy_version="consumer-credit-v1",
        action=action,
        reason_codes=("POLICY_PASS",),
        finalized=finalized,
        decided_at=datetime(2025, 1, 2, tzinfo=timezone.utc),
    )


def make_event(
    event_id: str,
    *,
    days_past_due: int,
    observation_date: date,
    source_event_ref: str | None = None,
) -> OutcomeEvent:
    return OutcomeEvent(
        outcome_event_id=event_id,
        decision_id="decision_1",
        case_id="case_outcome",
        account_ref="account_token",
        payment_status=(
            PaymentStatus.CURRENT
            if days_past_due == 0
            else PaymentStatus.DELINQUENT
        ),
        days_past_due=days_past_due,
        observation_date=observation_date,
        source=OutcomeSource.LOAN_SERVICER,
        source_event_ref=source_event_ref or f"source_{event_id}",
    )


def test_outcomes_are_append_only_and_deduplicated() -> None:
    pipeline = OutcomeLearningPipeline()
    event = make_event(
        "outcome_1",
        days_past_due=0,
        observation_date=date(2025, 2, 1),
    )
    pipeline.ingest(event)

    with pytest.raises(ValueError, match="already exists"):
        pipeline.ingest(event)
    with pytest.raises(ValueError, match="already ingested"):
        pipeline.ingest(
            make_event(
                "outcome_2",
                days_past_due=30,
                observation_date=date(2025, 3, 1),
                source_event_ref=event.source_event_ref,
            )
        )
    assert pipeline.store.get(event.outcome_event_id) == event


def test_90_plus_dpd_matures_positive_label_inside_window() -> None:
    pipeline = OutcomeLearningPipeline()
    pipeline.ingest(
        make_event(
            "outcome_default",
            days_past_due=95,
            observation_date=date(2025, 8, 1),
        )
    )

    label = pipeline.dataset_builder.label(
        make_decision(),
        as_of=date(2025, 8, 2),
    )

    assert label.mature is True
    assert label.value == 1
    assert label.positive_event_ids == ("outcome_default",)


def test_negative_label_matures_only_after_full_window() -> None:
    pipeline = OutcomeLearningPipeline()
    decision = make_decision()

    immature = pipeline.dataset_builder.label(
        decision,
        as_of=date(2025, 12, 31),
    )
    mature = pipeline.dataset_builder.label(
        decision,
        as_of=date(2026, 1, 2),
    )

    assert immature.mature is False
    assert immature.value is None
    assert mature.mature is True
    assert mature.value == 0


def test_dataset_uses_only_original_point_in_time_snapshot() -> None:
    pipeline = OutcomeLearningPipeline()
    decision = make_decision()
    original = make_snapshot()
    revised = make_snapshot(
        snapshot_id="snapshot_revised",
        created_at=datetime(2025, 2, 1, tzinfo=timezone.utc),
    )

    dataset = pipeline.dataset_builder.build(
        dataset_id="dataset_1",
        decisions=(decision,),
        snapshots={
            original.snapshot_id: original,
            revised.snapshot_id: revised,
        },
        as_of=date(2026, 1, 2),
    )

    assert len(dataset.examples) == 1
    assert dataset.examples[0].snapshot_id == original.snapshot_id
    assert dataset.examples[0].features == original.features


def test_dataset_rejects_snapshot_created_after_decision() -> None:
    pipeline = OutcomeLearningPipeline()
    future_snapshot = make_snapshot(
        created_at=datetime(2025, 1, 3, tzinfo=timezone.utc)
    )

    with pytest.raises(ValueError, match="after the decision"):
        pipeline.dataset_builder.build(
            dataset_id="dataset_invalid",
            decisions=(make_decision(),),
            snapshots={future_snapshot.snapshot_id: future_snapshot},
            as_of=date(2026, 1, 2),
        )


def test_outcome_pipeline_cannot_modify_active_registry() -> None:
    registry = ModelRegistry()
    adapter = StaticModelAdapter(
        model_name="credit-risk-xgb",
        model_version="v1",
        output=ModelOutput(
            score=0.2,
            recommendation=Recommendation.APPROVE,
            reason_codes=("LOW_RISK",),
        ),
    )
    registry.register(
        ModelDescriptor(
            agent_id=AgentId.CREDIT_RISK,
            model_name=adapter.model_name,
            model_version=adapter.model_version,
            status=ModelStatus.VALIDATED,
        ),
        adapter,
    )
    before = registry.descriptors()
    pipeline = OutcomeLearningPipeline()
    pipeline.ingest(
        make_event(
            "outcome_registry",
            days_past_due=95,
            observation_date=date(2025, 8, 1),
        )
    )
    evaluation = CandidateModelEvaluation(
        evaluation_id="evaluation_1",
        candidate_model_name="credit-risk-xgb",
        candidate_model_version="v2",
        agent_id=AgentId.CREDIT_RISK,
        dataset_id="dataset_1",
        metrics={"roc_auc": 0.82, "brier_score": 0.13},
        passed_validation=True,
        evaluated_by="validator_1",
    )
    pipeline.record_evaluation(evaluation)
    pipeline.approve(
        CandidateApproval(
            approval_id="approval_1",
            evaluation_id=evaluation.evaluation_id,
            approved=True,
            approver_id="model_risk_1",
            rationale="Validation and fairness checks passed.",
        )
    )

    assert registry.descriptors() == before
    assert registry.get(AgentId.CREDIT_RISK) is adapter


def test_failed_candidate_cannot_be_approved() -> None:
    pipeline = OutcomeLearningPipeline()
    evaluation = CandidateModelEvaluation(
        evaluation_id="evaluation_failed",
        candidate_model_name="credit-risk-xgb",
        candidate_model_version="v2",
        agent_id=AgentId.CREDIT_RISK,
        dataset_id="dataset_1",
        metrics={"roc_auc": 0.55},
        passed_validation=False,
        evaluated_by="validator_1",
    )
    pipeline.record_evaluation(evaluation)

    with pytest.raises(ValueError, match="failed candidate"):
        pipeline.approve(
            CandidateApproval(
                approval_id="approval_invalid",
                evaluation_id=evaluation.evaluation_id,
                approved=True,
                approver_id="model_risk_1",
                rationale="Should not pass.",
            )
        )
