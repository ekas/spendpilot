"""Local llama.cpp runtime for experimental GGUF manager assistance."""

from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path
from types import TracebackType
from typing import Any
from uuid import uuid4

import httpx

from spendpilot.assistants.structured import JSONCompletionResult


class LlamaCppJSONClient:
    """Calls a local llama.cpp completion endpoint with a JSON schema."""

    def __init__(
        self,
        *,
        base_url: str = "http://127.0.0.1:8080",
        timeout_seconds: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(timeout=timeout_seconds)
        self.last_completion_latency_ms: float | None = None

    def health(self) -> bool:
        try:
            response = self._client.get(f"{self.base_url}/health")
        except httpx.RequestError:
            return False
        if response.status_code != 200:
            return False
        try:
            return response.json().get("status") == "ok"
        except (ValueError, AttributeError):
            return False

    def props(self) -> dict[str, Any]:
        try:
            response = self._client.get(f"{self.base_url}/props")
        except httpx.RequestError as exc:
            raise RuntimeError("local llama.cpp server is unavailable") from exc
        if response.status_code != 200:
            raise RuntimeError(
                f"llama.cpp props request failed with status "
                f"{response.status_code}"
            )
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("llama.cpp props response must be an object")
        return payload

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        max_output_tokens: int,
        json_schema: dict[str, object],
    ) -> JSONCompletionResult:
        prompt = (
            "Instruction:\n"
            f"{system}\n\n"
            "Validated input JSON:\n"
            f"{user}\n\n"
            "Return only the requested JSON object:\n"
        )
        started = time.perf_counter()
        self.last_completion_latency_ms = None
        try:
            response = self._client.post(
                f"{self.base_url}/completion",
                json={
                    "prompt": prompt,
                    "n_predict": max_output_tokens,
                    "temperature": 0,
                    "seed": 0,
                    "cache_prompt": True,
                    "json_schema": json_schema,
                },
            )
        except httpx.RequestError as exc:
            self.last_completion_latency_ms = (
                time.perf_counter() - started
            ) * 1_000
            raise RuntimeError("local llama.cpp completion failed") from exc
        latency_ms = (time.perf_counter() - started) * 1_000
        self.last_completion_latency_ms = latency_ms
        if response.status_code != 200:
            raise RuntimeError(
                f"llama.cpp completion failed with status "
                f"{response.status_code}"
            )
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("llama.cpp completion response must be an object")
        content = payload.get("content")
        model = payload.get("model")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("llama.cpp response contains no JSON content")
        if not isinstance(model, str) or not model:
            model = str(self.props().get("model_alias", "local-gguf"))
        return JSONCompletionResult(
            content=content,
            provider="llama.cpp",
            model=model,
            request_id=f"local_{uuid4().hex}",
            latency_ms=latency_ms,
        )


class LlamaCppServer:
    """Starts one private llama.cpp server and guarantees cleanup."""

    def __init__(
        self,
        *,
        model_path: Path | str,
        host: str = "127.0.0.1",
        port: int = 8080,
        context_size: int = 2_048,
        parallel: int = 1,
        executable: str = "llama-server",
        startup_timeout_seconds: float = 60.0,
        log_path: Path | str | None = None,
    ) -> None:
        self.model_path = Path(model_path).expanduser().resolve()
        self.host = host
        self.port = port
        self.context_size = context_size
        self.parallel = parallel
        self.executable = executable
        self.startup_timeout_seconds = startup_timeout_seconds
        self.log_path = (
            Path(log_path)
            if log_path is not None
            else Path("artifacts/logs/llama-server.log")
        )
        self.process: subprocess.Popen[str] | None = None
        self._log_handle = None

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def __enter__(self) -> "LlamaCppServer":
        if not self.model_path.is_file():
            raise FileNotFoundError(f"GGUF model not found: {self.model_path}")
        resolved_executable = shutil.which(self.executable)
        if resolved_executable is None:
            raise FileNotFoundError(
                "llama-server is not installed; run `brew install llama.cpp`"
            )
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._log_handle = self.log_path.open("w")
        self.process = subprocess.Popen(
            [
                resolved_executable,
                "-m",
                str(self.model_path),
                "--host",
                self.host,
                "--port",
                str(self.port),
                "--ctx-size",
                str(self.context_size),
                "--parallel",
                str(self.parallel),
                "--n-gpu-layers",
                "99",
                "--no-warmup",
                "--no-webui",
                "--cache-ram",
                "0",
                "--alias",
                self.model_path.stem,
            ],
            stdout=self._log_handle,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            self._wait_until_ready()
        except Exception:
            self._stop()
            raise
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_type, exc_value, traceback
        self._stop()

    def _stop(self) -> None:
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        if self._log_handle is not None:
            self._log_handle.close()
            self._log_handle = None

    def _wait_until_ready(self) -> None:
        assert self.process is not None
        deadline = time.monotonic() + self.startup_timeout_seconds
        client = LlamaCppJSONClient(
            base_url=self.base_url,
            timeout_seconds=1.0,
        )
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError(
                    "llama-server exited before becoming healthy; "
                    f"see {self.log_path}"
                )
            if client.health():
                return
            time.sleep(0.25)
        raise TimeoutError(
            "llama-server did not become healthy before the startup timeout"
        )


def llama_cpp_version(executable: str = "llama-server") -> str:
    """Return stable llama.cpp build metadata."""

    resolved = shutil.which(executable)
    if resolved is None:
        raise FileNotFoundError("llama-server is not installed")
    completed = subprocess.run(
        [resolved, "--version"],
        check=True,
        capture_output=True,
        text=True,
    )
    output = "\n".join((completed.stdout, completed.stderr))
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    return " | ".join(lines[:2])
