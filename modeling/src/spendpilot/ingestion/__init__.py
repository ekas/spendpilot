"""Input adapters that create privacy-safe modeling snapshots."""

from spendpilot.ingestion.backend import BackendApplicant, BackendInputAdapter
from spendpilot.ingestion.external import (
    ExternalCaseBatch,
    ExternalCaseRequest,
    load_external_cases,
)

__all__ = [
    "BackendApplicant",
    "BackendInputAdapter",
    "ExternalCaseBatch",
    "ExternalCaseRequest",
    "load_external_cases",
]
