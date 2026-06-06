"""External research benchmarks that never score SpendPilot applicants."""

from spendpilot.benchmark.south_german import (
    BenchmarkConfig,
    download_south_german_credit,
    load_south_german_credit,
    run_south_german_benchmark,
)

__all__ = [
    "BenchmarkConfig",
    "download_south_german_credit",
    "load_south_german_credit",
    "run_south_german_benchmark",
]
