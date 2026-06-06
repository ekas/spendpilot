"""In-memory model registry used by orchestration and tests."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from spendpilot.models.contracts import ModelAdapter
from spendpilot.schemas.agent_report import AgentId


class ModelStatus(StrEnum):
    """Governance state of a registered model."""

    DEVELOPMENT = "development"
    VALIDATED = "validated"
    RETIRED = "retired"


class ModelDescriptor(BaseModel):
    """Governance metadata for a model adapter."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    agent_id: AgentId
    model_name: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    status: ModelStatus = ModelStatus.DEVELOPMENT


class ModelRegistry:
    """Registers one active adapter per specialist agent."""

    def __init__(self) -> None:
        self._models: dict[AgentId, tuple[ModelDescriptor, ModelAdapter]] = {}

    def register(
        self,
        descriptor: ModelDescriptor,
        adapter: ModelAdapter,
    ) -> None:
        if descriptor.model_name != adapter.model_name:
            raise ValueError("descriptor and adapter model names do not match")
        if descriptor.model_version != adapter.model_version:
            raise ValueError("descriptor and adapter model versions do not match")
        self._models[descriptor.agent_id] = (descriptor, adapter)

    def get(self, agent_id: AgentId) -> ModelAdapter:
        try:
            descriptor, adapter = self._models[agent_id]
        except KeyError as exc:
            raise LookupError(f"no model registered for {agent_id}") from exc
        if descriptor.status is ModelStatus.RETIRED:
            raise LookupError(f"model for {agent_id} is retired")
        return adapter

    def descriptors(self) -> tuple[ModelDescriptor, ...]:
        return tuple(descriptor for descriptor, _ in self._models.values())
