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
        "profile": {
            "company_name": "Test Company",
            "monthly_revenue": 240000,
            "monthly_spend": 160000,
            "planned_budget": 170000,
            "cash_reserve": 90000,
            "budget_variance_ratio": 0.12,
            "anomalous_transactions_30d": 2,
            "runway_months": 7,
            "late_payments_90d": 1,
            "invoice_match_rate": 0.94,
            "books_verified": True,
            "documents": ["general_ledger_jan.csv", "vendor_aging_jan.csv", "budget_plan_q1.json"],
        }
    }

    response = client.post("/cases/create", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["case_id"]
    assert data["profile"]["company_name"] == "Test Company"
    assert data["policy_decision"]["final_decision"] in {"HEALTHY", "WATCHLIST", "ACTION_REQUIRED"}


def test_create_case_with_upload_accepts_multipart_and_files() -> None:
    files = [
        (
            "files",
            (
                "income.txt",
                "monthly_revenue: 260000\nmonthly_spend: 158000\nbooks verified\n",
                "text/plain",
            ),
        ),
        (
            "files",
            (
                "credit.json",
                '{"budget_variance_ratio": 0.14, "anomalous_transactions_30d": 2, "runway_months": 8}',
                "application/json",
            ),
        ),
    ]

    data = {
        "company_name": "Upload Company",
        "monthly_revenue": "250000",
        "monthly_spend": "170000",
        "planned_budget": "175000",
        "cash_reserve": "70000",
        "budget_variance_ratio": "0.18",
        "anomalous_transactions_30d": "2",
        "runway_months": "6",
        "late_payments_90d": "1",
        "invoice_match_rate": "0.92",
        "books_verified": "false",
    }

    response = client.post("/cases/create-with-upload", data=data, files=files)

    assert response.status_code == 200
    body = response.json()
    assert body["profile"]["documents"]
    assert body["profile"]["document_signals"]["coverage_score"] >= 0
    assert isinstance(body["profile"]["document_signals"]["stored_paths"], list)


def test_human_decision_validation_and_not_found() -> None:
    missing_case = client.post("/cases/unknown/human-decision", params={"decision": "HEALTHY"})
    assert missing_case.status_code == 404

    payload = {
        "profile": {
            "company_name": "Decision Target",
            "monthly_revenue": 210000,
            "monthly_spend": 140000,
            "planned_budget": 150000,
            "cash_reserve": 60000,
            "budget_variance_ratio": 0.11,
            "anomalous_transactions_30d": 1,
            "runway_months": 7,
            "late_payments_90d": 0,
            "invoice_match_rate": 0.95,
            "books_verified": True,
            "documents": ["general_ledger_jan.csv", "vendor_aging_jan.csv", "budget_plan_q1.json"],
        }
    }
    created = client.post("/cases/create", json=payload)
    case_id = created.json()["case_id"]

    invalid = client.post(f"/cases/{case_id}/human-decision", params={"decision": "MAYBE"})
    assert invalid.status_code == 422

    valid = client.post(f"/cases/{case_id}/human-decision", params={"decision": "ACTION_REQUIRED"})
    assert valid.status_code == 200
    assert valid.json()["finance_decision"] == "ACTION_REQUIRED"


def test_review_queue_filters_cases_requiring_human_review() -> None:
    response = client.get("/cases/review-queue")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    for case in payload:
        assert case["policy_decision"]["requires_finance_review"] is True


def test_compare_periods_returns_side_by_side_metrics() -> None:
    payload = {
        "profile": {
            "company_name": "Compare Company",
            "monthly_revenue": 230000,
            "monthly_spend": 150000,
            "planned_budget": 155000,
            "cash_reserve": 72000,
            "budget_variance_ratio": 0.09,
            "anomalous_transactions_30d": 1,
            "runway_months": 8,
            "late_payments_90d": 0,
            "invoice_match_rate": 0.97,
            "books_verified": True,
            "documents": ["general_ledger_jan.csv", "vendor_aging_jan.csv", "budget_plan_q1.json"],
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


def test_modeling_analysis_uses_governed_agent_contracts() -> None:
    response = client.post(
        "/modeling/analyze",
        json={
            "applicant": {
                "name": "Private Applicant",
                "monthly_income": 4200,
                "monthly_expenses": 2100,
                "requested_amount": 6000,
                "existing_debt": 800,
                "credit_utilization": 0.22,
                "delinquencies_12m": 0,
                "employment_months": 28,
                "overdrafts_90d": 0,
                "income_verified": True,
                "documents": [
                    "private_id_document.pdf",
                    "private_bank_statement.pdf",
                    "private_income_proof.pdf",
                ],
                "document_text": "Private Applicant earns 4200 per month.",
            }
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["specialist_reports"]) == 3
    assert body["model_runtime"]["score_semantics"] == "adverse_risk"
    assert body["model_runtime"]["pii_minimized"] is True
    assert body["policy_decision"]["final_authority"].startswith(
        "Deterministic policy engine"
    )
    assert all(
        report["score_semantics"] == "adverse_risk"
        for report in body["specialist_reports"]
    )
    model_payload = str(body["specialist_reports"]) + str(
        body["manager_report"]
    )
    assert "Private Applicant" not in model_payload
    assert "earns 4200" not in model_payload
    assert body["applicant"]["document_text"] == ""


def test_modeling_health_reports_artifact_or_scorecard_runtime() -> None:
    response = client.get("/modeling/health")

    assert response.status_code == 200
    assert response.json()["fallback"] == "transparent_scorecard"
