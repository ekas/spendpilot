from fastapi import APIRouter

from app.models.modeling import ModelingAnalysisRequest
from app.services.modeling_workflow import modeling_health, run_modeling_workflow


router = APIRouter(prefix="/modeling", tags=["modeling"])


@router.get("/health")
def health():
    return modeling_health()


@router.post("/analyze")
def analyze(payload: ModelingAnalysisRequest):
    return run_modeling_workflow(payload)
