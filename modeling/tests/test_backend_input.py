import json

import pytest
from pydantic import ValidationError

from spendpilot.ingestion import (
    BackendApplicant,
    BackendInputAdapter,
    load_external_cases,
)


def test_backend_adapter_removes_pii_and_applies_conservative_hints() -> None:
    applicant = BackendApplicant(
        name="Amina Example",
        monthly_income=4200,
        monthly_expenses=2100,
        requested_amount=6000,
        existing_debt=800,
        credit_utilization=0.22,
        delinquencies_12m=0,
        employment_months=28,
        overdrafts_90d=0,
        income_verified=True,
        documents=(
            "amina_id_document.pdf",
            "amina_bank_statement.pdf",
            "amina_income_proof.pdf",
        ),
        document_text="Amina Example earns 4200 per month.",
        document_signals={
            "numeric_hints": {
                "monthly_income": 3900,
                "monthly_expenses": 2300,
                "existing_debt": 1000,
                "credit_utilization": 0.31,
                "delinquencies_12m": 1,
                "employment_months": 24,
            },
            "coverage_score": 0.8,
            "consistency_flags": ["INCOME_MISMATCH"],
        },
    )

    snapshot = BackendInputAdapter().to_snapshot(
        applicant,
        case_id="case_1",
        snapshot_id="snapshot_1",
    )

    assert snapshot.features["monthly_income"] == 3900
    assert snapshot.features["monthly_expenses"] == 2300
    assert snapshot.features["existing_debt"] == 1000
    assert snapshot.features["credit_utilization"] == 0.31
    assert snapshot.features["delinquencies_12m"] == 1
    assert snapshot.features["employment_months"] == 24
    assert snapshot.features["document_consistency_flag_count"] == 1
    assert snapshot.missing_fields == ()
    assert all(ref.startswith("document:") for ref in snapshot.evidence_refs)

    serialized = snapshot.model_dump_json()
    assert "Amina Example" not in serialized
    assert "earns 4200" not in serialized
    assert "amina_" not in serialized


def test_backend_adapter_marks_missing_required_documents() -> None:
    applicant = BackendApplicant(
        name="Applicant",
        monthly_income=2400,
        monthly_expenses=2300,
        requested_amount=18000,
        existing_debt=13000,
        credit_utilization=0.91,
        documents=("id_document.pdf",),
    )

    snapshot = BackendInputAdapter().to_snapshot(
        applicant,
        case_id="case_2",
        snapshot_id="snapshot_1",
        applicant_ref="applicant_token",
    )

    assert snapshot.missing_fields == ("bank_statement", "income_proof")
    assert snapshot.features["bank_statement_present"] is False
    assert snapshot.features["id_document_present"] is True


def test_external_json_is_validated_and_removes_direct_pii(tmp_path) -> None:
    input_path = tmp_path / "cases.json"
    input_path.write_text(
        json.dumps(
            {
                "case_id": "external_case_1",
                "applicant": {
                    "name": "Private Person",
                    "monthly_income": 4200,
                    "monthly_expenses": 2100,
                    "requested_amount": 6000,
                    "existing_debt": 800,
                    "credit_utilization": 0.22,
                    "employment_months": 28,
                    "income_verified": True,
                    "documents": [
                        "private_id_document.pdf",
                        "private_bank_statement.pdf",
                        "private_income_proof.pdf",
                    ],
                    "document_text": "Private Person earns 4200.",
                },
            }
        )
    )

    requests = load_external_cases(input_path)
    snapshot = requests[0].to_snapshot()
    serialized = snapshot.model_dump_json()

    assert snapshot.case_id == "external_case_1"
    assert "Private Person" not in serialized
    assert "earns 4200" not in serialized
    assert "private_" not in serialized


def test_external_json_rejects_unknown_or_invalid_fields(tmp_path) -> None:
    input_path = tmp_path / "invalid.json"
    input_path.write_text(
        json.dumps(
            {
                "case_id": "external_case_1",
                "applicant": {
                    "name": "Example",
                    "monthly_income": -1,
                    "monthly_expenses": 100,
                    "requested_amount": 500,
                    "existing_debt": 0,
                    "credit_utilization": 0.1,
                    "unsupported_field": "not allowed",
                },
            }
        )
    )

    with pytest.raises(ValidationError):
        load_external_cases(input_path)


def test_external_json_does_not_require_a_name(tmp_path) -> None:
    input_path = tmp_path / "anonymous.json"
    input_path.write_text(
        json.dumps(
            {
                "case_id": "anonymous_case",
                "applicant_ref": "source_customer_42",
                "applicant": {
                    "monthly_income": 3000,
                    "monthly_expenses": 1800,
                    "requested_amount": 5000,
                    "existing_debt": 1000,
                    "credit_utilization": 0.25,
                },
            }
        )
    )

    snapshot = load_external_cases(input_path)[0].to_snapshot()

    assert snapshot.applicant_ref == "source_customer_42"
