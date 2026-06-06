"""Contracts for model artifacts, benchmarks, and manager assistance."""

from enum import StrEnum
from typing import TypeAlias

from pydantic import BaseModel, ConfigDict, Field

from spendpilot.schemas.agent_report import AgentId


MetricValue: TypeAlias = bool | int | float | str


class ModelProvenance(StrEnum):
    """Origin of a registered model or deterministic adapter."""

    RULES = "rules"
    SYNTHETIC = "synthetic"
    PUBLIC_BENCHMARK = "public_benchmark"
    PRODUCTION_OUTCOMES = "production_outcomes"
    PRETRAINED = "pretrained"


class ModelArtifactManifest(BaseModel):
    """Immutable metadata needed to reproduce one model artifact."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    model_name: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    agent_id: AgentId
    provenance: ModelProvenance
    artifact_hash: str = Field(pattern=r"^sha256:[a-fA-F0-9]{64}$")
    training_config: dict[str, MetricValue] = Field(default_factory=dict)
    validation_report_ref: str = Field(min_length=1)


class BenchmarkContext(BaseModel):
    """Read-only aggregate evidence from an external research benchmark."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    dataset_name: str = Field(min_length=1)
    dataset_version: str = Field(min_length=1)
    metrics: dict[str, float]
    excluded_features: tuple[str, ...] = ()
    limitations: tuple[str, ...] = Field(min_length=1)
    report_ref: str = Field(min_length=1)


class ManagerNarrative(BaseModel):
    """Schema-validated language-model explanation for a manager report."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    summary: str = Field(min_length=1)
    disagreement_explanation: str = Field(min_length=1)
    reviewer_focus: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()


class FeedbackRoutingProposal(BaseModel):
    """Non-authoritative feedback targets proposed by a manager assistant."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    feedback_id: str = Field(min_length=1)
    proposed_targets: tuple[AgentId, ...] = Field(min_length=1)
    rationale_codes: tuple[str, ...] = Field(min_length=1)
