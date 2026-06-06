import json

from spendpilot.agents import ManagerAssistantStatus
from spendpilot.assistants.phi import PhiManagerAssistant
from spendpilot.cli import main
from spendpilot.demo import run_sample_cases
from spendpilot.schemas import AgentId, DecisionAction
from spendpilot.training import (
    SyntheticTrainingConfig,
    train_synthetic_models,
)


class NarrativeClient:
    def complete_json(self, **kwargs) -> str:
        del kwargs
        return json.dumps(
            {
                "summary": "Reports were summarized for human review.",
                "disagreement_explanation": "Recommendations are preserved.",
                "reviewer_focus": ["Review principal reason codes."],
                "limitations": ["Phi has no decision authority."],
            }
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


def test_phi_narrative_cannot_change_policy_result(tmp_path) -> None:
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
        assistant=PhiManagerAssistant(NarrativeClient()),
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
