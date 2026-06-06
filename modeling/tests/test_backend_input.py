from spendpilot.ingestion import BackendApplicant, BackendInputAdapter


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
