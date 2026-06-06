from uuid import uuid4
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from app.models.schemas import SpendProfile, CaseCreate, CaseResult
from app.agents import data_credibility_agent, affordability_agent, credit_risk_agent, manager_agent
from app.policy.rules import decide
from app.data.sample_cases import SAMPLE_CASES
from app.services.document_intelligence import analyze_uploaded_documents, persist_uploaded_documents
from app.storage.case_repository import case_count, list_cases as repo_list_cases, list_cases_between, list_review_queue as repo_list_review_queue, save_case, set_human_decision

router = APIRouter(prefix="/cases", tags=["cases"])


def _to_ts_range(start_date: date, end_date: date) -> tuple[str, str]:
    if end_date < start_date:
        raise HTTPException(status_code=422, detail="end date must be on or after start date")

    start_dt = datetime.combine(start_date, time.min)
    end_dt = datetime.combine(end_date + timedelta(days=1), time.min)
    return start_dt.strftime("%Y-%m-%d %H:%M:%S"), end_dt.strftime("%Y-%m-%d %H:%M:%S")


def _safe_rate(part: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round(part / total, 4)


def _summarize_period(cases: list[CaseResult], start_date: date, end_date: date) -> dict:
    totals = {"HEALTHY": 0, "WATCHLIST": 0, "ACTION_REQUIRED": 0}
    finance_review_count = 0
    score_acc = {}
    score_counts = {}

    for case in cases:
        totals[case.status] = totals.get(case.status, 0) + 1
        if case.policy_decision.requires_finance_review:
            finance_review_count += 1

        for report in case.specialist_reports:
            score_acc[report.agent_name] = score_acc.get(report.agent_name, 0.0) + report.score
            score_counts[report.agent_name] = score_counts.get(report.agent_name, 0) + 1

    avg_scores = {
        name: round(score_acc[name] / score_counts[name], 4)
        for name in sorted(score_acc.keys())
    }
    total_cases = len(cases)

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_cases": total_cases,
        "decision_counts": totals,
        "decision_rates": {
            "HEALTHY": _safe_rate(totals.get("HEALTHY", 0), total_cases),
            "WATCHLIST": _safe_rate(totals.get("WATCHLIST", 0), total_cases),
            "ACTION_REQUIRED": _safe_rate(totals.get("ACTION_REQUIRED", 0), total_cases),
        },
        "finance_review_rate": _safe_rate(finance_review_count, total_cases),
        "avg_specialist_scores": avg_scores,
    }

def run_case(profile: SpendProfile, case_id: str | None = None) -> CaseResult:
    case_id = case_id or str(uuid4())[:8]
    reports = [
        data_credibility_agent.run(profile),
        affordability_agent.run(profile),
        credit_risk_agent.run(profile),
    ]
    manager = manager_agent.run(reports)
    policy = decide(reports, manager)
    result = CaseResult(
        case_id=case_id,
        profile=profile,
        status=policy.final_decision,
        specialist_reports=reports,
        manager_report=manager,
        policy_decision=policy,
    )
    save_case(result)
    return result


def _build_profile_from_form(
    *,
    company_name: str,
    monthly_revenue: float,
    monthly_spend: float,
    planned_budget: float,
    cash_reserve: float,
    budget_variance_ratio: float,
    anomalous_transactions_30d: int,
    runway_months: int,
    late_payments_90d: int,
    invoice_match_rate: float,
    books_verified: bool,
) -> SpendProfile:
    return SpendProfile(
        company_name=company_name,
        monthly_revenue=monthly_revenue,
        monthly_spend=monthly_spend,
        planned_budget=planned_budget,
        cash_reserve=cash_reserve,
        budget_variance_ratio=budget_variance_ratio,
        anomalous_transactions_30d=anomalous_transactions_30d,
        runway_months=runway_months,
        late_payments_90d=late_payments_90d,
        invoice_match_rate=invoice_match_rate,
        books_verified=books_verified,
        documents=[],
    )

@router.get("/samples")
def load_samples():
    results=[]
    for item in SAMPLE_CASES:
        results.append(run_case(SpendProfile(**item)))
    return results

@router.post("/create", response_model=CaseResult)
def create_case(payload: CaseCreate):
    return run_case(payload.profile)


