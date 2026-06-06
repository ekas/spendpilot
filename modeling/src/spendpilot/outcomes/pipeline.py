"""Append-only outcomes and offline-only model learning preparation."""

import calendar
from datetime import date, datetime, timezone
from typing import Mapping

from pydantic import BaseModel, ConfigDict, Field

from spendpilot.schemas.agent_report import AgentId
from spendpilot.schemas.case import CaseSnapshot, FeatureValue
from spendpilot.schemas.decision import DecisionAction, DecisionRecord
from spendpilot.schemas.outcome import OutcomeEvent


LABEL_DEFINITION = "90_plus_dpd_within_12_months"


class OutcomeStore:
    """Append-only, deduplicated repayment observations."""

    def __init__(self) -> None:
        self._events: dict[str, OutcomeEvent] = {}
        self._source_keys: set[tuple[str, str]] = set()

    def append(self, event: OutcomeEvent) -> OutcomeEvent:
        if event.outcome_event_id in self._events:
            raise ValueError(
                f"outcome event {event.outcome_event_id} already exists"
            )
        source_key = (event.source.value, event.source_event_ref)
        if source_key in self._source_keys:
            raise ValueError("source repayment event was already ingested")
        self._events[event.outcome_event_id] = event
        self._source_keys.add(source_key)
        return event

    def get(self, outcome_event_id: str) -> OutcomeEvent:
        try:
            return self._events[outcome_event_id]
        except KeyError as exc:
            raise LookupError(
                f"outcome event {outcome_event_id} was not found"
            ) from exc

    def for_decision(self, decision_id: str) -> tuple[OutcomeEvent, ...]:
        return tuple(
            sorted(
                (
                    event
                    for event in self._events.values()
                    if event.decision_id == decision_id
                ),
                key=lambda event: (
                    event.observation_date,
                    event.recorded_at,
                    event.outcome_event_id,
                ),
            )
        )

    def all(self) -> tuple[OutcomeEvent, ...]:
        return tuple(self._events.values())


class OutcomeLabel(BaseModel):
    """Maturity and value of the governed credit-risk outcome."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    decision_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    definition: str = LABEL_DEFINITION
    value: int | None = Field(default=None, ge=0, le=1)
    mature: bool
    observation_window_end: date
    as_of: date
    positive_event_ids: tuple[str, ...] = ()


class TrainingExample(BaseModel):
    """One leakage-controlled row for offline model development."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    decision_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    feature_cutoff_at: datetime
    features: dict[str, FeatureValue]
    label: int = Field(ge=0, le=1)
    label_definition: str = LABEL_DEFINITION
    observation_window_end: date
    positive_event_ids: tuple[str, ...] = ()


