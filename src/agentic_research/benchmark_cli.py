from __future__ import annotations

import argparse
import json
import os

from .benchmark import run_benchmark_suite
from .sample_tasks import SAMPLE_TASKS


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run repeatable benchmark suites for the agentic research project.")
    parser.add_argument(
        "--tasks",
        nargs="+",
        choices=sorted(SAMPLE_TASKS),
        required=True,
        help="One or more task ids to include in the benchmark suite.",
    )
    parser.add_argument(
        "--architectures",
        nargs="+",
        choices=["single", "multi"],
        default=["single", "multi"],
        help="Which architectures to run for each task.",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=1,
        help="How many repeated runs to execute per task and architecture.",
    )
    parser.add_argument(
        "--mode",
        choices=["deterministic", "openai"],
        help="Override AGENTIC_MODE for this benchmark suite.",
    )
    parser.add_argument(
        "--output-dir",
        help="Optional output directory for benchmark artifacts. Defaults to benchmark_runs/<suite-id>.",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    if args.mode:
        os.environ["AGENTIC_MODE"] = args.mode
    result = run_benchmark_suite(
        task_ids=args.tasks,
        repeats=args.repeats,
        architectures=args.architectures,
        output_dir=args.output_dir,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
