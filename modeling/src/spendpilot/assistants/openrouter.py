"""OpenRouter client configured for privacy-restricted free routing."""

from __future__ import annotations

import os
from typing import Any

import httpx

from spendpilot.assistants.structured import JSONCompletionResult


OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_FREE_MODEL = "openrouter/free"


class OpenRouterJSONClient:
    """Calls OpenRouter without granting the hosted model decision authority."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = OPENROUTER_FREE_MODEL,
        timeout_seconds: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        resolved_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not resolved_key:
            raise ValueError("OPENROUTER_API_KEY is required")
        self._api_key = resolved_key
        self.model = model
        self._client = client or httpx.Client(timeout=timeout_seconds)

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        max_output_tokens: int,
        json_schema: dict[str, object],
    ) -> JSONCompletionResult:
        response = self._client.post(
            OPENROUTER_ENDPOINT,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "X-OpenRouter-Title": "SpendPilot Modeling",
            },
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0,
                "max_tokens": max_output_tokens,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "spendpilot_manager_output",
                        "strict": True,
                        "schema": json_schema,
                    },
                },
                "provider": {
                    "data_collection": "deny",
                    "zdr": True,
                    "require_parameters": True,
                },
            },
        )
        if response.status_code >= 400:
            raise RuntimeError(
                f"OpenRouter request failed with status {response.status_code}"
            )
        payload = response.json()
        return _completion_result(payload)


def _completion_result(payload: Any) -> JSONCompletionResult:
    if not isinstance(payload, dict):
        raise ValueError("OpenRouter response must be an object")
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("OpenRouter response contains no choices")
    choice = choices[0]
    if not isinstance(choice, dict):
        raise ValueError("OpenRouter choice must be an object")
    message = choice.get("message")
    if not isinstance(message, dict):
        raise ValueError("OpenRouter response contains no message")
    content = message.get("content")
    model = payload.get("model")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("OpenRouter response contains no JSON content")
    if not isinstance(model, str) or not model:
        raise ValueError("OpenRouter response contains no selected model")
    request_id = payload.get("id")
    if request_id is not None and not isinstance(request_id, str):
        request_id = None
    return JSONCompletionResult(
        content=content,
        provider="openrouter",
        model=model,
        request_id=request_id,
    )
