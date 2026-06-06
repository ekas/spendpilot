"""Command-line entry points for reproducible local modeling workflows."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from spendpilot.assistants.openrouter import OpenRouterJSONClient
from spendpilot.assistants.smoke import run_local_llm_smoke
from spendpilot.assistants.structured import StructuredManagerAssistant
from spendpilot.benchmark import (
    download_south_german_credit,
    run_south_german_benchmark,
)
from spendpilot.demo import run_external_cases, run_sample_cases
from spendpilot.ingestion import load_external_cases
from spendpilot.reports import generate_explainability_report
from spendpilot.training import (
    SyntheticTrainingConfig,
    train_synthetic_models,
)


DEFAULT_MODEL_ROOT = Path("artifacts/models")
DEFAULT_BENCHMARK_DATA = (
    Path("data/raw/south_german_credit") / "SouthGermanCredit.asc"
)
DEFAULT_BENCHMARK_REPORT = Path(
    "artifacts/reports/south_german_credit.json"
)
DEFAULT_LOCAL_SMOKE_REPORT = Path(
    "artifacts/reports/local-llm-smoke.json"
)
DEFAULT_EXPLAINABILITY_REPORT = Path(
    "artifacts/reports/explainability-demo.html"
)


def main(arguments: list[str] | None = None) -> int:
    parser = _parser()
    options = parser.parse_args(arguments)
    if options.command == "train-synthetic":
        manifests = train_synthetic_models(
            options.output,
            SyntheticTrainingConfig(
                sample_count=options.sample_count,
                seed=options.seed,
                n_estimators=options.n_estimators,
            ),
        )
        print(
            json.dumps(
                [manifest.model_dump(mode="json") for manifest in manifests],
                indent=2,
            )
        )
        return 0
    if options.command == "benchmark-south-german":
        data_path = options.data
        if not data_path.exists():
            data_path = download_south_german_credit(data_path.parent)
        context = run_south_german_benchmark(
            data_path,
            options.report,
        )
        print(context.model_dump_json(indent=2))
        return 0
    if options.command == "demo":
        assistant = None
        if options.with_openrouter:
            try:
                assistant = StructuredManagerAssistant(
                    OpenRouterJSONClient(model=options.openrouter_model)
                )
            except ValueError as exc:
                parser.error(str(exc))
        results = run_sample_cases(
            options.model_root,
            assistant=assistant,
            benchmark_report_path=options.benchmark_report,
        )
        print(
            json.dumps(
                [result.model_dump(mode="json") for result in results],
                indent=2,
            )
        )
        return 0
    if options.command == "evaluate-input":
        requests = load_external_cases(options.input)
        results = run_external_cases(
            options.model_root,
            requests,
            benchmark_report_path=options.benchmark_report,
        )
        print(
            json.dumps(
                [result.model_dump(mode="json") for result in results],
                indent=2,
            )
        )
        return 0
    if options.command == "local-llm-smoke":
        if options.gguf_path is None:
            parser.error(
                "--gguf-path or SPENDPILOT_GGUF_PATH is required"
            )
        report = run_local_llm_smoke(
            gguf_path=options.gguf_path,
            model_root=options.model_root,
            benchmark_report_path=options.benchmark_report,
            output_path=options.output,
            host=options.host,
            port=options.port,
        )
        print(report.model_dump_json(indent=2))
        return 0
    if options.command == "explainability-report":
        output = generate_explainability_report(
            model_root=options.model_root,
            benchmark_report_path=options.benchmark_report,
            smoke_report_path=options.smoke_report,
            output_path=options.output,
            input_path=options.input,
        )
        print(output.resolve())
        return 0
    parser.error("a command is required")
    return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m spendpilot.cli")
    subparsers = parser.add_subparsers(dest="command")

    train = subparsers.add_parser("train-synthetic")
    train.add_argument("--output", type=Path, default=DEFAULT_MODEL_ROOT)
    train.add_argument("--sample-count", type=int, default=25_000)
    train.add_argument("--seed", type=int, default=20_260_606)
    train.add_argument("--n-estimators", type=int, default=140)

    benchmark = subparsers.add_parser("benchmark-south-german")
    benchmark.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_BENCHMARK_DATA,
    )
    benchmark.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_BENCHMARK_REPORT,
    )

    demo = subparsers.add_parser("demo")
    demo.add_argument("--with-openrouter", action="store_true")
    demo.add_argument(
        "--openrouter-model",
        default="openrouter/free",
    )
    demo.add_argument(
        "--model-root",
        type=Path,
        default=DEFAULT_MODEL_ROOT,
    )
    demo.add_argument(
        "--benchmark-report",
        type=Path,
        default=DEFAULT_BENCHMARK_REPORT,
    )

    external = subparsers.add_parser("evaluate-input")
    external.add_argument("--input", type=Path, required=True)
    external.add_argument(
        "--model-root",
        type=Path,
        default=DEFAULT_MODEL_ROOT,
    )
    external.add_argument(
        "--benchmark-report",
        type=Path,
        default=DEFAULT_BENCHMARK_REPORT,
    )

    smoke = subparsers.add_parser("local-llm-smoke")
    smoke.add_argument(
        "--gguf-path",
        type=Path,
        default=(
            Path(os.environ["SPENDPILOT_GGUF_PATH"])
            if os.environ.get("SPENDPILOT_GGUF_PATH")
            else None
        ),
    )
    smoke.add_argument(
        "--model-root",
        type=Path,
        default=DEFAULT_MODEL_ROOT,
    )
    smoke.add_argument(
        "--benchmark-report",
        type=Path,
        default=DEFAULT_BENCHMARK_REPORT,
    )
    smoke.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_LOCAL_SMOKE_REPORT,
    )
    smoke.add_argument("--host", default="127.0.0.1")
    smoke.add_argument("--port", type=int, default=8080)

    explainability = subparsers.add_parser("explainability-report")
    explainability.add_argument(
        "--model-root",
        type=Path,
        default=DEFAULT_MODEL_ROOT,
    )
    explainability.add_argument(
        "--benchmark-report",
        type=Path,
        default=DEFAULT_BENCHMARK_REPORT,
    )
    explainability.add_argument(
        "--smoke-report",
        type=Path,
        default=DEFAULT_LOCAL_SMOKE_REPORT,
    )
    explainability.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_EXPLAINABILITY_REPORT,
    )
    explainability.add_argument(
        "--input",
        type=Path,
        help="Optional external JSON case or case batch.",
    )
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
