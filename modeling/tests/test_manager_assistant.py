import json
from decimal import Decimal

from spendpilot.agents import (
    AffordabilityAgent,
    CredibilityAgent,
    CreditRiskAgent,
    ManagerAgent,
    ManagerAssistantStatus,
)
from spendpilot.assistants.structured import (
    JSONCompletionResult,
    StructuredManagerAssistant,
)
from spendpilot.models import ModelOutput, StaticModelAdapter
from spendpilot.schemas import (
    AgentId,
    BenchmarkContext,
    CaseSnapshot,
    CreditProduct,
    FeedbackEvent,
    FeedbackSource,
    FeedbackType,
    Recommendation,
    VerificationStatus,
)


class FakeJSONClient:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.requests: list[dict[str, object]] = []

    def complete_json(self, **kwargs) -> JSONCompletionResult:
        self.requests.append(kwargs)
        response = self.responses.pop(0)
        if response == "TIMEOUT":
            raise TimeoutError("hosted model timed out")
        return JSONCompletionResult(
            content=response,
            provider="test-provider",
            model="test/model",
            request_id="request_1",
        )


def make_case() -> CaseSnapshot:
    return CaseSnapshot(
        case_id="case_assistant",
        snapshot_id="snapshot_1",
        applicant_ref="applicant_token",
        product=CreditProduct.PERSONAL_LOAN,
        requested_amount=Decimal("5000"),
        content_hash=f"sha256:{'a' * 64}",
        features={"monthly_income": 4000},
        evidence_refs=("document:1",),
    )


def make_reports():
    case = make_case()
    agents = []
    for agent_type, recommendation, score in (
        (CredibilityAgent, Recommendation.APPROVE, 0.12),
        (AffordabilityAgent, Recommendation.REFER, 0.48),
        (CreditRiskAgent, Recommendation.APPROVE, 0.22),
    ):
        agents.append(
            agent_type(
                StaticModelAdapter(
                    model_name=agent_type.agent_id.value,
                    model_version="v1",
                    output=ModelOutput(
                        score=score,
                        calibrated_probability=score,
                        confidence=0.9,
                        recommendation=recommendation,
                        reason_codes=("TEST_REASON",),
                    ),
                )
            )
        )
    return tuple(agent.assess(case) for agent in agents)


def verified_feedback(related_report_id: str) -> FeedbackEvent:
    from datetime import datetime, timezone

    return FeedbackEvent(
        feedback_id="feedback_1",
        case_id="case_assistant",
        source=FeedbackSource.REVIEWER,
        feedback_type=FeedbackType.DATA_CORRECTION,
        rationale="Raw reviewer comment must not enter the hosted model.",
        evidence_refs=("document:1",),
        related_report_ids=(related_report_id,),
        submitter_ref="reviewer_1",
        verification_status=VerificationStatus.VERIFIED,
        verified_by="verifier_1",
        verified_at=datetime.now(timezone.utc),
    )


def test_narrative_is_separate_from_deterministic_manager_result() -> None:
    client = FakeJSONClient(
        [
            json.dumps(
                {
                    "summary": "Specialists disagree on affordability.",
                    "disagreement_explanation": "Affordability is the outlier.",
                    "reviewer_focus": ["Verify income and expenses."],
                    "limitations": ["The hosted model did not decide."],
                }
            )
        ]
    )
    manager = ManagerAgent(
        assistant=StructuredManagerAssistant(client),
        benchmark_context=BenchmarkContext(
            dataset_name="South German Credit",
            dataset_version="UCI-2020",
            metrics={"roc_auc_mean": 0.78},
            limitations=("Historical benchmark only.",),
            report_ref="artifact:benchmark",
        ),
    )

    report = manager.consolidate(make_reports())

    assert report.proposed_action is Recommendation.REFER
    assert report.disagreement is True
    assert report.narrative is not None
    assert report.narrative.assistant_provider == "test-provider"
    assert report.narrative.assistant_model == "test/model"
    assert report.narrative.assistant_request_id == "request_1"
    assert report.assistant_status is ManagerAssistantStatus.COMPLETED
    payload = client.requests[0]["user"]
    assert "applicant_token" not in payload
    assert "Raw reviewer comment" not in payload


def test_malformed_or_timed_out_response_falls_back() -> None:
    for response in ("not-json", "TIMEOUT"):
        manager = ManagerAgent(
            assistant=StructuredManagerAssistant(FakeJSONClient([response]))
        )

        report = manager.consolidate(make_reports())

        assert report.narrative is None
        assert report.assistant_status is ManagerAssistantStatus.FALLBACK
        assert report.proposed_action is Recommendation.REFER


def test_routing_is_validated_and_raw_rationale_is_excluded() -> None:
    reports = make_reports()
    client = FakeJSONClient(
        [
            json.dumps(
                {
                    "feedback_id": "feedback_1",
                    "proposed_targets": [
                        "credibility",
                        "affordability",
                    ],
                    "rationale_codes": ["INCOME_CORRECTION"],
                }
            )
        ]
    )
    manager = ManagerAgent(assistant=StructuredManagerAssistant(client))
    feedback = verified_feedback(reports[1].report_id)

    routed = manager.route_feedback(
        feedback=feedback,
        previous_reports=reports,
        revised_case=make_case(),
    )

    assert set(routed.selected_targets) == {
        AgentId.CREDIBILITY,
        AgentId.AFFORDABILITY,
    }
    assert "Raw reviewer comment" not in client.requests[0]["user"]


def test_unauthorized_target_uses_deterministic_fallback() -> None:
    reports = make_reports()
    client = FakeJSONClient(
        [
            json.dumps(
                {
                    "feedback_id": "feedback_1",
                    "proposed_targets": ["credit_risk"],
                    "rationale_codes": ["UNAUTHORIZED"],
                }
            )
        ]
    )
    manager = ManagerAgent(assistant=StructuredManagerAssistant(client))
    feedback = verified_feedback(reports[1].report_id)

    routed = manager.route_feedback(
        feedback=feedback,
        previous_reports=reports,
        revised_case=make_case(),
    )

    assert set(routed.selected_targets) == {
        AgentId.CREDIBILITY,
        AgentId.AFFORDABILITY,
    }
