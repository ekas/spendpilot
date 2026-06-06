"""Deterministic and versioned credit decision policy."""

from uuid import uuid4

from spendpilot.agents.manager import ManagerReport
from spendpilot.orchestration.human_review import (
    HumanReviewAction,
    HumanReviewResolution,
)
from spendpilot.schemas.agent_report import CheckStatus, Recommendation
from spendpilot.schemas.decision import (
    DecisionAction,
    DecisionRecord,
    PolicyRuleHit,
)


ACTION_MAP = {
    Recommendation.APPROVE: DecisionAction.APPROVE,
    Recommendation.DECLINE: DecisionAction.DECLINE,
    Recommendation.REFER: DecisionAction.REFER,
    Recommendation.REQUEST_MORE_DATA: DecisionAction.REQUEST_MORE_DATA,
}


class PolicyEngine:
    """The only component authorized to create a decision record."""

    def __init__(
        self,
        *,
        policy_version: str = "consumer-credit-v1",
        minimum_confidence: float = 0.60,
    ) -> None:
        if not 0 <= minimum_confidence <= 1:
            raise ValueError("minimum_confidence must be between 0 and 1")
        self.policy_version = policy_version
        self.minimum_confidence = minimum_confidence

    def evaluate(
        self,
        manager_report: ManagerReport,
        human_resolution: HumanReviewResolution | None = None,
    ) -> DecisionRecord:
        rules = self._base_rules(manager_report)
        review_required = manager_report.requires_human_review or bool(rules)

        if human_resolution is not None:
            action, finalized, human_rule = self._apply_human_resolution(
                manager_report,
                human_resolution,
            )
            rules.append(human_rule)
            review_id = human_resolution.review_id
        elif review_required:
            action = self._review_action(manager_report, rules)
            finalized = False
            review_id = None
            rules.append(
                PolicyRuleHit(
                    rule_id="HUMAN_REVIEW_REQUIRED",
                    description="Policy requires an authorized human resolution.",
                )
            )
        else:
            action = DecisionAction.APPROVE
            finalized = True
            review_id = None
            rules.append(
                PolicyRuleHit(
                    rule_id="UNANIMOUS_AUTOMATIC_APPROVAL",
                    description=(
                        "All required specialist reports recommend approval "
                        "and no model guardrail triggered."
                    ),
                )
            )

        return DecisionRecord(
            decision_id=f"decision_{uuid4().hex}",
            case_id=manager_report.case_id,
            snapshot_id=manager_report.snapshot_id,
            policy_version=self.policy_version,
            action=action,
            reason_codes=self._decision_reasons(
                manager_report=manager_report,
                rules=rules,
                human_resolution=human_resolution,
            ),
            report_ids=tuple(
                report.report_id for report in manager_report.reports
            ),
            policy_rules=tuple(rules),
            human_review_id=review_id,
            finalized=finalized,
        )

    def _base_rules(self, manager_report: ManagerReport) -> list[PolicyRuleHit]:
        rules: list[PolicyRuleHit] = []
        if manager_report.missing_agents:
            rules.append(
                PolicyRuleHit(
                    rule_id="INCOMPLETE_REPORT_SET",
                    description="One or more required specialist reports are missing.",
                )
            )
        if manager_report.disagreement:
            rules.append(
                PolicyRuleHit(
                    rule_id="MATERIAL_AGENT_DISAGREEMENT",
                    description="Specialist recommendations do not agree.",
                )
            )
        if any(
            report.monotonicity_checks is CheckStatus.FAILED
            for report in manager_report.reports
        ):
            rules.append(
                PolicyRuleHit(
                    rule_id="MONOTONICITY_CHECK_FAILED",
                    description="A specialist model failed a monotonicity check.",
                )
            )
        if any(
            report.confidence is not None
            and report.confidence < self.minimum_confidence
            for report in manager_report.reports
        ):
            rules.append(
                PolicyRuleHit(
                    rule_id="LOW_MODEL_CONFIDENCE",
                    description="A specialist confidence is below policy threshold.",
                )
            )
        return rules

    @staticmethod
    def _review_action(
        manager_report: ManagerReport,
        rules: list[PolicyRuleHit],
    ) -> DecisionAction:
        rule_ids = {rule.rule_id for rule in rules}
        if "INCOMPLETE_REPORT_SET" in rule_ids:
            return DecisionAction.REQUEST_MORE_DATA
        return ACTION_MAP[manager_report.proposed_action]

    @staticmethod
    def _apply_human_resolution(
        manager_report: ManagerReport,
        resolution: HumanReviewResolution,
    ) -> tuple[DecisionAction, bool, PolicyRuleHit]:
        if resolution.action is HumanReviewAction.OVERRIDE_DECISION:
            assert resolution.override_action is not None
            action = resolution.override_action
            finalized = action in {
                DecisionAction.APPROVE,
                DecisionAction.DECLINE,
            }
        elif resolution.action is HumanReviewAction.APPROVE_RECOMMENDATION:
            action = ACTION_MAP[manager_report.proposed_action]
            finalized = action in {
                DecisionAction.APPROVE,
                DecisionAction.DECLINE,
            }
        elif resolution.action is HumanReviewAction.REQUEST_MORE_DATA:
            action = DecisionAction.REQUEST_MORE_DATA
            finalized = False
        else:
            action = DecisionAction.REFER
            finalized = False

        return (
            action,
            finalized,
            PolicyRuleHit(
                rule_id="HUMAN_RESOLUTION_APPLIED",
                description=(
                    f"Reviewer action {resolution.action.value} was applied "
                    "by the policy engine."
                ),
            ),
        )

    @staticmethod
    def _decision_reasons(
        *,
        manager_report: ManagerReport,
        rules: list[PolicyRuleHit],
        human_resolution: HumanReviewResolution | None,
    ) -> tuple[str, ...]:
        reasons = list(manager_report.reason_codes)
        for rule in rules:
            if rule.rule_id not in reasons:
                reasons.append(rule.rule_id)
        if human_resolution is not None:
            human_reason = f"HUMAN_{human_resolution.action.value.upper()}"
            if human_reason not in reasons:
                reasons.append(human_reason)
        return tuple(reasons)
