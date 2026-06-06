from decimal import Decimal

import pytest

from spendpilot.models import (
    CredibilityRulesAdapter,
    MonotonicXGBoostAdapter,
)
from spendpilot.schemas import AgentId, CaseSnapshot, CreditProduct
from spendpilot.training import SyntheticTrainingConfig, train_synthetic_models


def make_case(
    *,
    case_id: str,
    income: float,
    expenses: float,
    requested: float,
    debt: float,
    utilization: float,
    delinquencies: int,
    employment_months: int,
    overdrafts: int,
    verified: bool,
    missing_fields: tuple[str, ...] = (),
) -> CaseSnapshot:
    return CaseSnapshot(
        case_id=case_id,
        snapshot_id="snapshot_1",
        applicant_ref=f"applicant_{case_id}",
        product=CreditProduct.PERSONAL_LOAN,
        requested_amount=Decimal(str(requested)),
        currency="EUR",
        content_hash=f"sha256:{'a' * 64}",
        features={
            "monthly_income": income,
            "monthly_expenses": expenses,
            "existing_debt": debt,
            "credit_utilization": utilization,
            "delinquencies_12m": delinquencies,
            "employment_months": employment_months,
            "overdrafts_90d": overdrafts,
            "income_verified": verified,
            "document_count": 3,
            "document_coverage_score": 0.8,
            "document_consistency_flag_count": 0,
        },
        evidence_refs=("document:1", "document:2"),
        missing_fields=missing_fields,
    )


@pytest.fixture(scope="module")
def trained_artifacts(tmp_path_factory):
    root = tmp_path_factory.mktemp("synthetic-models")
    manifests = train_synthetic_models(
        root,
        SyntheticTrainingConfig(
            sample_count=1_200,
            n_estimators=45,
            seed=1234,
        ),
    )
    return root, manifests


def test_credibility_rules_are_explicit_and_adverse_risk_oriented() -> None:
    low = make_case(
        case_id="low",
        income=4200,
        expenses=2100,
        requested=6000,
        debt=800,
        utilization=0.22,
        delinquencies=0,
        employment_months=28,
        overdrafts=0,
        verified=True,
    )
    high = low.model_copy(
        update={
            "case_id": "high",
            "missing_fields": ("bank_statement", "income_proof"),
            "features": {
                **low.features,
                "income_verified": False,
                "document_consistency_flag_count": 2,
            },
        }
    )
    adapter = CredibilityRulesAdapter()

    low_output = adapter.predict(low)
    high_output = adapter.predict(high)

    assert low_output.score < high_output.score
    assert low_output.reason_codes == ("EVIDENCE_COMPLETE",)
    assert "MISSING_DOCUMENTS" in high_output.reason_codes
    assert "DOCUMENT_INCONSISTENCY" in high_output.reason_codes


def test_synthetic_training_writes_native_json_artifacts(
    trained_artifacts,
) -> None:
    root, manifests = trained_artifacts

    assert {manifest.agent_id for manifest in manifests} == {
        AgentId.AFFORDABILITY,
        AgentId.CREDIT_RISK,
    }
    for manifest in manifests:
        artifact_dir = root / manifest.agent_id.value
        assert (artifact_dir / "model.json").exists()
        assert (artifact_dir / "calibration.json").exists()
        assert (artifact_dir / "validation.json").exists()
        assert not tuple(artifact_dir.glob("*.pkl"))
        assert not tuple(artifact_dir.glob("*.joblib"))


def test_trained_adapters_score_adverse_case_higher(
    trained_artifacts,
) -> None:
    root, _ = trained_artifacts
    low = make_case(
        case_id="low",
        income=4200,
        expenses=2100,
        requested=6000,
        debt=800,
        utilization=0.22,
        delinquencies=0,
        employment_months=28,
        overdrafts=0,
        verified=True,
    )
    high = make_case(
        case_id="high",
        income=2400,
        expenses=2300,
        requested=18000,
        debt=13000,
        utilization=0.91,
        delinquencies=2,
        employment_months=4,
        overdrafts=4,
        verified=False,
    )

    for agent_id in (AgentId.AFFORDABILITY, AgentId.CREDIT_RISK):
        adapter = MonotonicXGBoostAdapter(root / agent_id.value, agent_id)
        low_output = adapter.predict(low)
        high_output = adapter.predict(high)

        assert 0 <= low_output.score <= 1
        assert low_output.score < high_output.score
        assert high_output.top_contributors
        assert high_output.monotonicity_checks.value == "passed"
