from __future__ import annotations

import os
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.models.modeling import ModelingAnalysisRequest
from spendpilot.demo import build_runtime_workflow
from spendpilot.ingestion import BackendApplicant, BackendInputAdapter
from spendpilot.schemas.agent_report import AgentId, AgentReport, Recommendation
from spendpilot.schemas.case import CaseSnapshot
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
    adapter = BackendInputAdapter()
    snapshot = adapter.to_snapshot(
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
    submitted_data = _submitted_data(payload)
    derived_features = _derived_features(snapshot)
    evidence = _evidence_summary(snapshot, payload)
    counterfactuals = _counterfactuals(
        workflow=workflow,
        adapter=adapter,
        snapshot=snapshot,
        original_result=result,
        model_source=model_source,
    )
    case_context = {
        "case_id": case_id,
        "snapshot_id": snapshot.snapshot_id,
        "snapshot_hash": snapshot.content_hash,
        "analysis_round_id": result.analysis_round.round_id,
        "decision_id": result.decision.decision_id,
        "applicant_ref": snapshot.applicant_ref,
        "currency": "EUR",
        "created_at": created_at,
    }
    manager_report = {
        "recommendation": _ui_recommendation(
            result.manager_report.proposed_action
        ),
        "disagreement": result.manager_report.disagreement,
        "disagreements": disagreement,
        "requested_reanalysis": requested_reanalysis,
        "reviewer_summary": result.manager_report.summary,
        "readable_explanation": policy_reason,
        "analysis_round_id": result.analysis_round.round_id,
        "assistant_status": result.manager_report.assistant_status.value,
        "requires_human_review": result.manager_report.requires_human_review,
        "reason_codes": list(result.manager_report.reason_codes),
    }
    policy_decision = {
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
    }
    model_runtime = {
        "source": model_source,
        "score_semantics": "adverse_risk",
        "snapshot_id": snapshot.snapshot_id,
        "snapshot_hash": snapshot.content_hash,
        "pii_minimized": True,
    }
    audit_bundle = _audit_bundle(
        case_context=case_context,
        snapshot=snapshot,
        submitted_data=submitted_data,
        derived_features=derived_features,
        evidence=evidence,
        reports=reports,
        manager_report=manager_report,
        policy_decision=policy_decision,
        counterfactuals=counterfactuals,
        model_runtime=model_runtime,
        generated_at=created_at,
    )

    return {
        "case_id": case_id,
        "applicant": {
            **payload.applicant.model_dump(
                exclude={"documents", "document_text", "document_signals"},
                mode="json",
            ),
            "documents": [],
            "document_text": "",
            "document_signals": {},
        },
        "status": final_decision,
        "case_context": case_context,
        "submitted_data": submitted_data,
        "derived_features": derived_features,
        "evidence": evidence,
        "specialist_reports": reports,
        "manager_report": manager_report,
        "policy_decision": policy_decision,
        "counterfactuals": counterfactuals,
        "model_runtime": model_runtime,
        "audit_bundle": audit_bundle,
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
        "model_source": (
            "deterministic_rules"
            if report.agent_id is AgentId.CREDIBILITY
            else model_source
        ),
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
                "evidence_refs": list(contribution.evidence_refs),
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


def _submitted_data(payload: ModelingAnalysisRequest) -> dict:
    applicant = payload.applicant
    return {
        "monthly_income": applicant.monthly_income,
        "monthly_expenses": applicant.monthly_expenses,
        "requested_amount": applicant.requested_amount,
        "existing_debt": applicant.existing_debt,
        "credit_utilization": applicant.credit_utilization,
        "delinquencies_12m": applicant.delinquencies_12m,
        "employment_months": applicant.employment_months,
        "overdrafts_90d": applicant.overdrafts_90d,
        "income_verified": applicant.income_verified,
    }


def _derived_features(snapshot: CaseSnapshot) -> dict:
    features = snapshot.features
    income = _optional_number(features.get("monthly_income"))
    expenses = _optional_number(features.get("monthly_expenses"))
    debt = _optional_number(features.get("existing_debt"))
    requested = float(snapshot.requested_amount)
    free_cash_flow = (
        income - expenses
        if income is not None and expenses is not None
        else None
    )
    installment = requested / 36
    return {
        "effective_monthly_income": income,
        "effective_monthly_expenses": expenses,
        "effective_existing_debt": debt,
        "effective_credit_utilization": _optional_number(
            features.get("credit_utilization")
        ),
        "effective_delinquencies_12m": _optional_number(
            features.get("delinquencies_12m")
        ),
        "effective_employment_months": _optional_number(
            features.get("employment_months")
        ),
        "free_cash_flow": free_cash_flow,
        "expense_ratio": (
            expenses / income if income and expenses is not None else None
        ),
        "debt_to_monthly_income": (
            debt / income if income and debt is not None else None
        ),
        "estimated_installment_36m": installment,
        "installment_burden": (
            installment / max(free_cash_flow, 1)
            if free_cash_flow is not None
            else None
        ),
    }


def _evidence_summary(
    snapshot: CaseSnapshot,
    payload: ModelingAnalysisRequest,
) -> dict:
    features = snapshot.features
    flags = payload.applicant.document_signals.get(
        "consistency_flags", []
    )
    if not isinstance(flags, list):
        flags = []
    unreadable = payload.applicant.document_signals.get(
        "unreadable_files", []
    )
    if not isinstance(unreadable, list):
        unreadable = []
    coverage_available = (
        "coverage_score" in payload.applicant.document_signals
    )
    return {
        "document_count": int(features.get("document_count") or 0),
        "evidence_refs": list(snapshot.evidence_refs),
        "coverage_score": (
            _optional_number(features.get("document_coverage_score"))
            if coverage_available
            else None
        ),
        "missing_documents": list(snapshot.missing_fields),
        "consistency_findings": [
            str(flag).replace("_", " ").title() for flag in flags
        ],
        "consistency_flag_count": int(
            features.get("document_consistency_flag_count") or 0
        ),
        "unreadable_document_count": len(unreadable),
        "verification_state": (
            "verified"
            if bool(features.get("income_verified"))
            else "unverified"
        ),
        "income_verified": bool(features.get("income_verified")),
    }


def _counterfactuals(
    *,
    workflow,
    adapter: BackendInputAdapter,
    snapshot: CaseSnapshot,
    original_result,
    model_source: str,
) -> list[dict]:
    features = snapshot.features
    income = _optional_number(features.get("monthly_income"))
    expenses = _optional_number(features.get("monthly_expenses"))
    candidates: list[tuple[str, str, str, dict[str, Any]]] = []
    utilization = _optional_number(features.get("credit_utilization"))
    if utilization is not None and utilization > 0.30:
        candidates.append(
            (
                "reduce_credit_utilization",
                "Reduce credit utilization to 30%",
                "Assumes revolving balances can be reduced without new debt.",
                {"credit_utilization": 0.30},
            )
        )
    expense_target = income * 0.70 if income is not None else None
    if (
        expense_target is not None
        and expenses is not None
        and expenses > expense_target
    ):
        candidates.append(
            (
                "reduce_monthly_expenses",
                "Reduce monthly expenses to 70% of income",
                "Assumes the lower expense level is sustainable and verified.",
                {"monthly_expenses": expense_target},
            )
        )
    if not bool(features.get("income_verified")):
        candidates.append(
            (
                "verify_income",
                "Verify submitted income",
                "Assumes acceptable evidence independently verifies income.",
                {"income_verified": True},
            )
        )
    overdrafts = _optional_number(features.get("overdrafts_90d"))
    if overdrafts is not None and overdrafts > 0:
        candidates.append(
            (
                "remove_recent_overdrafts",
                "Reduce recent overdrafts to zero",
                "Assumes a later observation window contains no overdrafts.",
                {"overdrafts_90d": 0},
            )
        )

    original_scores = {
        report.agent_id.value: report.score
        for report in original_result.reports
    }
    original_average = sum(original_scores.values()) / len(original_scores)
    scenarios = []
    for index, (scenario_id, label, assumption, updates) in enumerate(
        candidates, start=1
    ):
        hypothetical = adapter.revise_snapshot(
            snapshot,
            snapshot_id=f"{snapshot.snapshot_id}_hyp_{index}",
            feature_updates=updates,
        )
        scenario_result = workflow.run(hypothetical)
        scenario_scores = {
            report.agent_id.value: report.score
            for report in scenario_result.reports
        }
        scenario_average = sum(scenario_scores.values()) / len(scenario_scores)
        changes = [
            {
                "field": field,
                "original_value": features.get(field),
                "hypothetical_value": value,
            }
            for field, value in updates.items()
        ]
        scenarios.append(
            {
                "scenario_id": scenario_id,
                "label": label,
                "hypothetical": True,
                "persisted": False,
                "assumption": assumption,
                "changed_fields": changes,
                "specialist_deltas": [
                    {
                        "agent_id": agent_id,
                        "original_risk": original_scores[agent_id],
                        "hypothetical_risk": scenario_scores[agent_id],
                        "risk_delta": (
                            scenario_scores[agent_id]
                            - original_scores[agent_id]
                        ),
                    }
                    for agent_id in sorted(original_scores)
                ],
                "original_average_risk": original_average,
                "hypothetical_average_risk": scenario_average,
                "overall_risk_delta": scenario_average - original_average,
                "risk_reduction": original_average - scenario_average,
                "original_policy_outcome": _ui_decision(
                    original_result.decision.action
                ),
                "hypothetical_policy_outcome": _ui_decision(
                    scenario_result.decision.action
                ),
                "original_requires_review": (
                    original_result.review_task is not None
                ),
                "hypothetical_requires_review": (
                    scenario_result.review_task is not None
                ),
                "model_source": model_source,
            }
        )
    return sorted(
        (
            scenario
            for scenario in scenarios
            if scenario["risk_reduction"] > 0
        ),
        key=lambda scenario: scenario["risk_reduction"],
        reverse=True,
    )[:3]


def _audit_bundle(
    *,
    case_context: dict,
    snapshot: CaseSnapshot,
    submitted_data: dict,
    derived_features: dict,
    evidence: dict,
    reports: list[dict],
    manager_report: dict,
    policy_decision: dict,
    counterfactuals: list[dict],
    model_runtime: dict,
    generated_at: str,
) -> dict:
    return {
        "schema_version": "spendpilot-underwriting-audit-v1",
        "generated_at": generated_at,
        "identifiers": case_context,
        "sanitized_snapshot": {
            "case_id": snapshot.case_id,
            "snapshot_id": snapshot.snapshot_id,
            "applicant_ref": snapshot.applicant_ref,
            "product": snapshot.product.value,
            "requested_amount": float(snapshot.requested_amount),
            "currency": snapshot.currency,
            "content_hash": snapshot.content_hash,
            "features": snapshot.features,
            "evidence_refs": list(snapshot.evidence_refs),
            "missing_fields": list(snapshot.missing_fields),
        },
        "submitted_data": submitted_data,
        "derived_features": derived_features,
        "evidence": evidence,
        "specialist_reports": reports,
        "manager_report": manager_report,
        "policy_trace": policy_decision,
        "counterfactuals": counterfactuals,
        "model_provenance": _model_provenance(reports),
        "model_runtime": model_runtime,
        "limitations": [
            "Affordability and credit-risk models were trained on synthetic data.",
            "The South German Credit dataset is aggregate benchmark evidence only and never scores this applicant.",
            "Counterfactuals are hypothetical reruns, are not persisted, and are not lending decisions.",
            "Production use requires independent validation, fairness review, monitoring, and authorized governance approval.",
        ],
        "human_review": {
            "required": policy_decision["requires_human_review"],
            "review_id": policy_decision["review_id"],
            "finalized": policy_decision["finalized"],
        },
    }


def _model_provenance(reports: list[dict]) -> list[dict]:
    artifact_root = _artifact_root()
    provenance = []
    for report in reports:
        agent_id = report["agent_id"]
        manifest = _read_json(artifact_root / agent_id / "manifest.json")
        validation = _read_json(artifact_root / agent_id / "validation.json")
        provenance.append(
            {
                "agent_id": agent_id,
                "model_name": report["model_name"],
                "model_version": report["model_version"],
                "source": report["model_source"],
                "artifact_hash": manifest.get("artifact_hash"),
                "provenance": manifest.get(
                    "provenance",
                    "deterministic_rules"
                    if agent_id == AgentId.CREDIBILITY.value
                    else "runtime_fallback",
                ),
                "training_config": manifest.get("training_config"),
                "validation_reference": manifest.get(
                    "validation_report_ref"
                ),
                "validation_metrics": validation or None,
            }
        )
    return provenance


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _optional_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


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
