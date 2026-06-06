from uuid import uuid4
from fastapi import APIRouter
from app.models.schemas import Applicant, CaseCreate, CaseResult
from app.agents import data_credibility_agent, affordability_agent, credit_risk_agent, manager_agent
from app.policy.rules import decide
from app.data.sample_cases import SAMPLE_CASES

router = APIRouter(prefix="/cases", tags=["cases"])
STORE = {}

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
    STORE[case_id] = result
    return result

@router.get("/samples")
def load_samples():
    results=[]
    for item in SAMPLE_CASES:
        results.append(run_case(Applicant(**item)))
    return results

@router.post("/create", response_model=CaseResult)
def create_case(payload: CaseCreate):
    return run_case(payload.applicant)

@router.get("", response_model=list[CaseResult])
def list_cases():
    if not STORE:
        load_samples()
    return list(STORE.values())

@router.get("/review-queue", response_model=list[CaseResult])
def review_queue():
    if not STORE:
        load_samples()
    return [c for c in STORE.values() if c.policy_decision.requires_human_review]

@router.post("/{case_id}/human-decision")
def human_decision(case_id: str, decision: str):
    case = STORE.get(case_id)
    if not case:
        return {"error":"case not found"}
    case.status = decision.upper()
    return {"case_id": case_id, "human_decision": decision.upper(), "message":"Human reviewer decision recorded for demo."}
