"""Contracts for model artifacts, benchmarks, and manager assistance."""

from datetime import datetime, timezone
from enum import StrEnum
from typing import TypeAlias

from pydantic import BaseModel, ConfigDict, Field, field_validator

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
    assistant_provider: str | None = None
    assistant_model: str | None = None
    assistant_request_id: str | None = None
    assistant_latency_ms: float | None = Field(default=None, ge=0)


class FeedbackRoutingProposal(BaseModel):
    """Non-authoritative feedback targets proposed by a manager assistant."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    feedback_id: str = Field(min_length=1)
    proposed_targets: tuple[AgentId, ...] = Field(min_length=1)
    rationale_codes: tuple[str, ...] = Field(min_length=1)
    assistant_provider: str | None = None
    assistant_model: str | None = None
    assistant_request_id: str | None = None
    assistant_latency_ms: float | None = Field(default=None, ge=0)

    @field_validator("proposed_targets", "rationale_codes")
    @classmethod
    def values_must_be_unique(cls, values: tuple) -> tuple:
        if len(values) != len(set(values)):
            raise ValueError("routing proposal values must be unique")
        return values


class LocalLLMProbePurpose(StrEnum):
    """Structured capabilities evaluated by the local-model smoke test."""

    NARRATIVE = "narrative"
    FEEDBACK_ROUTING = "feedback_routing"


class LocalLLMProbe(BaseModel):
    """One schema-constrained local-model evaluation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    purpose: LocalLLMProbePurpose
    case_id: str | None = None
    success: bool
    schema_valid: bool
    latency_ms: float | None = Field(default=None, ge=0)
    narrative: ManagerNarrative | None = None
    routing_proposal: FeedbackRoutingProposal | None = None
    fallback_reason: str | None = None


class LocalLLMSmokeReport(BaseModel):
    """Audit report for an experimental local GGUF assistant."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    model_name: str = Field(min_length=1)
    model_file: str = Field(min_length=1)
    model_path_hash: str = Field(pattern=r"^sha256:[a-fA-F0-9]{64}$")
    artifact_hash: str = Field(pattern=r"^sha256:[a-fA-F0-9]{64}$")
    llama_cpp_version: str = Field(min_length=1)
    endpoint: str = Field(min_length=1)
    context_size: int = Field(ge=1)
    max_output_tokens: int = Field(ge=1)
    experimental: bool = True
    promoted: bool = False
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    probes: tuple[LocalLLMProbe, ...] = Field(min_length=1)
    success_rate: float = Field(ge=0, le=1)
    recommendation: str = Field(min_length=1)
