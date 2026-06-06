from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.models.modeling import ModelingAnalysisRequest
from spendpilot.demo import build_runtime_workflow
from spendpilot.ingestion import BackendApplicant, BackendInputAdapter
from spendpilot.schemas.agent_report import AgentId, AgentReport, Recommendation
from spendpilot.schemas.decision import DecisionAction


_AGENT_NAMES = {
    AgentId.CREDIBILITY: "Data Credibility Agent",
    AgentId.AFFORDABILITY: "Affordability Agent",
    AgentId.CREDIT_RISK: "Credit Risk Agent",
}

_FEATURE_LABELS = {
    "annual_debt_ratio": "Debt compared with annual income",
    "credit_utilization": "Credit limit currently in use",
    "debt_to_income": "Debt compared with monthly income",
    "delinquencies_12m": "Late payments in the last 12 months",
    "document_consistency_flag_count": "Document inconsistencies",
    "document_coverage_score": "Usable document coverage",
    "employment_shortfall_months": "Employment history below 12 months",
    "evidence_complete": "Required evidence is complete",
    "expense_ratio": "Monthly income used for expenses",
    "income_unverified": "Income is not independently verified",
    "income_verified": "Income verification",
    "installment_burden": "Estimated repayment burden",
    "missing_documents": "Missing required documents",
    "overdrafts_90d": "Overdrafts in the last 90 days",
}


def run_modeling_workflow(payload: ModelingAnalysisRequest) -> dict:
    case_id = payload.case_id or str(uuid4())[:8]
    applicant = BackendApplicant.model_validate(
        payload.applicant.model_dump()
    )
    snapshot = BackendInputAdapter().to_snapshot(
        applicant,
        case_id=case_id,
        snapshot_id=payload.snapshot_id,
    )
    workflow, model_source = build_runtime_workflow(_artifact_root())
    result = workflow.run(snapshot)
    reports = [
        _serialize_report(report, model_source)
        for report in result.reports
    ]

    disagreement = []
    if result.manager_report.disagreement:
        assessments = ", ".join(
            f"{_AGENT_NAMES[report.agent_id]}: "
            f"{report.recommendation.value.replace('_', ' ')}"
            for report in result.reports
        )
        disagreement.append(
            f"Specialists reached different recommendations ({assessments})."
        )

    requested_reanalysis = []
    if result.decision.action is DecisionAction.REQUEST_MORE_DATA:
        requested_reanalysis.append(
            "Provide the missing or unverifiable evidence and run a new "
            "immutable analysis round."
        )

    final_decision = _ui_decision(result.decision.action)
    policy_descriptions = [
        rule.description for rule in result.decision.policy_rules
    ]
    policy_reason = " ".join(policy_descriptions) or (
        "The deterministic policy engine accepted the unanimous specialist "
        "assessment."
    )
    created_at = datetime.now(timezone.utc).isoformat()

    return {
        "case_id": case_id,
        "applicant": {
            **payload.applicant.model_dump(
                exclude={"document_text"},
                mode="json",
            ),
            "document_text": "",
        },
        "status": final_decision,
        "specialist_reports": reports,
        "manager_report": {
            "recommendation": _ui_recommendation(
                result.manager_report.proposed_action
            ),
            "disagreements": disagreement,
            "requested_reanalysis": requested_reanalysis,
            "reviewer_summary": result.manager_report.summary,
            "readable_explanation": policy_reason,
            "analysis_round_id": result.analysis_round.round_id,
            "assistant_status": result.manager_report.assistant_status.value,
        },
        "policy_decision": {
            "final_decision": final_decision,
            "final_authority": (
                "Deterministic policy engine"
                + (
                    " + authorized human reviewer"
                    if result.review_task is not None
                    else ""
                )
            ),
            "policy_flags": list(result.decision.reason_codes),
            "policy_rules": [
                {
                    "rule_id": rule.rule_id,
                    "description": rule.description,
                }
                for rule in result.decision.policy_rules
            ],
            "requires_human_review": result.review_task is not None,
            "reason": policy_reason,
            "decision_id": result.decision.decision_id,
            "review_id": (
                result.review_task.review_id
                if result.review_task is not None
                else None
            ),
            "finalized": result.decision.finalized,
            "policy_version": result.decision.policy_version,
        },
        "model_runtime": {
            "source": model_source,
            "score_semantics": "adverse_risk",
            "snapshot_id": snapshot.snapshot_id,
            "snapshot_hash": snapshot.content_hash,
            "pii_minimized": True,
        },
        "created_at": created_at,
    }


