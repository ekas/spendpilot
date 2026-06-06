import json

import httpx

from spendpilot.agents import ManagerAssistantStatus
from spendpilot.assistants.local_llama import LlamaCppJSONClient
from spendpilot.assistants.structured import (
    JSONCompletionResult,
    StructuredManagerAssistant,
)
from spendpilot.cli import main
from spendpilot.demo import run_sample_cases
from spendpilot.schemas import AgentId, DecisionAction
from spendpilot.training import (
    SyntheticTrainingConfig,
    train_synthetic_models,
)


class NarrativeClient:
    def complete_json(self, **kwargs) -> JSONCompletionResult:
        del kwargs
        return JSONCompletionResult(
            content=json.dumps(
                {
                    "summary": "Reports were summarized for human review.",
                    "disagreement_explanation": "Recommendations are preserved.",
                    "reviewer_focus": ["Review principal reason codes."],
                    "limitations": [
                        "The hosted model has no decision authority."
                    ],
                }
            ),
            provider="test-provider",
            model="test/model",
            request_id="request_demo",
        )


def test_three_backend_samples_run_through_real_specialists(tmp_path) -> None:
    artifact_root = tmp_path / "models"
    train_synthetic_models(
        artifact_root,
        SyntheticTrainingConfig(
            sample_count=2_000,
            n_estimators=50,
            seed=2026,
        ),
    )

    results = run_sample_cases(artifact_root)

    assert len(results) == 3
    for result in results:
        assert {report.agent_id for report in result.reports} == set(AgentId)
        assert all(report.top_contributors for report in result.reports)
        assert result.decision.action in set(DecisionAction)
        assert tuple(result.manager_report.reports) == result.reports
    assert results[0].decision.action is DecisionAction.APPROVE
    assert results[0].decision.finalized is True
    assert results[2].review_task is not None
    assert results[2].decision.finalized is False


def test_hosted_narrative_cannot_change_policy_result(tmp_path) -> None:
    artifact_root = tmp_path / "models"
    train_synthetic_models(
        artifact_root,
        SyntheticTrainingConfig(
            sample_count=1_500,
            n_estimators=40,
            seed=99,
        ),
    )

    baseline = run_sample_cases(artifact_root)
    assisted = run_sample_cases(
        artifact_root,
        assistant=StructuredManagerAssistant(NarrativeClient()),
    )

    assert [result.decision.action for result in assisted] == [
        result.decision.action for result in baseline
    ]
    assert [result.decision.finalized for result in assisted] == [
        result.decision.finalized for result in baseline
    ]
    assert all(
        result.manager_report.assistant_status
        is ManagerAssistantStatus.COMPLETED
        for result in assisted
    )


def test_local_llama_narrative_cannot_change_reports_or_policy(
    tmp_path,
) -> None:
    artifact_root = tmp_path / "local-models"
    train_synthetic_models(
        artifact_root,
        SyntheticTrainingConfig(
            sample_count=700,
            n_estimators=20,
            seed=20260606,
        ),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "content": json.dumps(
                    {
                        "summary": "Review the deterministic reports.",
                        "disagreement_explanation": (
                            "Recommendations remain unchanged."
                        ),
                        "reviewer_focus": ["Review reason codes."],
                        "limitations": ["No decision authority."],
                    }
                ),
                "model": "phi-1.5-local",
            },
        )

    assistant = StructuredManagerAssistant(
        LlamaCppJSONClient(
            client=httpx.Client(transport=httpx.MockTransport(handler))
        )
    )
    baseline = run_sample_cases(artifact_root)
    assisted = run_sample_cases(artifact_root, assistant=assistant)

    def report_values(results):
        return [
            [
                (
                    report.agent_id,
                    report.score,
                    report.recommendation,
                    report.reason_codes,
                    report.top_contributors,
                )
                for report in result.reports
            ]
            for result in results
        ]

    assert report_values(assisted) == report_values(baseline)
    assert [result.decision.action for result in assisted] == [
        result.decision.action for result in baseline
    ]
    assert [result.decision.finalized for result in assisted] == [
        result.decision.finalized for result in baseline
    ]


def test_cli_can_train_reduced_artifacts(tmp_path, capsys) -> None:
    output = tmp_path / "cli-models"

    exit_code = main(
        [
            "train-synthetic",
            "--output",
            str(output),
            "--sample-count",
            "600",
            "--n-estimators",
            "20",
        ]
    )

    assert exit_code == 0
    assert (output / "affordability" / "model.json").exists()
    assert (output / "credit_risk" / "model.json").exists()
    assert "synthetic-20260606-v1" in capsys.readouterr().out


def test_cli_evaluates_an_external_json_case(tmp_path, capsys) -> None:
    artifact_root = tmp_path / "external-models"
    train_synthetic_models(
        artifact_root,
        SyntheticTrainingConfig(
            sample_count=700,
            n_estimators=20,
            seed=20260606,
        ),
    )
    input_path = tmp_path / "external.json"
    input_path.write_text(
        json.dumps(
            {
                "case_id": "external_case_1",
                "applicant_ref": "external_customer_1",
                "applicant": {
                    "name": "Sensitive Name",
                    "monthly_income": 3800,
                    "monthly_expenses": 2100,
                    "requested_amount": 7500,
                    "existing_debt": 1600,
                    "credit_utilization": 0.34,
                    "delinquencies_12m": 0,
                    "employment_months": 22,
                    "overdrafts_90d": 1,
                    "income_verified": True,
                    "documents": [
                        "id_document.pdf",
                        "bank_statement.pdf",
                        "income_proof.pdf",
                    ],
                    "document_text": "Sensitive Name private content.",
                },
            }
        )
    )

    exit_code = main(
        [
            "evaluate-input",
            "--input",
            str(input_path),
            "--model-root",
            str(artifact_root),
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "external_case_1" in output
    assert "Sensitive Name" not in output
    assert "private content" not in output

    report_path = tmp_path / "external-report.html"
    exit_code = main(
        [
            "explainability-report",
            "--input",
            str(input_path),
            "--model-root",
            str(artifact_root),
            "--output",
            str(report_path),
        ]
    )

    report = report_path.read_text()
    assert exit_code == 0
    assert "external_case_1" in report
    assert "Inputs accepted from outside the demo" in report
    assert "Sensitive Name" not in report
    assert "private content" not in report
