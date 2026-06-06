from app.models.schemas import Applicant, AgentReport, Contributor

def run(applicant: Applicant) -> AgentReport:
    signals = applicant.document_signals or {}
    numeric_hints = signals.get("numeric_hints", {})

    effective_utilization = max(applicant.credit_utilization, float(numeric_hints.get("credit_utilization", applicant.credit_utilization)))
    effective_delinquencies = max(applicant.delinquencies_12m, int(numeric_hints.get("delinquencies_12m", applicant.delinquencies_12m)))
    effective_employment_months = min(applicant.employment_months, int(numeric_hints.get("employment_months", applicant.employment_months)))

    risk = 0.10
    risk += effective_utilization * 0.35
    risk += min(effective_delinquencies, 4) * 0.12
    risk += 0.15 if effective_employment_months < 6 else 0.07 if effective_employment_months < 12 else -0.05
    risk += min(applicant.existing_debt / max(applicant.monthly_income*12, 1), 1.5) * 0.15
    score = max(0.0, min(1.0, 1-risk))

    contributors=[
        Contributor(feature="credit_utilization", impact=round(effective_utilization*0.35,2), direction="increases risk", explanation=f"Credit utilization is {effective_utilization:.0%}."),
        Contributor(feature="delinquencies_12m", impact=round(min(effective_delinquencies,4)*0.12,2), direction="increases risk", explanation=f"Recent delinquencies: {effective_delinquencies}."),
        Contributor(feature="employment_stability", impact=-0.05 if effective_employment_months>=12 else 0.15, direction="decreases risk" if effective_employment_months>=12 else "increases risk", explanation=f"Employment history: {effective_employment_months} months."),
    ]
    reasons=[]
    if effective_utilization > .75: reasons.append("HIGH_UTILIZATION")
    if effective_delinquencies > 0: reasons.append("RECENT_DELINQUENCY")
    if effective_employment_months < 6: reasons.append("SHORT_EMPLOYMENT_HISTORY")
    if numeric_hints:
        reasons.append("DOC_HINTS_APPLIED")
    if not reasons: reasons=["STABLE_CREDIT_PROFILE"]
    recommendation = "PASS" if score >= .74 else "REFER" if score >= .45 else "REJECT"
    return AgentReport(agent_name="Credit Risk Agent", score=round(score,2), model_version="credit-risk-monotonic-xgb-v1", top_contributors=contributors, evidence_refs=["credit_bureau_snapshot"], reason_codes=reasons, confidence_status="demo_calibrated", recommendation=recommendation, summary="Probability-of-default style model with TreeSHAP-like reason contributions.")
