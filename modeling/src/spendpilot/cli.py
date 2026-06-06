"""Command-line entry points for reproducible local modeling workflows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from spendpilot.assistants.phi import (
    MLXLocalJSONClient,
    PhiManagerAssistant,
    setup_phi_model,
)
from spendpilot.benchmark import (
    download_south_german_credit,
    run_south_german_benchmark,
)
from spendpilot.demo import run_sample_cases
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
DEFAULT_PHI_PATH = Path("models/phi/Phi-4-mini-instruct-4bit")


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
    if options.command == "setup-phi":
        print(setup_phi_model(options.destination))
        return 0
    if options.command == "demo":
        assistant = None
        if options.with_phi:
            if not options.phi_path.exists():
                parser.error(
                    "Phi model is missing; run "
                    "`python -m spendpilot.cli setup-phi` first"
                )
            assistant = PhiManagerAssistant(
                MLXLocalJSONClient(options.phi_path)
            )
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

    setup_phi = subparsers.add_parser("setup-phi")
    setup_phi.add_argument(
        "--destination",
        type=Path,
        default=DEFAULT_PHI_PATH,
    )

    demo = subparsers.add_parser("demo")
    demo.add_argument("--with-phi", action="store_true")
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
    demo.add_argument("--phi-path", type=Path, default=DEFAULT_PHI_PATH)
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
