from app.models.schemas import Applicant, AgentReport, Contributor

def run(applicant: Applicant) -> AgentReport:
    signals = applicant.document_signals or {}
    numeric_hints = signals.get("numeric_hints", {})

    effective_income = min(applicant.monthly_income, float(numeric_hints.get("monthly_income", applicant.monthly_income)))
    effective_expenses = max(applicant.monthly_expenses, float(numeric_hints.get("monthly_expenses", applicant.monthly_expenses)))
    effective_debt = max(applicant.existing_debt, float(numeric_hints.get("existing_debt", applicant.existing_debt)))

    free_cash_flow = effective_income - effective_expenses
    dti = effective_debt / max(effective_income, 1)
    installment_proxy = applicant.requested_amount / 36
    burden = installment_proxy / max(free_cash_flow, 1)

    risk = 0.15 + min(dti, 1.5) * 0.35 + min(burden, 2.0) * 0.25 + min(applicant.overdrafts_90d, 5) * 0.04
    if applicant.income_verified: risk -= 0.08
    if free_cash_flow > installment_proxy * 2: risk -= 0.10
    score = max(0.0, min(1.0, 1 - risk))

    contributors = [
        Contributor(feature="debt_to_income_ratio", impact=round(min(dti,1.5)*0.35,2), direction="increases risk", explanation=f"Debt-to-income ratio is {dti:.2f}."),
        Contributor(feature="free_cash_flow", impact=round(-0.10 if free_cash_flow > installment_proxy*2 else 0.12,2), direction="decreases risk" if free_cash_flow > installment_proxy*2 else "increases risk", explanation=f"Estimated free cash flow is €{free_cash_flow:.0f}."),
        Contributor(feature="overdrafts_90d", impact=round(min(applicant.overdrafts_90d,5)*0.04,2), direction="increases risk", explanation=f"Overdraft count in last 90 days: {applicant.overdrafts_90d}."),
    ]
    reasons=[]
    if dti > 0.45: reasons.append("HIGH_DTI")
    if burden > 0.6: reasons.append("LOW_AFFORDABILITY_BUFFER")
    if applicant.overdrafts_90d >= 2: reasons.append("RECENT_OVERDRAFTS")
    if numeric_hints:
        reasons.append("DOC_HINTS_APPLIED")
    if not reasons: reasons=["AFFORDABILITY_BUFFER_OK"]
    recommendation = "PASS" if score >= .72 else "REFER" if score >= .45 else "REJECT"
    return AgentReport(agent_name="Affordability Agent", score=round(score,2), model_version="affordability-monotonic-xgb-v1", top_contributors=contributors, evidence_refs=["bank_statement", "income_proof"], reason_codes=reasons, confidence_status="demo_calibrated", recommendation=recommendation, summary="Monotonic XGBoost-style affordability model: risk rises with DTI, burden, overdrafts and falls with verified income/free cash flow.")
