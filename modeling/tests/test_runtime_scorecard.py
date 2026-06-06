from spendpilot.demo import build_runtime_workflow
from spendpilot.ingestion import BackendApplicant, BackendInputAdapter


def _snapshot(*, utilization: float, delinquencies: int):
    applicant = BackendApplicant(
        name="Private Applicant",
        monthly_income=4000,
        monthly_expenses=2200,
        requested_amount=6000,
        existing_debt=1200,
        credit_utilization=utilization,
        delinquencies_12m=delinquencies,
        employment_months=24,
        income_verified=True,
        documents=(
            "id_document.pdf",
            "bank_statement.pdf",
            "income_proof.pdf",
        ),
    )
    return BackendInputAdapter().to_snapshot(
        applicant,
        case_id=f"case_{utilization}_{delinquencies}",
        snapshot_id="snapshot_1",
    )


def test_runtime_uses_transparent_scorecards_without_artifacts(tmp_path) -> None:
    workflow, source = build_runtime_workflow(tmp_path)

    result = workflow.run(_snapshot(utilization=0.2, delinquencies=0))

    assert source == "transparent_scorecard_fallback"
    assert len(result.reports) == 3
    assert result.decision.policy_version == "consumer-credit-v1"


def test_credit_scorecard_risk_increases_for_adverse_profile(tmp_path) -> None:
    workflow, _ = build_runtime_workflow(tmp_path)

    low_risk = workflow.run(_snapshot(utilization=0.2, delinquencies=0))
    high_risk = workflow.run(_snapshot(utilization=0.9, delinquencies=3))
    low_credit = next(
        report for report in low_risk.reports if report.agent_id == "credit_risk"
    )
    high_credit = next(
        report for report in high_risk.reports if report.agent_id == "credit_risk"
    )

    assert high_credit.score > low_credit.score
