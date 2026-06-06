import json

import httpx
import pytest

from spendpilot.agents.manager import ManagerReport
from spendpilot.assistants.local_llama import (
    LlamaCppJSONClient,
    llama_cpp_version,
)
from spendpilot.assistants.structured import StructuredManagerAssistant
from spendpilot.schemas import Recommendation


TEST_SCHEMA = {
    "type": "object",
    "properties": {"summary": {"type": "string"}},
    "required": ["summary"],
    "additionalProperties": False,
}


def test_local_llama_health_and_schema_constrained_completion() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        if request.url.path == "/completion":
            captured["payload"] = json.loads(request.content)
            return httpx.Response(
                200,
                json={
                    "content": '{"summary":"review the evidence"}',
                    "model": "phi-1.5-local",
                },
            )
        raise AssertionError(f"unexpected path: {request.url.path}")

    client = LlamaCppJSONClient(
        client=httpx.Client(transport=httpx.MockTransport(handler))
    )

    assert client.health() is True
    result = client.complete_json(
        system="Return JSON.",
        user='{"reports":[]}',
        max_output_tokens=256,
        json_schema=TEST_SCHEMA,
    )

    assert result.provider == "llama.cpp"
    assert result.model == "phi-1.5-local"
    assert result.latency_ms is not None
    payload = captured["payload"]
    assert payload["json_schema"] == TEST_SCHEMA
    assert payload["temperature"] == 0
    assert payload["n_predict"] == 256
    assert payload["seed"] == 0


def test_local_llama_unavailable_health_and_props() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    client = LlamaCppJSONClient(
        client=httpx.Client(transport=httpx.MockTransport(handler))
    )

    assert client.health() is False
    with pytest.raises(RuntimeError, match="unavailable"):
        client.props()


def test_local_llama_timeout_falls_back_to_runtime_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow model", request=request)

    client = LlamaCppJSONClient(
        client=httpx.Client(transport=httpx.MockTransport(handler))
    )

    with pytest.raises(RuntimeError, match="completion failed"):
        client.complete_json(
            system="Return JSON.",
            user="{}",
            max_output_tokens=256,
            json_schema=TEST_SCHEMA,
        )
    assert client.last_completion_latency_ms is not None


def test_local_llama_rejects_malformed_http_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"content": None})

    client = LlamaCppJSONClient(
        client=httpx.Client(transport=httpx.MockTransport(handler))
    )

    with pytest.raises(ValueError, match="no JSON content"):
        client.complete_json(
            system="Return JSON.",
            user="{}",
            max_output_tokens=256,
            json_schema=TEST_SCHEMA,
        )


def test_local_llama_malformed_json_is_rejected_by_assistant() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"content": "not-json", "model": "phi-1.5-local"},
        )

    client = LlamaCppJSONClient(
        client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    assistant = StructuredManagerAssistant(client)
    manager_report = ManagerReport(
        case_id="case_1",
        snapshot_id="snapshot_1",
        reports=(),
        disagreement=False,
        requires_human_review=False,
        proposed_action=Recommendation.APPROVE,
        reason_codes=("ALL_SPECIALISTS_APPROVE",),
        summary="All specialists approve.",
    )

    with pytest.raises(json.JSONDecodeError):
        assistant.narrate(manager_report, benchmark_context=None)
    assert client.last_completion_latency_ms is not None


def test_llama_cpp_version_accepts_stderr_output(monkeypatch) -> None:
    class Completed:
        stdout = ""
        stderr = (
            "version: 9430 (d48a56eff)\n"
            "built with AppleClang for Darwin arm64\n"
        )

    monkeypatch.setattr(
        "spendpilot.assistants.local_llama.shutil.which",
        lambda executable: f"/opt/homebrew/bin/{executable}",
    )
    monkeypatch.setattr(
        "spendpilot.assistants.local_llama.subprocess.run",
        lambda *args, **kwargs: Completed(),
    )

    assert llama_cpp_version() == (
        "version: 9430 (d48a56eff) | "
        "built with AppleClang for Darwin arm64"
    )
