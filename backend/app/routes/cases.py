from uuid import uuid4
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from app.models.schemas import Applicant, CaseCreate, CaseResult
from app.agents import data_credibility_agent, affordability_agent, credit_risk_agent, manager_agent
from app.policy.rules import decide
from app.data.sample_cases import SAMPLE_CASES
from app.services.document_intelligence import analyze_uploaded_documents, persist_uploaded_documents
from app.storage.case_repository import case_count, list_cases as repo_list_cases, list_review_queue as repo_list_review_queue, save_case, set_human_decision

router = APIRouter(prefix="/cases", tags=["cases"])

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
