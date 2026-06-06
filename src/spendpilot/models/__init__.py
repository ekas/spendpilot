"""Model adapters and registry contracts."""

from spendpilot.models.contracts import ModelAdapter, ModelOutput
from spendpilot.models.registry import ModelDescriptor, ModelRegistry, ModelStatus

__all__ = [
    "ModelAdapter",
    "ModelDescriptor",
    "ModelOutput",
    "ModelRegistry",
    "ModelStatus",
]
