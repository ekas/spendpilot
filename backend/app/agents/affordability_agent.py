from app.models.schemas import SpendProfile, AgentReport, Contributor


def run(profile: SpendProfile) -> AgentReport:
    signals = profile.document_signals or {}
    numeric_hints = signals.get("numeric_hints", {})

    effective_revenue = min(profile.monthly_revenue, float(numeric_hints.get("monthly_revenue", profile.monthly_revenue)))
    effective_spend = max(profile.monthly_spend, float(numeric_hints.get("monthly_spend", profile.monthly_spend)))
    effective_budget = min(profile.planned_budget, float(numeric_hints.get("planned_budget", profile.planned_budget)))

    efficiency_margin = (effective_revenue - effective_spend) / max(effective_revenue, 1)
    budget_overshoot = max(0.0, (effective_spend - effective_budget) / max(effective_budget, 1))
    reserve_buffer = profile.cash_reserve / max(effective_spend, 1)

    risk = 0.20 + min(budget_overshoot, 1.5) * 0.35 + (0.25 if efficiency_margin < 0 else 0.08)
    risk += min(profile.late_payments_90d, 5) * 0.05
    if profile.books_verified:
        risk -= 0.07
    if reserve_buffer > 1.2:
        risk -= 0.12
    score = max(0.0, min(1.0, 1 - risk))

    contributors = [
        Contributor(feature="budget_overshoot", impact=round(min(budget_overshoot, 1.5) * 0.35,2), direction="increases risk", explanation=f"Spend-to-budget overshoot ratio is {budget_overshoot:.2f}."),
        Contributor(feature="efficiency_margin", impact=round(-0.10 if efficiency_margin > 0.2 else 0.16,2), direction="decreases risk" if efficiency_margin > 0.2 else "increases risk", explanation=f"Operating spend margin is {efficiency_margin:.2%}."),
        Contributor(feature="late_payments_90d", impact=round(min(profile.late_payments_90d,5)*0.05,2), direction="increases risk", explanation=f"Late vendor payments in last 90 days: {profile.late_payments_90d}."),
    ]
    reasons=[]
    if budget_overshoot > 0.15: reasons.append("BUDGET_OVERSHOOT")
    if efficiency_margin < 0.05: reasons.append("LOW_SPEND_EFFICIENCY")
    if profile.late_payments_90d >= 2: reasons.append("RECENT_LATE_PAYMENTS")
    if numeric_hints:
        reasons.append("DOC_HINTS_APPLIED")
    if not reasons: reasons=["SPEND_EFFICIENCY_STABLE"]
    recommendation = "HEALTHY" if score >= .72 else "WATCHLIST" if score >= .45 else "ACTION_REQUIRED"
    return AgentReport(agent_name="Spend Efficiency Agent", score=round(score,2), model_version="spend-efficiency-monotonic-v2", top_contributors=contributors, evidence_refs=["general_ledger", "budget_plan"], reason_codes=reasons, confidence_status="demo_calibrated", recommendation=recommendation, summary="Evaluates budget discipline, spend efficiency margin, and payment hygiene to score operational spend quality.")
