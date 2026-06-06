from app.models.schemas import SpendProfile, AgentReport, Contributor


def run(profile: SpendProfile) -> AgentReport:
    score = 0.85
    reasons = []
    contributors = []
    refs = profile.documents or ["spend_submission_form"]
    signals = profile.document_signals or {}
    numeric_hints = signals.get("numeric_hints", {})
    consistency_flags = signals.get("consistency_flags", [])
    coverage_score = float(signals.get("coverage_score", 0.0))

    required = ["general_ledger", "vendor_aging", "budget_plan"]
    missing = [d for d in required if not any(d in x.lower() for x in profile.documents)]
    if missing:
        score -= 0.12 * len(missing)
        reasons.append("MISSING_DOCUMENTS")
        contributors.append(Contributor(feature="missing_documents", impact=0.12*len(missing), direction="increases risk", explanation=f"Missing: {', '.join(missing)}"))

    if not profile.books_verified:
        score -= 0.18
        reasons.append("UNVERIFIED_BOOKS")
        contributors.append(Contributor(feature="books_verified", impact=0.18, direction="increases risk", explanation="Finance books have not been verified with supporting documents."))

    if profile.monthly_revenue <= 0 or profile.planned_budget <= 0:
        score -= 0.25
        reasons.append("INVALID_FIELDS")
        contributors.append(Contributor(feature="field_validation", impact=0.25, direction="increases risk", explanation="Spend profile contains invalid finance values."))

    if coverage_score < 0.25 and profile.documents:
        score -= 0.10
        reasons.append("LOW_DOCUMENT_COVERAGE")
        contributors.append(Contributor(feature="document_coverage", impact=0.10, direction="increases risk", explanation="Uploaded documents provided limited machine-readable financial signals."))

    if consistency_flags:
        score -= min(0.2, 0.08 * len(consistency_flags))
        reasons.extend(consistency_flags)
        contributors.append(Contributor(feature="document_consistency", impact=min(0.2, 0.08 * len(consistency_flags)), direction="increases risk", explanation="Detected potential inconsistencies in uploaded documents."))

    hinted_spend = numeric_hints.get("monthly_spend")
    if hinted_spend and profile.monthly_spend > 0:
        delta_ratio = abs(float(hinted_spend) - profile.monthly_spend) / profile.monthly_spend
        if delta_ratio > 0.2:
            score -= 0.12
            reasons.append("SPEND_MISMATCH_WITH_DOCUMENTS")
            contributors.append(Contributor(feature="spend_mismatch", impact=0.12, direction="increases risk", explanation="Document-extracted monthly spend materially differs from provided spend profile."))

    score = max(0.0, min(1.0, score))
    recommendation = "HEALTHY" if score >= 0.70 else "WATCHLIST" if score >= 0.45 else "ACTION_REQUIRED"
    if not contributors:
        contributors.append(Contributor(feature="complete_evidence", impact=-0.10, direction="decreases risk", explanation="Required spend documents are present and internally consistent."))
        reasons.append("EVIDENCE_COMPLETE")

    return AgentReport(agent_name="Data Quality Agent", score=round(score,2), model_version="data-quality-rules-v2", top_contributors=contributors[:3], evidence_refs=refs, reason_codes=reasons, confidence_status="demo_calibrated", recommendation=recommendation, summary="Validates spend data completeness, document consistency, and bookkeeping confidence.")
