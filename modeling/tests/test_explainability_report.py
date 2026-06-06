import json
from datetime import datetime, timezone

from spendpilot.reports import (
    contribution_direction,
    generate_explainability_report,
)
from spendpilot.schemas import (
    LocalLLMProbe,
    LocalLLMProbePurpose,
    LocalLLMSmokeReport,
    ManagerNarrative,
)
from spendpilot.training import (
    SyntheticTrainingConfig,
    train_synthetic_models,
)


def test_contribution_direction_uses_adverse_risk_sign() -> None:
    assert contribution_direction(0.2) == "increases risk"
    assert contribution_direction(-0.2) == "protective"
    assert contribution_direction(0.0) == "neutral"


def test_report_contains_cases_explanations_and_no_pii(tmp_path) -> None:
    model_root = tmp_path / "models"
    train_synthetic_models(
        model_root,
        SyntheticTrainingConfig(
            sample_count=700,
            n_estimators=20,
            seed=20260606,
        ),
    )
    benchmark_path = tmp_path / "benchmark.json"
    benchmark_path.write_text(
        json.dumps(
            {
                "dataset": {
                    "name": "South German Credit",
                    "version": "UCI-2020",
                },
                "evaluation": {
                    "models": {
                        "xgboost": {
                            "roc_auc_mean": 0.78,
                            "roc_auc_std": 0.02,
                            "pr_auc_mean": 0.62,
                            "brier_score_mean": 0.16,
                            "expected_calibration_error_mean": 0.06,
                        }
                    }
                },
                "excluded_features": [
                    "age",
                    "foreign_worker",
                    "personal_status_sex",
                ],
                "limitations": ["Historical benchmark only."],
                "xgboost_top_shap": [
                    {
                        "feature": "numeric__duration",
                        "mean_absolute_contribution": 0.3,
                    }
                ],
            }
        )
    )
    smoke_path = tmp_path / "smoke.json"
    smoke_path.write_text(
        LocalLLMSmokeReport(
            model_name="phi-1.5-local",
            model_file="phi-1.5.Q4_K_M.gguf",
            model_path_hash=f"sha256:{'b' * 64}",
            artifact_hash=f"sha256:{'a' * 64}",
            llama_cpp_version="llama.cpp b9430",
            endpoint="http://127.0.0.1:8080",
            context_size=2048,
            max_output_tokens=256,
            started_at=datetime.now(timezone.utc),
            probes=(
                LocalLLMProbe(
                    purpose=LocalLLMProbePurpose.NARRATIVE,
                    case_id="demo_case_1",
                    success=True,
                    schema_valid=True,
                    latency_ms=42,
                    narrative=ManagerNarrative(
                        summary="All specialists report lower risk.",
                        disagreement_explanation="No disagreement.",
                        assistant_provider="llama.cpp",
                        assistant_model="phi-1.5-local",
                        assistant_latency_ms=42,
                    ),
                ),
            ),
            success_rate=1.0,
            recommendation="Experimental only.",
        ).model_dump_json()
    )
    output = tmp_path / "explainability.html"

    generate_explainability_report(
        model_root=model_root,
        benchmark_report_path=benchmark_path,
        smoke_report_path=smoke_path,
        output_path=output,
    )

    report = output.read_text()
    assert all(f"demo_case_{index}" in report for index in range(1, 4))
    assert "Key factors behind this score" in report
    assert "data-direction=\"increases risk\"" in report
    assert "data-direction=\"protective\"" in report
    assert "South German Credit" in report
    assert "Duration" in report
    assert "Path SHA-256" in report
    assert "Specialist disagreement" in report
    assert "Human review" in report
    assert "Input to decision workflow" in report
    assert "Parallel specialist agents" in report
    assert "Manager agent" in report
    assert "Policy engine" in report
    assert "Governed output" in report
    assert 'role="tablist"' in report
    assert 'class="case-tab"' in report
    assert 'class="agent-node"' in report
    assert 'class="contribution-row"' in report
    assert "selectCase" in report
    assert "Inputs accepted from outside the demo" in report
    assert "Existing debt compared with monthly income" in report
    assert "Supporting documents" in report
    assert "This factor lowers risk" in report
    assert "Outstanding debt is lower relative to monthly income" in report
    assert "HIGH_DTI" not in report
    assert "debt_to_income" not in report
    assert "document:" not in report
    assert "<script" in report
    assert "<link" not in report
    assert "src=\"http" not in report
    assert "href=\"http" not in report
    for forbidden in (
        "Amina Lowrisk",
        "Ben Borderline",
        "Clara Adverse",
        "id_document.pdf",
        "bank_statement_jan.pdf",
        "OPENROUTER_API_KEY",
    ):
        assert forbidden not in report
