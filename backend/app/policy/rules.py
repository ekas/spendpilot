from typing import List
from app.models.schemas import AgentReport, ManagerReport, PolicyDecision

def decide(reports: List[AgentReport], manager: ManagerReport) -> PolicyDecision:
    flags=[]
    by_name={r.agent_name:r for r in reports}
    data=by_name["Data Quality Agent"]
    efficiency=by_name["Spend Efficiency Agent"]
    variance=by_name["Budget Variance Agent"]
    if data.score < 0.45:
        flags.append("POLICY_ACTION_REQUIRED_DATA_QUALITY_LOW")
        return PolicyDecision(final_decision="ACTION_REQUIRED", policy_flags=flags, requires_finance_review=True, reason="Data quality score below minimum policy threshold for reliable spend insights.")
    if efficiency.score < 0.35:
        flags.append("POLICY_ACTION_REQUIRED_SPEND_EFFICIENCY_LOW")
        return PolicyDecision(final_decision="ACTION_REQUIRED", policy_flags=flags, requires_finance_review=True, reason="Spend efficiency score indicates urgent budget control intervention.")
    if variance.score < 0.35:
        flags.append("POLICY_ACTION_REQUIRED_VARIANCE_HIGH")
        return PolicyDecision(final_decision="ACTION_REQUIRED", policy_flags=flags, requires_finance_review=True, reason="Variance risk score indicates unstable monthly spend behavior.")
    if manager.disagreements or manager.recommendation == "WATCHLIST" or any(r.recommendation == "WATCHLIST" for r in reports):
        flags.append("POLICY_WATCHLIST_FINANCE_REVIEW_RECOMMENDED")
        return PolicyDecision(final_decision="WATCHLIST", policy_flags=flags, requires_finance_review=True, reason="Spend profile needs finance review due to disagreement or borderline operating metrics.")
    flags.append("POLICY_HEALTHY_SPEND_PROFILE")
    return PolicyDecision(final_decision="HEALTHY", policy_flags=flags, requires_finance_review=False, reason="Spend profile is stable across data quality, efficiency, and variance checks.")
