"""Synthetic training pipeline for backend-compatible specialist models."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from spendpilot.models.features import (
    AFFORDABILITY_FEATURES,
    CREDIT_RISK_FEATURES,
)
from spendpilot.schemas.agent_report import AgentId
from spendpilot.schemas.modeling import (
    ModelArtifactManifest,
    ModelProvenance,
)


class SyntheticTrainingConfig(BaseModel):
    """Configuration committed alongside reproducible training code."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sample_count: int = Field(default=25_000, ge=500)
    seed: int = 20_260_606
    test_fraction: float = Field(default=0.20, gt=0, lt=0.5)
    validation_fraction: float = Field(default=0.20, gt=0, lt=0.5)
    noise_standard_deviation: float = Field(default=0.35, ge=0, le=1)
    n_estimators: int = Field(default=140, ge=20)
    max_depth: int = Field(default=3, ge=1, le=6)
    learning_rate: float = Field(default=0.05, gt=0, le=0.3)


def train_synthetic_models(
    output_root: Path | str,
    config: SyntheticTrainingConfig | None = None,
) -> tuple[ModelArtifactManifest, ...]:
    """Train both monotonic specialists and write native JSON artifacts."""

    import numpy as np

    settings = config or SyntheticTrainingConfig()
    rng = np.random.default_rng(settings.seed)
    population = _generate_population(rng, settings.sample_count)
    manifests = []
    for offset, agent_id in enumerate(
        (AgentId.AFFORDABILITY, AgentId.CREDIT_RISK)
    ):
        features, labels = _training_matrix(
            population,
            agent_id,
            rng=np.random.default_rng(settings.seed + offset + 1),
            noise_standard_deviation=settings.noise_standard_deviation,
        )
        manifests.append(
            _train_one(
                output_root=Path(output_root),
                agent_id=agent_id,
                features=features,
                labels=labels,
                config=settings,
            )
        )
    return tuple(manifests)


def _generate_population(rng, sample_count: int) -> dict[str, object]:
    import numpy as np

    income = np.clip(rng.lognormal(mean=8.15, sigma=0.48, size=sample_count), 900, 15_000)
    expense_ratio = rng.uniform(0.35, 1.05, sample_count)
    expenses = income * expense_ratio
    debt = np.clip(rng.gamma(shape=1.8, scale=3_200, size=sample_count), 0, 40_000)
    requested = np.clip(
        rng.lognormal(mean=8.9, sigma=0.65, size=sample_count),
        500,
        35_000,
    )
    return {
        "income": income,
        "expenses": expenses,
        "debt": debt,
        "requested": requested,
        "utilization": np.clip(rng.beta(2.0, 2.8, sample_count), 0, 1),
        "delinquencies": np.clip(rng.poisson(0.45, sample_count), 0, 5),
        "employment_months": np.clip(
            rng.gamma(shape=2.2, scale=15.0, size=sample_count),
            0,
            180,
        ),
        "overdrafts": np.clip(rng.poisson(0.8, sample_count), 0, 6),
        "income_unverified": rng.binomial(1, 0.24, sample_count),
    }


def _training_matrix(
    population: dict[str, object],
    agent_id: AgentId,
    *,
    rng,
    noise_standard_deviation: float,
):
    import numpy as np

    income = population["income"]
    expenses = population["expenses"]
    debt = population["debt"]
    overdrafts = population["overdrafts"]
    if agent_id is AgentId.AFFORDABILITY:
        free_cash_flow = np.maximum(income - expenses, 1)
        matrix = np.column_stack(
            (
                debt / income,
                (population["requested"] / 36.0) / free_cash_flow,
                expenses / income,
                overdrafts,
                population["income_unverified"],
            )
        )
        logit = (
            -3.6
            + 0.95 * np.minimum(matrix[:, 0], 3.0)
            + 0.75 * np.minimum(matrix[:, 1], 4.0)
            + 1.35 * matrix[:, 2]
            + 0.18 * matrix[:, 3]
            + 0.55 * matrix[:, 4]
        )
    else:
        matrix = np.column_stack(
            (
                population["utilization"],
                population["delinquencies"],
                np.maximum(12.0 - population["employment_months"], 0),
                debt / (income * 12.0),
                overdrafts,
            )
        )
        logit = (
            -3.3
            + 2.1 * matrix[:, 0]
            + 0.72 * matrix[:, 1]
            + 0.055 * matrix[:, 2]
            + 1.2 * np.minimum(matrix[:, 3], 1.5)
            + 0.14 * matrix[:, 4]
        )
    noisy_logit = logit + rng.normal(
        0.0,
        noise_standard_deviation,
        len(matrix),
    )
    probability = 1.0 / (1.0 + np.exp(-noisy_logit))
    return matrix, rng.binomial(1, probability)


