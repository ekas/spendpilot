from typing import List
from app.models.schemas import AgentReport, ManagerReport, PolicyDecision

def decide(reports: List[AgentReport], manager: ManagerReport) -> PolicyDecision:
    flags=[]
    by_name={r.agent_name:r for r in reports}
    data=by_name["Data Credibility Agent"]
    aff=by_name["Affordability Agent"]
    credit=by_name["Credit Risk Agent"]
    if data.score < 0.45:
        flags.append("POLICY_REJECT_EVIDENCE_CREDIBILITY_TOO_LOW")
        return PolicyDecision(final_decision="REJECT", policy_flags=flags, requires_human_review=False, reason="Evidence credibility below minimum policy threshold.")
    if aff.score < 0.35:
        flags.append("POLICY_REJECT_AFFORDABILITY_TOO_LOW")
        return PolicyDecision(final_decision="REJECT", policy_flags=flags, requires_human_review=False, reason="Affordability score below minimum policy threshold.")
    if credit.score < 0.35:
        flags.append("POLICY_REJECT_CREDIT_RISK_TOO_HIGH")
        return PolicyDecision(final_decision="REJECT", policy_flags=flags, requires_human_review=False, reason="Credit risk below minimum acceptance threshold.")
    if manager.disagreements or manager.recommendation == "REFER" or any(r.recommendation == "REFER" for r in reports):
        flags.append("POLICY_REFER_HUMAN_REVIEW_REQUIRED")
        return PolicyDecision(final_decision="REFER", policy_flags=flags, requires_human_review=True, reason="Case requires human review due to disagreement, borderline scores, or adverse indicators.")
    flags.append("POLICY_APPROVE_LOW_RISK")
    return PolicyDecision(final_decision="APPROVE", policy_flags=flags, requires_human_review=False, reason="All specialist agents passed and deterministic policy thresholds are satisfied.")
