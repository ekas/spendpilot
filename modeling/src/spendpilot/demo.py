"""Runnable end-to-end demo assembled from the governed components."""

from __future__ import annotations

from pathlib import Path

from spendpilot.agents import (
    AffordabilityAgent,
    CredibilityAgent,
    CreditRiskAgent,
    ManagerAgent,
)
from spendpilot.assistants.contracts import ManagerAssistant
from spendpilot.benchmark import load_benchmark_context
from spendpilot.ingestion import BackendApplicant, BackendInputAdapter
from spendpilot.models import (
    CredibilityRulesAdapter,
    MonotonicXGBoostAdapter,
)
from spendpilot.orchestration import (
    DecisionWorkflow,
    HumanReviewQueue,
    PolicyEngine,
    WorkflowResult,
)
from spendpilot.schemas import AgentId, BenchmarkContext


SAMPLE_APPLICANTS = (
    BackendApplicant(
        name="Amina Lowrisk",
        monthly_income=4200,
        monthly_expenses=2100,
        requested_amount=6000,
        existing_debt=800,
        credit_utilization=0.22,
        delinquencies_12m=0,
        employment_months=28,
        overdrafts_90d=0,
        income_verified=True,
        documents=(
            "id_document.pdf",
            "bank_statement_jan.pdf",
            "income_proof.pdf",
        ),
    ),
    BackendApplicant(
        name="Ben Borderline",
        monthly_income=3100,
        monthly_expenses=2450,
        requested_amount=12000,
        existing_debt=7200,
        credit_utilization=0.68,
        delinquencies_12m=0,
        employment_months=9,
        overdrafts_90d=2,
        income_verified=True,
        documents=(
            "id_document.pdf",
            "bank_statement_jan.pdf",
            "income_proof.pdf",
        ),
    ),
    BackendApplicant(
        name="Clara Adverse",
        monthly_income=2400,
        monthly_expenses=2300,
        requested_amount=18000,
        existing_debt=13000,
        credit_utilization=0.91,
        delinquencies_12m=2,
        employment_months=4,
        overdrafts_90d=4,
        income_verified=False,
        documents=("id_document.pdf",),
    ),
)


def build_demo_workflow(
    artifact_root: Path | str,
    *,
    assistant: ManagerAssistant | None = None,
    benchmark_context: BenchmarkContext | None = None,
) -> DecisionWorkflow:
    """Build the production-shaped workflow from local demo artifacts."""

    root = Path(artifact_root)
    specialists = (
        CredibilityAgent(CredibilityRulesAdapter()),
        AffordabilityAgent(
            MonotonicXGBoostAdapter(
                root / AgentId.AFFORDABILITY.value,
                AgentId.AFFORDABILITY,
            )
        ),
        CreditRiskAgent(
            MonotonicXGBoostAdapter(
                root / AgentId.CREDIT_RISK.value,
                AgentId.CREDIT_RISK,
            )
        ),
    )
    return DecisionWorkflow(
        specialists=specialists,
        manager=ManagerAgent(
            assistant=assistant,
            benchmark_context=benchmark_context,
        ),
        policy_engine=PolicyEngine(),
        review_queue=HumanReviewQueue(),
    )


def run_sample_cases(
    artifact_root: Path | str,
    *,
    assistant: ManagerAssistant | None = None,
    benchmark_report_path: Path | str | None = None,
) -> tuple[WorkflowResult, ...]:
    """Run the three backend examples without retaining their names."""

    benchmark_context = None
    if benchmark_report_path is not None:
        report_path = Path(benchmark_report_path)
        if report_path.exists():
            benchmark_context = load_benchmark_context(report_path)
    workflow = build_demo_workflow(
        artifact_root,
        assistant=assistant,
        benchmark_context=benchmark_context,
    )
    adapter = BackendInputAdapter()
    results = []
    for index, applicant in enumerate(SAMPLE_APPLICANTS, start=1):
        snapshot = adapter.to_snapshot(
            applicant,
            case_id=f"demo_case_{index}",
            snapshot_id="snapshot_1",
            applicant_ref=f"demo_applicant_{index}",
        )
        results.append(workflow.run(snapshot))
    return tuple(results)
