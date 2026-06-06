from typing import List
from app.models.schemas import AgentReport, ManagerReport

def run(reports: List[AgentReport]) -> ManagerReport:
    recs = {r.agent_name: r.recommendation for r in reports}
    scores = {r.agent_name: r.score for r in reports}
    disagreements=[]
    if len(set(recs.values())) > 1:
        disagreements.append(f"Agents disagree: {recs}")
    if max(scores.values()) - min(scores.values()) > 0.35:
        disagreements.append("Large confidence gap between specialist scores.")
    requested=[]
    for r in reports:
        if r.recommendation == "REFER" and r.score < 0.55:
            requested.append(f"Request targeted re-analysis from {r.agent_name}")
    if any(r.recommendation == "REJECT" for r in reports):
        recommendation="REFER"
    elif disagreements or any(r.recommendation == "REFER" for r in reports):
        recommendation="REFER"
    else:
        recommendation="APPROVE"
    all_reasons=[]
    for r in reports:
        all_reasons.extend(r.reason_codes)
    reviewer_summary = " | ".join([f"{r.agent_name}: {r.recommendation} ({r.score})" for r in reports])
    explanation = "Manager summarizes specialist outputs only. It does not change scores or approve credit. Main reason codes: " + ", ".join(sorted(set(all_reasons)))
    return ManagerReport(recommendation=recommendation, disagreements=disagreements, requested_reanalysis=requested, reviewer_summary=reviewer_summary, readable_explanation=explanation)
