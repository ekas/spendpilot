"""Reproducible South German Credit research benchmark."""

from __future__ import annotations

import hashlib
import json
import urllib.request
import zipfile
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from spendpilot.schemas.modeling import BenchmarkContext


DATASET_URL = (
    "https://archive.ics.uci.edu/static/public/573/"
    "south+german+credit+update.zip"
)
DATASET_SHA256 = (
    "0b40d40eb7321693d559e247a556f88a6cc8df8489c3cb2ae084db7592584551"
)
DATASET_VERSION = "UCI-2020"
RAW_FILENAME = "SouthGermanCredit.asc"
EXCLUDED_FEATURES = ("age", "foreign_worker", "personal_status_sex")

ORIGINAL_COLUMNS = (
    "laufkont",
    "laufzeit",
    "moral",
    "verw",
    "hoehe",
    "sparkont",
    "beszeit",
    "rate",
    "famges",
    "buerge",
    "wohnzeit",
    "verm",
    "alter",
    "weitkred",
    "wohn",
    "bishkred",
    "beruf",
    "pers",
    "telef",
    "gastarb",
    "kredit",
)
RENAMED_COLUMNS = (
    "status",
    "duration",
    "credit_history",
    "purpose",
    "amount",
    "savings",
    "employment_duration",
    "installment_rate",
    "personal_status_sex",
    "other_debtors",
    "present_residence",
    "property",
    "age",
    "other_installment_plans",
    "housing",
    "number_credits",
    "job",
    "people_liable",
    "telephone",
    "foreign_worker",
    "credit_risk",
)
NUMERIC_FEATURES = ("duration", "amount")
CATEGORICAL_FEATURES = tuple(
    feature
    for feature in RENAMED_COLUMNS[:-1]
    if feature not in NUMERIC_FEATURES and feature not in EXCLUDED_FEATURES
)


