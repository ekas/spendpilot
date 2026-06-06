"""Deterministic model adapters for local development and tests."""

from spendpilot.models.contracts import ModelOutput
from spendpilot.schemas.case import CaseSnapshot


class StaticModelAdapter:
    """Returns a prevalidated model output without loading an ML artifact."""

    def __init__(
        self,
        *,
        model_name: str,
        model_version: str,
        output: ModelOutput,
    ) -> None:
        self._model_name = model_name
        self._model_version = model_version
        self._output = output

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def model_version(self) -> str:
        return self._model_version

    def predict(self, case: CaseSnapshot) -> ModelOutput:
        del case
        return self._output
