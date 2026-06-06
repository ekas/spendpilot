"""Pretrained local Phi assistant with strict JSON-only interfaces."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Protocol

from spendpilot.agents.manager import ManagerReport
from spendpilot.schemas.agent_report import AgentId, AgentReport
from spendpilot.schemas.feedback import FeedbackEvent
from spendpilot.schemas.modeling import (
    BenchmarkContext,
    FeedbackRoutingProposal,
    ManagerNarrative,
)


PHI_REPOSITORY = "mlx-community/Phi-4-mini-instruct-4bit"
MAX_INPUT_TOKENS = 2_048
MAX_OUTPUT_TOKENS = 256


class JSONCompletionClient(Protocol):
    """Minimum completion behavior required by the Phi assistant."""

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        max_output_tokens: int,
    ) -> str:
        """Return one JSON object as text."""


class MLXLocalJSONClient:
    """Loads one 4-bit MLX model and serializes local requests."""

    def __init__(self, model_path: Path | str) -> None:
        from mlx_lm import load

        self._model, self._tokenizer = load(str(model_path))
        self._lock = threading.Lock()

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        max_output_tokens: int = MAX_OUTPUT_TOKENS,
    ) -> str:
        from mlx_lm import generate
        from mlx_lm.sample_utils import make_sampler

        messages = (
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        )
        prompt = self._tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=False,
        )
        if len(self._tokenizer.encode(prompt)) > MAX_INPUT_TOKENS:
            raise ValueError("Phi manager input exceeds 2,048 tokens")
        with self._lock:
            return generate(
                self._model,
                self._tokenizer,
                prompt=prompt,
                max_tokens=min(max_output_tokens, MAX_OUTPUT_TOKENS),
                sampler=make_sampler(temp=0.0),
                verbose=False,
            )


class PhiManagerAssistant:
    """Uses Phi for bounded explanations and feedback-routing proposals."""

    def __init__(self, client: JSONCompletionClient) -> None:
        self._client = client

    def narrate(
        self,
        manager_report: ManagerReport,
        benchmark_context: BenchmarkContext | None,
    ) -> ManagerNarrative:
        payload = {
            "proposed_action": manager_report.proposed_action.value,
            "disagreement": manager_report.disagreement,
            "requires_human_review": manager_report.requires_human_review,
            "reason_codes": manager_report.reason_codes,
            "reports": [
                {
                    "agent_id": report.agent_id.value,
                    "score": report.score,
                    "recommendation": report.recommendation.value,
                    "reason_codes": report.reason_codes,
                    "top_contributors": [
                        {
                            "feature": contribution.feature,
                            "contribution": contribution.contribution,
                            "reason_code": contribution.reason_code,
                            "evidence_refs": contribution.evidence_refs,
                        }
                        for contribution in report.top_contributors
                    ],
                    "limitations": report.limitations,
                }
                for report in manager_report.reports
            ],
            "report_deltas": [
                delta.model_dump(mode="json")
                for delta in manager_report.report_deltas
            ],
            "benchmark_context": (
                benchmark_context.model_dump(mode="json")
                if benchmark_context
                else None
            ),
        }
        response = self._client.complete_json(
            system=(
                "You explain already-computed credit model reports to a human "
                "reviewer. Do not make a credit decision, change scores, or "
                "invent evidence. Return only JSON with keys summary, "
                "disagreement_explanation, reviewer_focus, and limitations. "
                "Do not reveal hidden reasoning."
            ),
            user=json.dumps(payload, separators=(",", ":")),
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )
        return ManagerNarrative.model_validate(_parse_json_object(response))

    def propose_feedback_routing(
        self,
        *,
        feedback: FeedbackEvent,
        previous_reports: tuple[AgentReport, ...],
        allowed_targets: frozenset[AgentId],
    ) -> FeedbackRoutingProposal:
        payload = {
            "feedback_id": feedback.feedback_id,
            "feedback_type": feedback.feedback_type.value,
            "evidence_refs": feedback.evidence_refs,
            "related_report_ids": feedback.related_report_ids,
            "allowed_targets": sorted(target.value for target in allowed_targets),
            "reports": [
                {
                    "report_id": report.report_id,
                    "agent_id": report.agent_id.value,
                    "recommendation": report.recommendation.value,
                    "reason_codes": report.reason_codes,
                }
                for report in previous_reports
            ],
        }
        response = self._client.complete_json(
            system=(
                "Route verified credit-case feedback to relevant specialist "
                "agents. Use only allowed_targets. Do not make a decision, "
                "change a score, or infer facts from free text. Return only "
                "JSON with feedback_id, proposed_targets, and rationale_codes."
            ),
            user=json.dumps(payload, separators=(",", ":")),
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )
        return FeedbackRoutingProposal.model_validate(
            _parse_json_object(response)
        )


def setup_phi_model(destination: Path | str) -> Path:
    """Explicitly download the approved pretrained MLX model."""

    from huggingface_hub import snapshot_download

    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    downloaded = snapshot_download(
        repo_id=PHI_REPOSITORY,
        local_dir=path,
    )
    return Path(downloaded)


def _parse_json_object(text: str) -> dict[str, object]:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines)
    parsed = json.loads(stripped)
    if not isinstance(parsed, dict):
        raise ValueError("Phi response must be one JSON object")
    return parsed
