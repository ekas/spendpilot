"""Model adapters and registry contracts."""

from spendpilot.models.contracts import ModelAdapter, ModelOutput
from spendpilot.models.credibility_rules import CredibilityRulesAdapter
from spendpilot.models.mock import StaticModelAdapter
from spendpilot.models.registry import ModelDescriptor, ModelRegistry, ModelStatus
from spendpilot.models.scorecard import TransparentScorecardAdapter
from spendpilot.models.xgboost_adapter import MonotonicXGBoostAdapter

__all__ = [
    "ModelAdapter",
    "ModelDescriptor",
    "ModelOutput",
    "ModelRegistry",
    "ModelStatus",
    "CredibilityRulesAdapter",
    "MonotonicXGBoostAdapter",
    "StaticModelAdapter",
    "TransparentScorecardAdapter",
]