def _train_one(
    *,
    output_root: Path,
    agent_id: AgentId,
    features,
    labels,
    config: SyntheticTrainingConfig,
) -> ModelArtifactManifest:
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import (
        average_precision_score,
        brier_score_loss,
        roc_auc_score,
    )
    from sklearn.model_selection import train_test_split
    from xgboost import XGBClassifier

    feature_names = (
        AFFORDABILITY_FEATURES
        if agent_id is AgentId.AFFORDABILITY
        else CREDIT_RISK_FEATURES
    )
    x_train, x_holdout, y_train, y_holdout = train_test_split(
        features,
        labels,
        test_size=config.test_fraction + config.validation_fraction,
        random_state=config.seed,
        stratify=labels,
    )
    relative_test_size = config.test_fraction / (
        config.test_fraction + config.validation_fraction
    )
    x_validation, x_test, y_validation, y_test = train_test_split(
        x_holdout,
        y_holdout,
        test_size=relative_test_size,
        random_state=config.seed + 1,
        stratify=y_holdout,
    )
    model = XGBClassifier(
        n_estimators=config.n_estimators,
        max_depth=config.max_depth,
        learning_rate=config.learning_rate,
        subsample=0.9,
        colsample_bytree=0.9,
        objective="binary:logistic",
        eval_metric="logloss",
        monotone_constraints=tuple(1 for _ in feature_names),
        tree_method="hist",
        random_state=config.seed,
        n_jobs=2,
    )
    model.fit(x_train, y_train)

    validation_probability = model.predict_proba(x_validation)[:, 1]
    calibrator = LogisticRegression(random_state=config.seed)
    calibrator.fit(validation_probability.reshape(-1, 1), y_validation)
    raw_test_probability = model.predict_proba(x_test)[:, 1]
    test_probability = calibrator.predict_proba(
        raw_test_probability.reshape(-1, 1)
    )[:, 1]

    artifact_dir = output_root / agent_id.value
    artifact_dir.mkdir(parents=True, exist_ok=True)
    model_path = artifact_dir / "model.json"
    model.get_booster().feature_names = list(feature_names)
    model.save_model(model_path)
    calibration = {
        "coefficient": float(calibrator.coef_[0][0]),
        "intercept": float(calibrator.intercept_[0]),
    }
    (artifact_dir / "calibration.json").write_text(
        json.dumps(calibration, indent=2, sort_keys=True) + "\n"
    )
    validation = {
        "sample_count": config.sample_count,
        "positive_rate": float(labels.mean()),
        "roc_auc": float(roc_auc_score(y_test, test_probability)),
        "pr_auc": float(average_precision_score(y_test, test_probability)),
        "brier_score": float(brier_score_loss(y_test, test_probability)),
        "feature_names": feature_names,
        "monotonic_constraints": [1 for _ in feature_names],
    }
    validation_path = artifact_dir / "validation.json"
    validation_path.write_text(
        json.dumps(validation, indent=2, sort_keys=True) + "\n"
    )
    artifact_hash = hashlib.sha256(model_path.read_bytes()).hexdigest()
    model_version = f"synthetic-{config.seed}-v1"
    manifest = ModelArtifactManifest(
        model_name=f"{agent_id.value}-monotonic-xgboost",
        model_version=model_version,
        agent_id=agent_id,
        provenance=ModelProvenance.SYNTHETIC,
        artifact_hash=f"sha256:{artifact_hash}",
        training_config={
            "sample_count": config.sample_count,
            "seed": config.seed,
            "noise_standard_deviation": config.noise_standard_deviation,
            "n_estimators": config.n_estimators,
            "max_depth": config.max_depth,
            "learning_rate": config.learning_rate,
        },
        validation_report_ref=str(validation_path),
    )
    (artifact_dir / "manifest.json").write_text(
        manifest.model_dump_json(indent=2) + "\n"
    )
    return manifest