class BenchmarkConfig(BaseModel):
    """Evaluation settings for the small 1,000-row historical dataset."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    random_seed: int = 20_260_606
    folds: int = Field(default=5, ge=2)
    repeats: int = Field(default=3, ge=1)
    xgboost_estimators: int = Field(default=100, ge=10)


def download_south_german_credit(destination: Path | str) -> Path:
    """Download, checksum, and extract the official UCI data file."""

    destination_path = Path(destination)
    destination_path.mkdir(parents=True, exist_ok=True)
    archive_path = destination_path / "south_german_credit.zip"
    urllib.request.urlretrieve(DATASET_URL, archive_path)
    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    if digest != DATASET_SHA256:
        archive_path.unlink(missing_ok=True)
        raise ValueError("South German Credit archive checksum mismatch")

    with zipfile.ZipFile(archive_path) as archive:
        member = archive.getinfo(RAW_FILENAME)
        target_path = destination_path / RAW_FILENAME
        target_path.write_bytes(archive.read(member))
    return target_path


def load_south_german_credit(path: Path | str):
    """Load corrected UCI data and normalize ``bad_credit=1``."""

    import pandas as pd

    frame = pd.read_csv(path, sep=r"\s+")
    if tuple(frame.columns) != ORIGINAL_COLUMNS:
        raise ValueError("unexpected South German Credit column layout")
    frame.columns = RENAMED_COLUMNS
    if set(frame["credit_risk"].unique()) != {0, 1}:
        raise ValueError("unexpected South German Credit target coding")

    audit_slices = frame.loc[:, list(EXCLUDED_FEATURES)].copy()
    target = (frame.pop("credit_risk") == 0).astype(int).rename("bad_credit")
    features = frame.drop(columns=list(EXCLUDED_FEATURES))
    return features, target, audit_slices


def run_south_german_benchmark(
    data_path: Path | str,
    report_path: Path | str,
    config: BenchmarkConfig | None = None,
) -> BenchmarkContext:
    """Evaluate two research models without creating a scoring adapter."""

    import numpy as np
    import xgboost as xgb
    from sklearn.compose import ColumnTransformer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import (
        average_precision_score,
        brier_score_loss,
        roc_auc_score,
    )
    from sklearn.model_selection import RepeatedStratifiedKFold
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    from xgboost import XGBClassifier

    settings = config or BenchmarkConfig()
    features, target, _ = load_south_german_credit(data_path)
    splitter = RepeatedStratifiedKFold(
        n_splits=settings.folds,
        n_repeats=settings.repeats,
        random_state=settings.random_seed,
    )

    def preprocessor() -> ColumnTransformer:
        return ColumnTransformer(
            (
                ("numeric", StandardScaler(), list(NUMERIC_FEATURES)),
                (
                    "categorical",
                    OneHotEncoder(handle_unknown="ignore"),
                    list(CATEGORICAL_FEATURES),
                ),
            )
        )

    models = {
        "logistic_regression": lambda: Pipeline(
            (
                ("preprocessor", preprocessor()),
                (
                    "model",
                    LogisticRegression(
                        max_iter=1_000,
                        random_state=settings.random_seed,
                    ),
                ),
            )
        ),
        "xgboost": lambda: Pipeline(
            (
                ("preprocessor", preprocessor()),
                (
                    "model",
                    XGBClassifier(
                        n_estimators=settings.xgboost_estimators,
                        max_depth=3,
                        learning_rate=0.05,
                        subsample=0.9,
                        colsample_bytree=0.9,
                        objective="binary:logistic",
                        eval_metric="logloss",
                        tree_method="hist",
                        random_state=settings.random_seed,
                        n_jobs=2,
                    ),
                ),
            )
        ),
    }
    model_metrics: dict[str, dict[str, float]] = {}
    for model_name, factory in models.items():
        fold_values = {
            "roc_auc": [],
            "pr_auc": [],
            "brier_score": [],
            "expected_calibration_error": [],
        }
        for train_index, test_index in splitter.split(features, target):
            model = factory()
            model.fit(features.iloc[train_index], target.iloc[train_index])
            probability = model.predict_proba(features.iloc[test_index])[:, 1]
            expected = target.iloc[test_index].to_numpy()
            fold_values["roc_auc"].append(
                roc_auc_score(expected, probability)
            )
            fold_values["pr_auc"].append(
                average_precision_score(expected, probability)
            )
            fold_values["brier_score"].append(
                brier_score_loss(expected, probability)
            )
            fold_values["expected_calibration_error"].append(
                _expected_calibration_error(expected, probability)
            )
        model_metrics[model_name] = {
            f"{metric}_{summary}": float(
                np.mean(values) if summary == "mean" else np.std(values)
            )
            for metric, values in fold_values.items()
            for summary in ("mean", "std")
        }

    final_xgboost = models["xgboost"]()
    final_xgboost.fit(features, target)
    transformed = final_xgboost.named_steps["preprocessor"].transform(features)
    feature_names = final_xgboost.named_steps[
        "preprocessor"
    ].get_feature_names_out()
    booster = final_xgboost.named_steps["model"].get_booster()
    contribution_matrix = booster.predict(
        xgb.DMatrix(transformed, feature_names=list(feature_names)),
        pred_contribs=True,
    )[:, :-1]
    mean_absolute_contribution = np.abs(contribution_matrix).mean(axis=0)
    top_shap = [
        {
            "feature": str(feature_names[index]),
            "mean_absolute_contribution": float(
                mean_absolute_contribution[index]
            ),
        }
        for index in np.argsort(mean_absolute_contribution)[::-1][:10]
    ]

    report = {
        "dataset": {
            "name": "South German Credit",
            "version": DATASET_VERSION,
            "source": DATASET_URL,
            "license": "CC BY 4.0",
            "sha256": hashlib.sha256(Path(data_path).read_bytes()).hexdigest(),
            "rows": len(features),
            "bad_credit_rate": float(target.mean()),
        },
        "evaluation": {
            "folds": settings.folds,
            "repeats": settings.repeats,
            "random_seed": settings.random_seed,
            "models": model_metrics,
        },
        "excluded_features": EXCLUDED_FEATURES,
        "xgboost_top_shap": top_shap,
        "limitations": _limitations(),
    }
    output = Path(report_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    xgb_metrics = model_metrics["xgboost"]
    return BenchmarkContext(
        dataset_name="South German Credit",
        dataset_version=DATASET_VERSION,
        metrics={
            "roc_auc_mean": xgb_metrics["roc_auc_mean"],
            "roc_auc_std": xgb_metrics["roc_auc_std"],
            "pr_auc_mean": xgb_metrics["pr_auc_mean"],
            "brier_score_mean": xgb_metrics["brier_score_mean"],
            "expected_calibration_error_mean": xgb_metrics[
                "expected_calibration_error_mean"
            ],
        },
        excluded_features=EXCLUDED_FEATURES,
        limitations=_limitations(),
        report_ref=str(output),
    )


def load_benchmark_context(report_path: Path | str) -> BenchmarkContext:
    """Load only approved aggregate benchmark fields for manager context."""

    path = Path(report_path)
    report = json.loads(path.read_text())
    metrics = report["evaluation"]["models"]["xgboost"]
    return BenchmarkContext(
        dataset_name=report["dataset"]["name"],
        dataset_version=report["dataset"]["version"],
        metrics={
            "roc_auc_mean": metrics["roc_auc_mean"],
            "roc_auc_std": metrics["roc_auc_std"],
            "pr_auc_mean": metrics["pr_auc_mean"],
            "brier_score_mean": metrics["brier_score_mean"],
            "expected_calibration_error_mean": metrics[
                "expected_calibration_error_mean"
            ],
        },
        excluded_features=tuple(report["excluded_features"]),
        limitations=tuple(report["limitations"]),
        report_ref=str(path),
    )


def _expected_calibration_error(expected, probability, bins: int = 10) -> float:
    import numpy as np

    boundaries = np.linspace(0.0, 1.0, bins + 1)
    assignments = np.digitize(probability, boundaries[1:-1])
    error = 0.0
    for bin_index in range(bins):
        selected = assignments == bin_index
        if not selected.any():
            continue
        error += selected.mean() * abs(
            expected[selected].mean() - probability[selected].mean()
        )
    return float(error)


def _limitations() -> tuple[str, ...]:
    return (
        "Historical German credit data collected from 1973 to 1975.",
        "Bad credits were intentionally oversampled.",
        "The amount field is transformed and its original scale is unknown.",
        "Features do not match SpendPilot backend inputs.",
        "Benchmark metrics must not be used as an applicant-level score.",
    )
