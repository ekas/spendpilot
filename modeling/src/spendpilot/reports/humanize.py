"""Plain-language labels for reviewer-facing report content."""

from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from spendpilot.schemas import AgentId


FEATURE_LABELS = {
    "monthly_income": "Monthly income",
    "monthly_expenses": "Monthly living expenses",
    "existing_debt": "Current outstanding debt",
    "credit_utilization": "Credit limit currently in use",
    "delinquencies_12m": "Late payments in the last 12 months",
    "employment_months": "Current employment history",
    "overdrafts_90d": "Bank overdrafts in the last 90 days",
    "income_verified": "Income verification",
    "document_count": "Documents supplied",
    "document_coverage_score": "Usable information found in documents",
    "document_consistency_flag_count": "Conflicts found across documents",
    "missing_documents": "Required documents missing",
    "evidence_complete": "Required evidence",
    "debt_to_income": "Existing debt compared with monthly income",
    "installment_burden": (
        "Estimated loan payment compared with available monthly cash"
    ),
    "expense_ratio": "Monthly income used by regular expenses",
    "income_unverified": "Income could not be independently verified",
    "employment_shortfall_months": (
        "Employment history below the 12-month reference"
    ),
    "annual_debt_ratio": "Existing debt compared with annual income",
}


REASON_EXPLANATIONS = {
    "MISSING_DOCUMENTS": (
        "One or more required documents were not supplied, so the application "
        "cannot be fully verified."
    ),
    "UNVERIFIED_INCOME": (
        "The stated income has not been independently verified."
    ),
    "LOW_DOCUMENT_COVERAGE": (
        "The supplied documents contain too little usable information for "
        "strong verification."
    ),
    "DOCUMENT_INCONSISTENCY": (
        "Information in the supplied documents does not fully agree."
    ),
    "EVIDENCE_COMPLETE": (
        "The expected documents are present and no material evidence problem "
        "was identified."
    ),
    "HIGH_DTI": (
        "Outstanding debt is high relative to monthly income, reducing "
        "repayment capacity."
    ),
    "LOW_AFFORDABILITY_BUFFER": (
        "The estimated payment would use a large share of the cash remaining "
        "after regular expenses."
    ),
    "HIGH_EXPENSE_RATIO": (
        "Regular expenses already consume a large share of monthly income."
    ),
    "RECENT_OVERDRAFTS": (
        "Recent overdrafts may indicate short-term cash-flow pressure."
    ),
    "HIGH_UTILIZATION": (
        "A large share of available credit is already being used."
    ),
    "RECENT_DELINQUENCY": (
        "Recent late payments increase the estimated risk of future missed "
        "payments."
    ),
    "SHORT_EMPLOYMENT_HISTORY": (
        "A short current employment history provides less evidence of stable "
        "income."
    ),
    "HIGH_ANNUAL_DEBT_RATIO": (
        "Outstanding debt is high compared with estimated annual income."
    ),
    "AFFORDABILITY_PROFILE_STABLE": (
        "The observed income, expenses, debt, and estimated payment leave a "
        "reasonable affordability buffer."
    ),
    "CREDIT_PROFILE_STABLE": (
        "The observed utilization, payment history, debt, and employment "
        "features indicate lower credit risk."
    ),
}

POLICY_EXPLANATIONS = {
    "UNANIMOUS_AUTOMATIC_APPROVAL": (
        "All three specialists recommended approval and no safety rule "
        "required a person to review the case."
    ),
    "HUMAN_REVIEW_REQUIRED": (
        "A person must review this case before a final lending decision."
    ),
    "MATERIAL_AGENT_DISAGREEMENT": (
        "The specialist agents reached different recommendations."
    ),
    "INCOMPLETE_REPORT_SET": (
        "One or more required specialist assessments are missing."
    ),
    "MONOTONICITY_CHECK_FAILED": (
        "A model safety check did not behave as expected."
    ),
    "LOW_MODEL_CONFIDENCE": (
        "At least one specialist has insufficient confidence for automatic "
        "processing."
    ),
    "FEEDBACK_REANALYSIS_REQUIRES_REVIEW": (
        "This case was reassessed after feedback and therefore requires a "
        "person to review the new result."
    ),
}

