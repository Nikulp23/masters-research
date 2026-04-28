from __future__ import annotations

import argparse
import json
import os

from .benchmark import compact_result, run_compare_once
from .graphs import run_architecture
from .sample_tasks import SAMPLE_TASKS


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the agentic research prototype.")
    parser.add_argument(
        "--architecture",
        choices=["single", "multi", "compare"],
        default="compare",
        help="Which architecture to run.",
    )
    parser.add_argument(
        "--task",
        choices=sorted(SAMPLE_TASKS),
        default="requests-netrc-empty-default",
        help="Which built-in sample task to run.",
    )
    parser.add_argument(
        "--mode",
        choices=["deterministic", "claude"],
        help="Override AGENTIC_MODE for this run.",
    )
    return parser

def main() -> None:
    args = _build_parser().parse_args()
    if args.mode:
        os.environ["AGENTIC_MODE"] = args.mode
    if args.architecture == "compare":
        output = run_compare_once(args.task)
    else:
        raw = run_architecture(args.architecture, task_id=args.task)
        output = compact_result(raw)
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
