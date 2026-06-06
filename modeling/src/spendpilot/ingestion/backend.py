"""Adapter for the current SpendPilot backend applicant payload."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from spendpilot.schemas.case import CaseSnapshot, CreditProduct


class BackendApplicant(BaseModel):
    """Input contract mirrored from ``backend/app/models/schemas.py``."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="redacted_applicant", min_length=1)
    monthly_income: float = Field(gt=0)
    monthly_expenses: float = Field(ge=0)
    requested_amount: float = Field(gt=0)
    existing_debt: float = Field(ge=0)
    credit_utilization: float = Field(ge=0, le=1)
    delinquencies_12m: int = Field(default=0, ge=0)
    employment_months: int = Field(default=0, ge=0)
    overdrafts_90d: int = Field(default=0, ge=0)
    income_verified: bool = False
    documents: tuple[str, ...] = ()
    document_text: str = ""
    document_signals: dict[str, Any] = Field(default_factory=dict)


class BackendInputAdapter:
    """Converts backend inputs into immutable, PII-minimized snapshots."""

    _required_documents = (
        "bank_statement",
        "id_document",
        "income_proof",
    )

    def to_snapshot(
        self,
        applicant: BackendApplicant,
        *,
        case_id: str,
        snapshot_id: str,
        applicant_ref: str | None = None,
        product: CreditProduct = CreditProduct.PERSONAL_LOAN,
        currency: str = "EUR",
    ) -> CaseSnapshot:
        numeric_hints = applicant.document_signals.get("numeric_hints", {})
        if not isinstance(numeric_hints, dict):
            numeric_hints = {}

        effective_income = min(
            applicant.monthly_income,
            self._number(numeric_hints, "monthly_income", applicant.monthly_income),
        )
        effective_expenses = max(
            applicant.monthly_expenses,
            self._number(
                numeric_hints,
                "monthly_expenses",
                applicant.monthly_expenses,
            ),
        )
        effective_debt = max(
            applicant.existing_debt,
            self._number(numeric_hints, "existing_debt", applicant.existing_debt),
        )
        effective_utilization = max(
            applicant.credit_utilization,
            self._number(
                numeric_hints,
                "credit_utilization",
                applicant.credit_utilization,
            ),
        )
        effective_delinquencies = max(
            applicant.delinquencies_12m,
            self._integer(
                numeric_hints,
                "delinquencies_12m",
                applicant.delinquencies_12m,
            ),
        )
        effective_employment_months = min(
            applicant.employment_months,
            self._integer(
                numeric_hints,
                "employment_months",
                applicant.employment_months,
            ),
        )

        flags = applicant.document_signals.get("consistency_flags", ())
        if not isinstance(flags, (list, tuple)):
            flags = ()
        coverage_score = applicant.document_signals.get("coverage_score", 0.0)
        if not isinstance(coverage_score, (int, float)):
            coverage_score = 0.0
        coverage_score = min(max(float(coverage_score), 0.0), 1.0)

        document_presence = {
            f"{required}_present": any(
                required in document.lower() for document in applicant.documents
            )
            for required in self._required_documents
        }
        features: dict[str, bool | int | float | str | None] = {
            "monthly_income": effective_income,
            "monthly_expenses": effective_expenses,
            "existing_debt": effective_debt,
            "credit_utilization": min(effective_utilization, 1.0),
            "delinquencies_12m": effective_delinquencies,
            "employment_months": effective_employment_months,
            "overdrafts_90d": applicant.overdrafts_90d,
            "income_verified": applicant.income_verified,
            "document_count": len(applicant.documents),
            "document_coverage_score": coverage_score,
            "document_consistency_flag_count": len(flags),
            "document_hints_applied": bool(numeric_hints),
            **document_presence,
        }
        evidence_refs = tuple(
            f"document:{hashlib.sha256(document.encode()).hexdigest()[:16]}"
            for document in applicant.documents
        )
        missing_fields = tuple(
            required
            for required in self._required_documents
            if not document_presence[f"{required}_present"]
        )
        canonical = {
            "case_id": case_id,
            "snapshot_id": snapshot_id,
            "product": product.value,
            "requested_amount": applicant.requested_amount,
            "currency": currency,
            "features": features,
            "evidence_refs": evidence_refs,
            "missing_fields": missing_fields,
        }
        content_digest = hashlib.sha256(
            json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        pseudonym = applicant_ref or (
            "applicant:"
            + hashlib.sha256(
                f"{case_id}:{applicant.name}".encode()
            ).hexdigest()[:16]
        )

        return CaseSnapshot(
            case_id=case_id,
            snapshot_id=snapshot_id,
            applicant_ref=pseudonym,
            product=product,
            requested_amount=Decimal(str(applicant.requested_amount)),
            currency=currency,
            content_hash=f"sha256:{content_digest}",
            features=features,
            evidence_refs=evidence_refs,
            missing_fields=missing_fields,
        )

    def revise_snapshot(
        self,
        snapshot: CaseSnapshot,
        *,
        snapshot_id: str,
        feature_updates: dict[str, bool | int | float | str | None],
    ) -> CaseSnapshot:
        """Create a new immutable snapshot for a hypothetical assessment."""

        features = {**snapshot.features, **feature_updates}
        canonical = {
            "case_id": snapshot.case_id,
            "snapshot_id": snapshot_id,
            "product": snapshot.product.value,
            "requested_amount": float(snapshot.requested_amount),
            "currency": snapshot.currency,
            "features": features,
            "evidence_refs": snapshot.evidence_refs,
            "missing_fields": snapshot.missing_fields,
        }
        content_digest = hashlib.sha256(
            json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return snapshot.model_copy(
            update={
                "snapshot_id": snapshot_id,
                "created_at": datetime.now(timezone.utc),
                "content_hash": f"sha256:{content_digest}",
                "features": features,
            }
        )

    @staticmethod
    def _number(values: dict[str, Any], key: str, fallback: float) -> float:
        value = values.get(key, fallback)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return fallback
        return max(float(value), 0.0)

    @classmethod
    def _integer(cls, values: dict[str, Any], key: str, fallback: int) -> int:
        return int(cls._number(values, key, float(fallback)))