class OutcomeDataset(BaseModel):
    """Immutable offline dataset manifest and examples."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    dataset_id: str = Field(min_length=1)
    label_definition: str = LABEL_DEFINITION
    as_of: date
    examples: tuple[TrainingExample, ...]
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class CandidateModelEvaluation(BaseModel):
    """Offline validation result for a candidate model artifact."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evaluation_id: str = Field(min_length=1)
    candidate_model_name: str = Field(min_length=1)
    candidate_model_version: str = Field(min_length=1)
    agent_id: AgentId
    dataset_id: str = Field(min_length=1)
    metrics: dict[str, float]
    passed_validation: bool
    evaluated_by: str = Field(min_length=1)
    evaluated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class CandidateApproval(BaseModel):
    """Explicit human approval that remains separate from deployment."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    approval_id: str = Field(min_length=1)
    evaluation_id: str = Field(min_length=1)
    approved: bool
    approver_id: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    approved_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class OutcomeDatasetBuilder:
    """Creates point-in-time examples from original decision snapshots."""

    def __init__(self, store: OutcomeStore) -> None:
        self._store = store

    def label(
        self,
        decision: DecisionRecord,
        *,
        as_of: date,
    ) -> OutcomeLabel:
        decision_date = decision.decided_at.date()
        window_end = _add_calendar_months(decision_date, 12)
        events = self._validated_events(decision)
        positive_events = tuple(
            event
            for event in events
            if decision_date <= event.observation_date <= window_end
            and event.days_past_due >= 90
        )
        if positive_events:
            value = 1
            mature = True
        elif as_of >= window_end:
            value = 0
            mature = True
        else:
            value = None
            mature = False
        return OutcomeLabel(
            decision_id=decision.decision_id,
            case_id=decision.case_id,
            value=value,
            mature=mature,
            observation_window_end=window_end,
            as_of=as_of,
            positive_event_ids=tuple(
                event.outcome_event_id for event in positive_events
            ),
        )

    def build(
        self,
        *,
        dataset_id: str,
        decisions: tuple[DecisionRecord, ...],
        snapshots: Mapping[str, CaseSnapshot],
        as_of: date,
    ) -> OutcomeDataset:
        examples: list[TrainingExample] = []
        for decision in decisions:
            if not decision.finalized or decision.action is not DecisionAction.APPROVE:
                continue
            snapshot = self._original_snapshot(decision, snapshots)
            label = self.label(decision, as_of=as_of)
            if not label.mature:
                continue
            assert label.value is not None
            examples.append(
                TrainingExample(
                    decision_id=decision.decision_id,
                    case_id=decision.case_id,
                    snapshot_id=snapshot.snapshot_id,
                    feature_cutoff_at=decision.decided_at,
                    features=dict(snapshot.features),
                    label=label.value,
                    observation_window_end=label.observation_window_end,
                    positive_event_ids=label.positive_event_ids,
                )
            )
        return OutcomeDataset(
            dataset_id=dataset_id,
            as_of=as_of,
            examples=tuple(examples),
        )

    def _validated_events(
        self,
        decision: DecisionRecord,
    ) -> tuple[OutcomeEvent, ...]:
        events = self._store.for_decision(decision.decision_id)
        for event in events:
            if event.case_id != decision.case_id:
                raise ValueError("outcome event case does not match its decision")
            if event.observation_date < decision.decided_at.date():
                raise ValueError("outcome event predates the credit decision")
        return events

    @staticmethod
    def _original_snapshot(
        decision: DecisionRecord,
        snapshots: Mapping[str, CaseSnapshot],
    ) -> CaseSnapshot:
        try:
            snapshot = snapshots[decision.snapshot_id]
        except KeyError as exc:
            raise LookupError(
                f"original snapshot {decision.snapshot_id} was not supplied"
            ) from exc
        if snapshot.snapshot_id != decision.snapshot_id:
            raise ValueError("snapshot mapping key and identifier differ")
        if snapshot.case_id != decision.case_id:
            raise ValueError("snapshot case does not match its decision")
        if snapshot.created_at > decision.decided_at:
            raise ValueError(
                "snapshot was created after the decision feature cutoff"
            )
        return snapshot


class OutcomeLearningPipeline:
    """Coordinates outcome capture and offline governance artifacts only."""

    def __init__(self, store: OutcomeStore | None = None) -> None:
        self.store = store or OutcomeStore()
        self.dataset_builder = OutcomeDatasetBuilder(self.store)
        self._evaluations: dict[str, CandidateModelEvaluation] = {}
        self._approvals: dict[str, CandidateApproval] = {}

    def ingest(self, event: OutcomeEvent) -> OutcomeEvent:
        return self.store.append(event)

    def record_evaluation(
        self,
        evaluation: CandidateModelEvaluation,
    ) -> CandidateModelEvaluation:
        if evaluation.evaluation_id in self._evaluations:
            raise ValueError("candidate evaluation already exists")
        self._evaluations[evaluation.evaluation_id] = evaluation
        return evaluation

    def approve(
        self,
        approval: CandidateApproval,
    ) -> CandidateApproval:
        if approval.approval_id in self._approvals:
            raise ValueError("candidate approval already exists")
        try:
            evaluation = self._evaluations[approval.evaluation_id]
        except KeyError as exc:
            raise LookupError("candidate evaluation was not found") from exc
        if approval.approved and not evaluation.passed_validation:
            raise ValueError("a failed candidate evaluation cannot be approved")
        self._approvals[approval.approval_id] = approval
        return approval

    def evaluations(self) -> tuple[CandidateModelEvaluation, ...]:
        return tuple(self._evaluations.values())

    def approvals(self) -> tuple[CandidateApproval, ...]:
        return tuple(self._approvals.values())


def _add_calendar_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)
