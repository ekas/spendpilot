from app.models.schemas import SpendProfile, AgentReport, Contributor


def run(profile: SpendProfile) -> AgentReport:
    signals = profile.document_signals or {}
    numeric_hints = signals.get("numeric_hints", {})

    effective_variance = max(profile.budget_variance_ratio, float(numeric_hints.get("budget_variance_ratio", profile.budget_variance_ratio)))
    effective_anomalies = max(profile.anomalous_transactions_30d, int(numeric_hints.get("anomalous_transactions_30d", profile.anomalous_transactions_30d)))
    effective_runway_months = min(profile.runway_months, int(numeric_hints.get("runway_months", profile.runway_months)))
    effective_invoice_match_rate = min(profile.invoice_match_rate, float(numeric_hints.get("invoice_match_rate", profile.invoice_match_rate)))

    risk = 0.10
    risk += effective_variance * 0.35
    risk += min(effective_anomalies, 20) * 0.02
    risk += 0.16 if effective_runway_months < 3 else 0.07 if effective_runway_months < 6 else -0.04
    risk += (1 - effective_invoice_match_rate) * 0.18
    score = max(0.0, min(1.0, 1-risk))

    contributors=[
        Contributor(feature="budget_variance_ratio", impact=round(effective_variance*0.35,2), direction="increases risk", explanation=f"Budget variance ratio is {effective_variance:.0%}."),
        Contributor(feature="anomalous_transactions_30d", impact=round(min(effective_anomalies,20)*0.02,2), direction="increases risk", explanation=f"Recent anomalous transactions: {effective_anomalies}."),
        Contributor(feature="runway_months", impact=-0.04 if effective_runway_months>=6 else 0.16, direction="decreases risk" if effective_runway_months>=6 else "increases risk", explanation=f"Current cash runway: {effective_runway_months} months."),
    ]
    reasons=[]
    if effective_variance > .25: reasons.append("HIGH_BUDGET_VARIANCE")
    if effective_anomalies > 4: reasons.append("ANOMALOUS_SPEND_PATTERN")
    if effective_runway_months < 3: reasons.append("LOW_CASH_RUNWAY")
    if effective_invoice_match_rate < 0.85: reasons.append("LOW_INVOICE_MATCH_RATE")
    if numeric_hints:
        reasons.append("DOC_HINTS_APPLIED")
    if not reasons: reasons=["SPEND_VARIANCE_STABLE"]
    recommendation = "HEALTHY" if score >= .74 else "WATCHLIST" if score >= .45 else "ACTION_REQUIRED"
    return AgentReport(agent_name="Budget Variance Agent", score=round(score,2), model_version="budget-variance-monotonic-v2", top_contributors=contributors, evidence_refs=["expense_ledger", "invoice_register"], reason_codes=reasons, confidence_status="demo_calibrated", recommendation=recommendation, summary="Scores spend volatility and control risk using variance, anomalies, runway, and invoice matching indicators.")
