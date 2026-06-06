import json

import httpx
import pytest

from spendpilot.assistants.openrouter import (
    OPENROUTER_ENDPOINT,
    OpenRouterJSONClient,
)

TEST_SCHEMA = {
    "type": "object",
    "properties": {"summary": {"type": "string"}},
    "required": ["summary"],
    "additionalProperties": False,
}


def test_openrouter_uses_free_router_and_privacy_constraints() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers["Authorization"]
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "id": "generation_123",
                "model": "meta-llama/llama-3.3-8b-instruct:free",
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": '{"summary":"ok"}',
                        }
                    }
                ],
            },
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = OpenRouterJSONClient(
        api_key="test-key",
        client=http_client,
    )

    result = client.complete_json(
        system="Return JSON.",
        user='{"input":"safe"}',
        max_output_tokens=256,
        json_schema=TEST_SCHEMA,
    )

    assert result.provider == "openrouter"
    assert result.model == "meta-llama/llama-3.3-8b-instruct:free"
    assert result.request_id == "generation_123"
    assert captured["authorization"] == "Bearer test-key"
    payload = captured["payload"]
    assert payload["model"] == "openrouter/free"
    assert payload["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "spendpilot_manager_output",
            "strict": True,
            "schema": TEST_SCHEMA,
        },
    }
    assert payload["provider"] == {
        "data_collection": "deny",
        "zdr": True,
        "require_parameters": True,
    }


def test_openrouter_requires_an_api_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        OpenRouterJSONClient()


def test_openrouter_error_does_not_expose_response_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == OPENROUTER_ENDPOINT
        return httpx.Response(
            429,
            json={"error": {"message": "sensitive provider detail"}},
        )

    client = OpenRouterJSONClient(
        api_key="test-key",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(RuntimeError, match="status 429") as exc:
        client.complete_json(
            system="Return JSON.",
            user="{}",
            max_output_tokens=20,
            json_schema=TEST_SCHEMA,
        )

    assert "sensitive provider detail" not in str(exc.value)
