from uuid import uuid4
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from app.models.schemas import Applicant, CaseCreate, CaseResult
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
    totals = {"APPROVE": 0, "REFER": 0, "REJECT": 0}
    human_review_count = 0
    score_acc = {}
    score_counts = {}

    for case in cases:
        totals[case.status] = totals.get(case.status, 0) + 1
        if case.policy_decision.requires_human_review:
            human_review_count += 1

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
            "APPROVE": _safe_rate(totals.get("APPROVE", 0), total_cases),
            "REFER": _safe_rate(totals.get("REFER", 0), total_cases),
            "REJECT": _safe_rate(totals.get("REJECT", 0), total_cases),
        },
        "human_review_rate": _safe_rate(human_review_count, total_cases),
        "avg_specialist_scores": avg_scores,
    }

def run_case(applicant: Applicant, case_id: str | None = None) -> CaseResult:
    case_id = case_id or str(uuid4())[:8]
    reports = [
        data_credibility_agent.run(applicant),
        affordability_agent.run(applicant),
        credit_risk_agent.run(applicant),
    ]
    manager = manager_agent.run(reports)
    policy = decide(reports, manager)
    result = CaseResult(
        case_id=case_id,
        applicant=applicant,
        status=policy.final_decision,
        specialist_reports=reports,
        manager_report=manager,
        policy_decision=policy,
    )
    save_case(result)
    return result


def _build_applicant_from_form(
    *,
    name: str,
    monthly_income: float,
    monthly_expenses: float,
    requested_amount: float,
    existing_debt: float,
    credit_utilization: float,
    delinquencies_12m: int,
    employment_months: int,
    overdrafts_90d: int,
    income_verified: bool,
) -> Applicant:
    return Applicant(
        name=name,
        monthly_income=monthly_income,
        monthly_expenses=monthly_expenses,
        requested_amount=requested_amount,
        existing_debt=existing_debt,
        credit_utilization=credit_utilization,
        delinquencies_12m=delinquencies_12m,
        employment_months=employment_months,
        overdrafts_90d=overdrafts_90d,
        income_verified=income_verified,
        documents=[],
    )

@router.get("/samples")
def load_samples():
    results=[]
    for item in SAMPLE_CASES:
        results.append(run_case(Applicant(**item)))
    return results

@router.post("/create", response_model=CaseResult)
def create_case(payload: CaseCreate):
    return run_case(payload.applicant)


@router.post("/create-with-upload", response_model=CaseResult)
async def create_case_with_upload(
    name: str = Form(...),
    monthly_income: float = Form(...),
    monthly_expenses: float = Form(...),
    requested_amount: float = Form(...),
    existing_debt: float = Form(...),
    credit_utilization: float = Form(...),
    delinquencies_12m: int = Form(0),
    employment_months: int = Form(0),
    overdrafts_90d: int = Form(0),
    income_verified: bool = Form(False),
    files: list[UploadFile] = File(...),
):
    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required.")

    case_id = str(uuid4())[:8]
    applicant = _build_applicant_from_form(
        name=name,
        monthly_income=monthly_income,
        monthly_expenses=monthly_expenses,
        requested_amount=requested_amount,
        existing_debt=existing_debt,
        credit_utilization=credit_utilization,
        delinquencies_12m=delinquencies_12m,
        employment_months=employment_months,
        overdrafts_90d=overdrafts_90d,
        income_verified=income_verified,
    )

    analysis = await analyze_uploaded_documents(files)
    stored_paths = await persist_uploaded_documents(files, case_id)

    applicant.documents = analysis["evidence_refs"]
    applicant.document_text = analysis["document_text"]
    applicant.document_signals = analysis["document_signals"]
    applicant.document_signals["stored_paths"] = stored_paths

    if analysis["document_signals"].get("income_verified_from_docs"):
        applicant.income_verified = True

    return run_case(applicant, case_id=case_id)

@router.get("", response_model=list[CaseResult])
def list_cases():
    if case_count() == 0:
        load_samples()
    return repo_list_cases()

@router.get("/review-queue", response_model=list[CaseResult])
def review_queue():
    if case_count() == 0:
        load_samples()
    return repo_list_review_queue()

@router.post("/{case_id}/human-decision")
def human_decision(case_id: str, decision: str):
    if decision.upper() not in {"APPROVE", "REJECT", "REFER"}:
        raise HTTPException(status_code=422, detail="decision must be one of APPROVE, REJECT, REFER")
    updated = set_human_decision(case_id, decision.upper())
    if not updated:
        raise HTTPException(status_code=404, detail="case not found")
    return {"case_id": case_id, "human_decision": decision.upper(), "message":"Human reviewer decision recorded for demo."}


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
            "approve_rate": round(summary_b["decision_rates"]["APPROVE"] - summary_a["decision_rates"]["APPROVE"], 4),
            "refer_rate": round(summary_b["decision_rates"]["REFER"] - summary_a["decision_rates"]["REFER"], 4),
            "reject_rate": round(summary_b["decision_rates"]["REJECT"] - summary_a["decision_rates"]["REJECT"], 4),
            "human_review_rate": round(summary_b["human_review_rate"] - summary_a["human_review_rate"], 4),
        },
    }