def modeling_health() -> dict:
    artifact_root = _artifact_root()
    required = (
        artifact_root / "affordability" / "manifest.json",
        artifact_root / "credit_risk" / "manifest.json",
    )
    return {
        "status": "ok",
        "artifact_root": str(artifact_root),
        "trained_artifacts_available": all(path.is_file() for path in required),
        "fallback": "transparent_scorecard",
    }


def _serialize_report(report: AgentReport, model_source: str) -> dict:
    return {
        "agent_name": _AGENT_NAMES[report.agent_id],
        "agent_id": report.agent_id.value,
        "score": report.score,
        "score_semantics": "adverse_risk",
        "calibrated_probability": report.calibrated_probability,
        "confidence": report.confidence,
        "model_version": report.model_version,
        "model_name": report.model_name,
        "model_source": model_source,
        "top_contributors": [
            {
                "feature": contribution.feature,
                "feature_label": _FEATURE_LABELS.get(
                    contribution.feature,
                    contribution.feature.replace("_", " ").title(),
                ),
                "value": contribution.value,
                "impact": contribution.contribution,
                "direction": (
                    "increases risk"
                    if contribution.contribution > 0
                    else (
                        "reduces risk"
                        if contribution.contribution < 0
                        else "neutral"
                    )
                ),
                "explanation": _contribution_explanation(contribution),
                "reason_code": contribution.reason_code,
            }
            for contribution in report.top_contributors
        ],
        "monotonicity_checks": report.monotonicity_checks.value,
        "evidence_refs": list(report.evidence_refs),
        "reason_codes": list(report.reason_codes),
        "confidence_status": (
            f"{round((report.confidence or 0) * 100)}% model confidence"
        ),
        "recommendation": _ui_recommendation(report.recommendation),
        "summary": _report_summary(report),
        "limitations": list(report.limitations),
        "report_id": report.report_id,
        "analysis_round_id": report.analysis_round_id,
    }


def _contribution_explanation(contribution) -> str:
    label = _FEATURE_LABELS.get(
        contribution.feature,
        contribution.feature.replace("_", " ").title(),
    )
    direction = (
        "raised the estimated adverse risk"
        if contribution.contribution > 0
        else (
            "reduced the estimated adverse risk"
            if contribution.contribution < 0
            else "did not change the estimated adverse risk"
        )
    )
    return f"{label} {direction}; observed value: {contribution.value}."


def _report_summary(report: AgentReport) -> str:
    name = _AGENT_NAMES[report.agent_id]
    risk_percent = round(report.score * 100)
    recommendation = report.recommendation.value.replace("_", " ")
    return (
        f"{name} estimates {risk_percent}% adverse risk and recommends "
        f"{recommendation}."
    )


def _ui_recommendation(recommendation: Recommendation) -> str:
    if recommendation is Recommendation.APPROVE:
        return "APPROVE"
    if recommendation is Recommendation.DECLINE:
        return "REJECT"
    return "REFER"


def _ui_decision(action: DecisionAction) -> str:
    if action is DecisionAction.APPROVE:
        return "APPROVE"
    if action is DecisionAction.DECLINE:
        return "REJECT"
    return "REFER"


def _artifact_root() -> Path:
    configured = os.environ.get("SPENDPILOT_MODEL_ARTIFACT_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parents[3] / "modeling" / "artifacts" / "models"