PROTECTIVE_EXPLANATIONS = {
    "MISSING_DOCUMENTS": "The required documents are sufficiently complete.",
    "UNVERIFIED_INCOME": "Income verification supports the stated income.",
    "LOW_DOCUMENT_COVERAGE": (
        "The documents provide enough usable information for verification."
    ),
    "DOCUMENT_INCONSISTENCY": (
        "No material conflict was found across the supplied documents."
    ),
    "HIGH_DTI": (
        "Outstanding debt is lower relative to monthly income, supporting "
        "repayment capacity."
    ),
    "LOW_AFFORDABILITY_BUFFER": (
        "The estimated payment uses a smaller share of the cash remaining "
        "after regular expenses."
    ),
    "HIGH_EXPENSE_RATIO": (
        "Regular expenses leave a stronger monthly affordability buffer."
    ),
    "RECENT_OVERDRAFTS": (
        "Few or no recent overdrafts indicate steadier short-term cash flow."
    ),
    "HIGH_UTILIZATION": (
        "A smaller share of available credit is currently being used."
    ),
    "RECENT_DELINQUENCY": (
        "Few or no recent late payments support a lower risk estimate."
    ),
    "SHORT_EMPLOYMENT_HISTORY": (
        "A longer current employment history supports income stability."
    ),
    "HIGH_ANNUAL_DEBT_RATIO": (
        "Outstanding debt is lower compared with estimated annual income."
    ),
    "EVIDENCE_COMPLETE": (
        "The expected documents are present and no material evidence problem "
        "was identified."
    ),
}


def human_label(identifier: str) -> str:
    """Return a readable label for a feature or arbitrary identifier."""

    normalized = identifier.removeprefix("numeric__").removeprefix(
        "categorical__"
    )
    return FEATURE_LABELS.get(
        normalized,
        normalized.replace("_", " ").strip().title(),
    )


def reason_explanation(reason_code: str) -> str:
    """Translate an immutable audit code for a general reviewer."""

    return REASON_EXPLANATIONS.get(
        reason_code,
        reason_code.replace("_", " ").strip().capitalize() + ".",
    )


def policy_explanation(rule_id: str, fallback: str) -> str:
    """Translate a deterministic policy rule for a general reviewer."""

    return POLICY_EXPLANATIONS.get(rule_id, fallback)


def contribution_explanation(
    reason_code: str,
    contribution: float,
) -> str:
    """Explain a feature consistently with the actual SHAP direction."""

    if contribution < 0:
        return PROTECTIVE_EXPLANATIONS.get(
            reason_code,
            "This observed value lowers the model's risk estimate.",
        )
    if contribution > 0:
        return reason_explanation(reason_code)
    return "This observed value has little effect on the model's risk estimate."


def format_feature_value(feature: str, value: object) -> str:
    """Format engineered values using their real-world meaning."""

    if feature in {
        "credit_utilization",
        "document_coverage_score",
        "debt_to_income",
        "installment_burden",
        "expense_ratio",
        "annual_debt_ratio",
    } and isinstance(value, (int, float)):
        return f"{float(value) * 100:.0f}%"
    if feature in {"employment_months", "employment_shortfall_months"}:
        return f"{int(float(value))} months"
    if feature in {
        "delinquencies_12m",
        "overdrafts_90d",
        "document_count",
        "document_consistency_flag_count",
        "missing_documents",
    }:
        return str(int(float(value)))
    if feature in {"income_verified", "evidence_complete"}:
        return "Yes" if bool(value) else "No"
    if feature == "income_unverified":
        return "Yes" if bool(value) else "No"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (int, float, Decimal)):
        return f"{float(value):,.2f}".rstrip("0").rstrip(".")
    return str(value)


def evidence_summary(
    evidence_refs: Iterable[str],
    all_case_refs: tuple[str, ...],
) -> str:
    """Describe opaque evidence without displaying internal hashes."""

    refs = tuple(dict.fromkeys(evidence_refs))
    if not refs:
        return "No supporting document was linked."
    indexes = [
        all_case_refs.index(reference) + 1
        for reference in refs
        if reference in all_case_refs
    ]
    if indexes:
        documents = ", ".join(str(index) for index in indexes)
        noun = "document" if len(indexes) == 1 else "documents"
        return (
            f"Supporting {noun} {documents}; identifiers hidden for privacy."
        )
    return (
        f"{len(refs)} supporting evidence reference"
        f"{'' if len(refs) == 1 else 's'}; identifiers hidden for privacy."
    )


def agent_method_label(agent_id: AgentId) -> str:
    """Describe each specialist without exposing artifact identifiers."""

    return {
        AgentId.CREDIBILITY: "Transparent document and consistency checks",
        AgentId.AFFORDABILITY: "Explainable affordability model",
        AgentId.CREDIT_RISK: "Explainable credit-risk model",
    }[agent_id]
