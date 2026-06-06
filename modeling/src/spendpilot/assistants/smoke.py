"""Real local-model probes that remain outside decision authority."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from spendpilot.assistants.local_llama import (
    LlamaCppJSONClient,
    LlamaCppServer,
    llama_cpp_version,
)
from spendpilot.assistants.structured import StructuredManagerAssistant
from spendpilot.demo import run_sample_cases
from spendpilot.schemas import (
    AgentId,
    FeedbackEvent,
    FeedbackSource,
    FeedbackType,
    LocalLLMProbe,
    LocalLLMProbePurpose,
    LocalLLMSmokeReport,
    VerificationStatus,
)


def run_local_llm_smoke(
    *,
    gguf_path: Path | str,
    model_root: Path | str,
    benchmark_report_path: Path | str,
    output_path: Path | str,
    host: str = "127.0.0.1",
    port: int = 8080,
) -> LocalLLMSmokeReport:
    """Start llama.cpp, run structured probes, and persist an audit report."""

    model_path = Path(gguf_path).expanduser().resolve()
    started_at = datetime.now(timezone.utc)
    with LlamaCppServer(
        model_path=model_path,
        host=host,
        port=port,
        context_size=2_048,
        parallel=1,
    ) as server:
        client = LlamaCppJSONClient(base_url=server.base_url)
        props = client.props()
        probes = evaluate_local_assistant(
            client=client,
            model_root=model_root,
            benchmark_report_path=benchmark_report_path,
        )
        model_name = str(props.get("model_alias", model_path.stem))

    successes = sum(probe.success for probe in probes)
    success_rate = successes / len(probes)
    report = LocalLLMSmokeReport(
        model_name=model_name,
        model_file=model_path.name,
        model_path_hash=f"sha256:{_sha256_text(str(model_path))}",
        artifact_hash=f"sha256:{_sha256(model_path)}",
        llama_cpp_version=llama_cpp_version(),
        endpoint=f"http://{host}:{port}",
        context_size=2_048,
        max_output_tokens=256,
        experimental=True,
        promoted=False,
        started_at=started_at,
        probes=probes,
        success_rate=success_rate,
        recommendation=(
            "Structured probes passed, but Phi-1.5 remains experimental and "
            "must not receive decision authority."
            if success_rate == 1.0
            else "Structured output was unreliable. Keep deterministic "
            "fallback and prefer Phi-4-mini-instruct Q4_K_M."
        ),
    )
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report.model_dump_json(indent=2) + "\n")
    return report


def evaluate_local_assistant(
    *,
    client: LlamaCppJSONClient,
    model_root: Path | str,
    benchmark_report_path: Path | str,
) -> tuple[LocalLLMProbe, ...]:
    """Evaluate narratives and one routing proposal against real reports."""

    assistant = StructuredManagerAssistant(client)
    results = run_sample_cases(
        model_root,
        benchmark_report_path=benchmark_report_path,
    )
    probes: list[LocalLLMProbe] = []
    for result in results:
        try:
            narrative = assistant.narrate(
                result.manager_report,
                benchmark_context=None,
            )
        except Exception as exc:
            probes.append(
                _failed_probe(
                    purpose=LocalLLMProbePurpose.NARRATIVE,
                    case_id=result.analysis_round.case_id,
                    error=exc,
                    latency_ms=client.last_completion_latency_ms,
                )
            )
        else:
            probes.append(
                LocalLLMProbe(
                    purpose=LocalLLMProbePurpose.NARRATIVE,
                    case_id=result.analysis_round.case_id,
                    success=True,
                    schema_valid=True,
                    latency_ms=narrative.assistant_latency_ms,
                    narrative=narrative,
                )
            )

    routing_result = results[1]
    affordability_report = next(
        report
        for report in routing_result.reports
        if report.agent_id is AgentId.AFFORDABILITY
    )
    feedback = FeedbackEvent(
        feedback_id="local_smoke_feedback",
        case_id=routing_result.analysis_round.case_id,
        source=FeedbackSource.REVIEWER,
        feedback_type=FeedbackType.DATA_CORRECTION,
        rationale="Rationale is intentionally excluded from the model prompt.",
        evidence_refs=affordability_report.evidence_refs[:1],
        related_report_ids=(affordability_report.report_id,),
        submitter_ref="local_smoke_reviewer",
        verification_status=VerificationStatus.VERIFIED,
        verified_by="local_smoke_verifier",
        verified_at=datetime.now(timezone.utc),
    )
    try:
        proposal = assistant.propose_feedback_routing(
            feedback=feedback,
            previous_reports=routing_result.reports,
            allowed_targets=frozenset(AgentId),
        )
    except Exception as exc:
        probes.append(
            _failed_probe(
                purpose=LocalLLMProbePurpose.FEEDBACK_ROUTING,
                case_id=routing_result.analysis_round.case_id,
                error=exc,
                latency_ms=client.last_completion_latency_ms,
            )
        )
    else:
        probes.append(
            LocalLLMProbe(
                purpose=LocalLLMProbePurpose.FEEDBACK_ROUTING,
                case_id=routing_result.analysis_round.case_id,
                success=True,
                schema_valid=True,
                latency_ms=proposal.assistant_latency_ms,
                routing_proposal=proposal,
            )
        )
    return tuple(probes)


def load_local_llm_smoke(path: Path | str) -> LocalLLMSmokeReport:
    """Load an ignored smoke artifact for visualization."""

    return LocalLLMSmokeReport.model_validate_json(Path(path).read_text())


def _failed_probe(
    *,
    purpose: LocalLLMProbePurpose,
    case_id: str,
    error: Exception,
    latency_ms: float | None = None,
) -> LocalLLMProbe:
    return LocalLLMProbe(
        purpose=purpose,
        case_id=case_id,
        success=False,
        schema_valid=False,
        latency_ms=latency_ms,
        fallback_reason=(
            f"{type(error).__name__}: {str(error)[:240]}"
        ),
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()
