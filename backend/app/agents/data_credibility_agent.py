from app.models.schemas import Applicant, AgentReport, Contributor

def run(applicant: Applicant) -> AgentReport:
    score = 0.85
    reasons = []
    contributors = []
    refs = applicant.documents or ["application_form"]
    signals = applicant.document_signals or {}
    numeric_hints = signals.get("numeric_hints", {})
    consistency_flags = signals.get("consistency_flags", [])
    coverage_score = float(signals.get("coverage_score", 0.0))

    required = ["bank_statement", "id_document", "income_proof"]
    missing = [d for d in required if not any(d in x.lower() for x in applicant.documents)]
    if missing:
        score -= 0.12 * len(missing)
        reasons.append("MISSING_DOCUMENTS")
        contributors.append(Contributor(feature="missing_documents", impact=0.12*len(missing), direction="increases risk", explanation=f"Missing: {', '.join(missing)}"))

    if not applicant.income_verified:
        score -= 0.18
        reasons.append("UNVERIFIED_INCOME")
        contributors.append(Contributor(feature="income_verified", impact=0.18, direction="increases risk", explanation="Income has not been verified by supplied documents."))

    if applicant.monthly_income <= 0 or applicant.requested_amount <= 0:
        score -= 0.25
        reasons.append("INVALID_FIELDS")
        contributors.append(Contributor(feature="field_validation", impact=0.25, direction="increases risk", explanation="Application contains invalid financial fields."))

    if coverage_score < 0.25 and applicant.documents:
        score -= 0.10
        reasons.append("LOW_DOCUMENT_COVERAGE")
        contributors.append(Contributor(feature="document_coverage", impact=0.10, direction="increases risk", explanation="Uploaded documents provided limited machine-readable financial signals."))

    if consistency_flags:
        score -= min(0.2, 0.08 * len(consistency_flags))
        reasons.extend(consistency_flags)
        contributors.append(Contributor(feature="document_consistency", impact=min(0.2, 0.08 * len(consistency_flags)), direction="increases risk", explanation="Detected potential inconsistencies in uploaded documents."))

    hinted_income = numeric_hints.get("monthly_income")
    if hinted_income and applicant.monthly_income > 0:
        delta_ratio = abs(float(hinted_income) - applicant.monthly_income) / applicant.monthly_income
        if delta_ratio > 0.2:
            score -= 0.12
            reasons.append("INCOME_MISMATCH_WITH_DOCUMENTS")
            contributors.append(Contributor(feature="income_mismatch", impact=0.12, direction="increases risk", explanation="Document-extracted income materially differs from provided application income."))

    score = max(0.0, min(1.0, score))
    recommendation = "PASS" if score >= 0.70 else "REFER" if score >= 0.45 else "REJECT"
    if not contributors:
        contributors.append(Contributor(feature="complete_evidence", impact=-0.10, direction="decreases risk", explanation="Required documents are present and internally consistent."))
        reasons.append("EVIDENCE_COMPLETE")

    return AgentReport(agent_name="Data Credibility Agent", score=round(score,2), model_version="data-credibility-rules-xgb-v1", top_contributors=contributors[:3], evidence_refs=refs, reason_codes=reasons, confidence_status="demo_calibrated", recommendation=recommendation, summary="Validates missing documents, inconsistent fields, and basic fraud/inconsistency indicators.")
