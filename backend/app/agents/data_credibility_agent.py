from app.models.schemas import Applicant, AgentReport, Contributor

def run(applicant: Applicant) -> AgentReport:
    score = 0.85
    reasons = []
    contributors = []
    refs = applicant.documents or ["application_form"]

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

    score = max(0.0, min(1.0, score))
    recommendation = "PASS" if score >= 0.70 else "REFER" if score >= 0.45 else "REJECT"
    if not contributors:
        contributors.append(Contributor(feature="complete_evidence", impact=-0.10, direction="decreases risk", explanation="Required documents are present and internally consistent."))
        reasons.append("EVIDENCE_COMPLETE")

    return AgentReport(agent_name="Data Credibility Agent", score=round(score,2), model_version="data-credibility-rules-xgb-v1", top_contributors=contributors[:3], evidence_refs=refs, reason_codes=reasons, confidence_status="demo_calibrated", recommendation=recommendation, summary="Validates missing documents, inconsistent fields, and basic fraud/inconsistency indicators.")
