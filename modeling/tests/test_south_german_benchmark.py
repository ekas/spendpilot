from pathlib import Path

import pytest

from spendpilot.benchmark import (
    BenchmarkConfig,
    load_south_german_credit,
    run_south_german_benchmark,
)


FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "south_german_credit_sample.asc"
)


def test_loader_normalizes_target_and_excludes_protected_fields() -> None:
    features, target, audit_slices = load_south_german_credit(FIXTURE)

    assert target.name == "bad_credit"
    assert set(target.unique()) == {0, 1}
    assert target.iloc[0] == 0
    assert target.iloc[6] == 1
    assert {"age", "foreign_worker", "personal_status_sex"}.isdisjoint(
        features.columns
    )
    assert set(audit_slices.columns) == {
        "age",
        "foreign_worker",
        "personal_status_sex",
    }


@pytest.mark.filterwarnings("ignore:.*least populated class.*")
def test_benchmark_produces_reproducible_context(tmp_path) -> None:
    report_path = tmp_path / "benchmark.json"

    context = run_south_german_benchmark(
        FIXTURE,
        report_path,
        BenchmarkConfig(
            random_seed=7,
            folds=2,
            repeats=1,
            xgboost_estimators=10,
        ),
    )

    assert context.dataset_name == "South German Credit"
    assert 0 <= context.metrics["roc_auc_mean"] <= 1
    assert "age" in context.excluded_features
    assert report_path.exists()
    assert any(
        "must not be used" in limitation
        for limitation in context.limitations
    )