@router.post("/create-with-upload", response_model=CaseResult)
async def create_case_with_upload(
    company_name: str = Form(...),
    monthly_revenue: float = Form(...),
    monthly_spend: float = Form(...),
    planned_budget: float = Form(...),
    cash_reserve: float = Form(...),
    budget_variance_ratio: float = Form(...),
    anomalous_transactions_30d: int = Form(0),
    runway_months: int = Form(0),
    late_payments_90d: int = Form(0),
    invoice_match_rate: float = Form(1.0),
    books_verified: bool = Form(False),
    files: list[UploadFile] = File(...),
):
    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required.")

    case_id = str(uuid4())[:8]
    profile = _build_profile_from_form(
        company_name=company_name,
        monthly_revenue=monthly_revenue,
        monthly_spend=monthly_spend,
        planned_budget=planned_budget,
        cash_reserve=cash_reserve,
        budget_variance_ratio=budget_variance_ratio,
        anomalous_transactions_30d=anomalous_transactions_30d,
        runway_months=runway_months,
        late_payments_90d=late_payments_90d,
        invoice_match_rate=invoice_match_rate,
        books_verified=books_verified,
    )

    analysis = await analyze_uploaded_documents(files)
    stored_paths = await persist_uploaded_documents(files, case_id)

    profile.documents = analysis["evidence_refs"]
    profile.document_text = analysis["document_text"]
    profile.document_signals = analysis["document_signals"]
    profile.document_signals["stored_paths"] = stored_paths

    if analysis["document_signals"].get("books_verified_from_docs"):
        profile.books_verified = True

    return run_case(profile, case_id=case_id)

@router.get("", response_model=list[CaseResult])
def list_cases():
    if case_count() == 0:
        load_samples()
    return repo_list_cases()

@router.get("/review-queue", response_model=list[CaseResult])
def review_queue():
    if case_count() == 0:
        load_samples()
    return [c for c in repo_list_review_queue() if c.policy_decision.requires_finance_review]

@router.post("/{case_id}/human-decision")
def human_decision(case_id: str, decision: str):
    if decision.upper() not in {"HEALTHY", "WATCHLIST", "ACTION_REQUIRED"}:
        raise HTTPException(status_code=422, detail="decision must be one of HEALTHY, WATCHLIST, ACTION_REQUIRED")
    updated = set_human_decision(case_id, decision.upper())
    if not updated:
        raise HTTPException(status_code=404, detail="case not found")
    return {"case_id": case_id, "finance_decision": decision.upper(), "message":"Finance reviewer decision recorded for demo."}


@router.get("/compare-periods")
def compare_periods(
    period_a_start: date = Query(..., description="Start date for period A (YYYY-MM-DD)"),
    period_a_end: date = Query(..., description="End date for period A (YYYY-MM-DD)"),
    period_b_start: date = Query(..., description="Start date for period B (YYYY-MM-DD)"),
    period_b_end: date = Query(..., description="End date for period B (YYYY-MM-DD)"),
):
    a_start_ts, a_end_ts = _to_ts_range(period_a_start, period_a_end)
    b_start_ts, b_end_ts = _to_ts_range(period_b_start, period_b_end)

    cases_a = list_cases_between(a_start_ts, a_end_ts)
    cases_b = list_cases_between(b_start_ts, b_end_ts)

    summary_a = _summarize_period(cases_a, period_a_start, period_a_end)
    summary_b = _summarize_period(cases_b, period_b_start, period_b_end)

    return {
        "period_a": summary_a,
        "period_b": summary_b,
        "delta": {
            "total_cases": summary_b["total_cases"] - summary_a["total_cases"],
            "healthy_rate": round(summary_b["decision_rates"]["HEALTHY"] - summary_a["decision_rates"]["HEALTHY"], 4),
            "watchlist_rate": round(summary_b["decision_rates"]["WATCHLIST"] - summary_a["decision_rates"]["WATCHLIST"], 4),
            "action_required_rate": round(summary_b["decision_rates"]["ACTION_REQUIRED"] - summary_a["decision_rates"]["ACTION_REQUIRED"], 4),
            "finance_review_rate": round(summary_b["finance_review_rate"] - summary_a["finance_review_rate"], 4),
        },
    }
