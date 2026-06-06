import os
from pathlib import Path

from fastapi.testclient import TestClient

TEST_DB_PATH = Path(__file__).parent / "decisionos_test.db"
os.environ["DECISIONOS_DB_PATH"] = str(TEST_DB_PATH)

from app.main import app
from app.storage.case_repository import clear_all_cases, init_db


client = TestClient(app)


def setup_function() -> None:
    init_db()
    clear_all_cases()


def test_create_case_json_returns_case_result() -> None:
    payload = {
        "applicant": {
            "name": "Test Applicant",
            "monthly_income": 4200,
            "monthly_expenses": 1900,
            "requested_amount": 5000,
            "existing_debt": 700,
            "credit_utilization": 0.28,
            "delinquencies_12m": 0,
            "employment_months": 24,
            "overdrafts_90d": 0,
            "income_verified": True,
            "documents": ["id_document.pdf", "bank_statement_jan.pdf", "income_proof.pdf"],
        }
    }

    response = client.post("/cases/create", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["case_id"]
    assert data["applicant"]["name"] == "Test Applicant"
    assert data["policy_decision"]["final_decision"] in {"APPROVE", "REFER", "REJECT"}


def test_create_case_with_upload_accepts_multipart_and_files() -> None:
    files = [
        (
            "files",
            (
                "income.txt",
                "monthly_income: 5200\nmonthly_expenses: 2500\nincome verified\n",
                "text/plain",
            ),
        ),
        (
            "files",
            (
                "credit.json",
                '{"credit_utilization": 0.41, "delinquencies_12m": 1, "employment_months": 18}',
                "application/json",
            ),
        ),
    ]

    data = {
        "name": "Upload Applicant",
        "monthly_income": "5000",
        "monthly_expenses": "2400",
        "requested_amount": "8000",
        "existing_debt": "1200",
        "credit_utilization": "0.35",
        "delinquencies_12m": "0",
        "employment_months": "20",
        "overdrafts_90d": "0",
        "income_verified": "false",
    }

    response = client.post("/cases/create-with-upload", data=data, files=files)

    assert response.status_code == 200
    body = response.json()
    assert body["applicant"]["documents"]
    assert body["applicant"]["document_signals"]["coverage_score"] >= 0
    assert isinstance(body["applicant"]["document_signals"]["stored_paths"], list)


def test_human_decision_validation_and_not_found() -> None:
    missing_case = client.post("/cases/unknown/human-decision", params={"decision": "APPROVE"})
    assert missing_case.status_code == 404

    payload = {
        "applicant": {
            "name": "Decision Target",
            "monthly_income": 4000,
            "monthly_expenses": 2000,
            "requested_amount": 6000,
            "existing_debt": 1000,
            "credit_utilization": 0.3,
            "delinquencies_12m": 0,
            "employment_months": 18,
            "overdrafts_90d": 0,
            "income_verified": True,
            "documents": ["id_document.pdf", "bank_statement_jan.pdf", "income_proof.pdf"],
        }
    }
    created = client.post("/cases/create", json=payload)
    case_id = created.json()["case_id"]

    invalid = client.post(f"/cases/{case_id}/human-decision", params={"decision": "MAYBE"})
    assert invalid.status_code == 422

    valid = client.post(f"/cases/{case_id}/human-decision", params={"decision": "REJECT"})
    assert valid.status_code == 200
    assert valid.json()["human_decision"] == "REJECT"


def test_review_queue_filters_cases_requiring_human_review() -> None:
    response = client.get("/cases/review-queue")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    for case in payload:
        assert case["policy_decision"]["requires_human_review"] is True


def test_compare_periods_returns_side_by_side_metrics() -> None:
    payload = {
        "applicant": {
            "name": "Compare Applicant",
            "monthly_income": 4200,
            "monthly_expenses": 2000,
            "requested_amount": 6000,
            "existing_debt": 900,
            "credit_utilization": 0.3,
            "delinquencies_12m": 0,
            "employment_months": 20,
            "overdrafts_90d": 0,
            "income_verified": True,
            "documents": ["id_document.pdf", "bank_statement_jan.pdf", "income_proof.pdf"],
        }
    }
    client.post("/cases/create", json=payload)

    response = client.get(
        "/cases/compare-periods",
        params={
            "period_a_start": "2000-01-01",
            "period_a_end": "2000-01-31",
            "period_b_start": "2000-02-01",
            "period_b_end": "2100-12-31",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert "period_a" in body
    assert "period_b" in body
    assert "delta" in body
    assert body["period_a"]["total_cases"] == 0
    assert body["period_b"]["total_cases"] >= 1
