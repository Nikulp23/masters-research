# Real Repo. Real Fix. Real Test.

Small benchmark harness for comparing a single-agent coding loop against a
multi-agent workflow on real open-source bug-fix tasks.

The repo does not commit benchmark outputs. To reproduce a run, install the
project, create a local `.env`, and run the CLI.

## Setup

```bash
pip install -e .
```

Create `.env` in the repo root:

```bash
AGENTIC_MODE=claude
ANTHROPIC_API_KEY=your_key_here
ANTHROPIC_MODEL=claude-sonnet-4-6
```

Optional per-role overrides:

```bash
ANTHROPIC_ENGINEER_MODEL=claude-sonnet-4-6
ANTHROPIC_REVIEWER_MODEL=claude-sonnet-4-6
ANTHROPIC_COORDINATOR_MODEL=claude-sonnet-4-6
```

Clone the upstream task fixtures:

```bash
python scripts/setup_repos.py
```

## Run

Run one task with the single-agent path:

```bash
PYTHONPATH=src python3 -m agentic_research.cli \
  --architecture single \
  --task requests-netrc-empty-default \
  --mode claude
```

Compare both architectures on one task:

```bash
PYTHONPATH=src python3 -m agentic_research.cli \
  --architecture compare \
  --task requests-netrc-empty-default \
  --mode claude
```

Run a small benchmark suite:

```bash
PYTHONPATH=src python3 -m agentic_research.benchmark_cli \
  --tasks requests-netrc-empty-default click-flag-value-optional \
  --architectures single multi \
  --repeats 1 \
  --mode claude
```

Benchmark output is written locally under `benchmark_runs/`.

## Tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Layout

```text
src/agentic_research/   benchmark code
scripts/setup_repos.py  clone upstream task repositories
tests/                  unit tests
benchmark_runs/         local generated run output, ignored by git
repos/                  local upstream repository cache, ignored by git
```
