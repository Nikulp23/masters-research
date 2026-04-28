# Nikul Patel - Master's Project

This repository contains the benchmark harness for my master's project on
single-agent vs. multi-agent LLM coding workflows.

The paper asks:

> Do multi-agent LLM systems fix real software bugs better than single-agent
> systems, and at what cost?

The benchmark runs both architectures on historical open-source bugs. Each task
starts from a pinned buggy commit, injects a regression test, restricts the
editable files, and grades the run with the real test command instead of an LLM
judge. The paper's pilot study found that both workflows reached the same final
success rate on the tested tasks, but the multi-agent workflow made fewer
first-attempt mistakes while using much more token budget.

Generated benchmark outputs are not committed. Running the harness writes local
results under `benchmark_runs/`.

## What Is Here

- `src/agentic_research/cli.py`: run one task with one architecture, or compare both.
- `src/agentic_research/benchmark_cli.py`: run repeatable benchmark suites.
- `src/agentic_research/graphs.py`: LangGraph workflows for the single-agent and multi-agent paths.
- `src/agentic_research/sample_tasks.py`: pinned task specs, base commits, injected tests, and validation commands.
- `src/agentic_research/sandbox.py`: workspace cloning, test injection, dependency setup, and validation.
- `scripts/setup_repos.py`: helper for cloning upstream repositories into `repos/`.
- `tests/`: local unit tests for the harness. These do not call an LLM.

## Requirements

For the harness itself:

- Python 3.11 or newer
- Git
- An Anthropic API key for live Claude runs

For full-suite runs, install the ecosystem tools for the tasks you choose:

- Python tasks: Python and pip
- Go tasks: Go
- Rust tasks: Rust and Cargo
- React/TypeScript tasks: Node.js and npm or pnpm

For the quickest advisor check, use the `requests-netrc-empty-default` task
below. It only needs the Python stack plus the cloned `requests` repository.

## Install

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

`requirements.txt` is also provided for reference, but `pip install -e .` is
the preferred setup because it installs the package entry points.

## Configure Claude

Create a local `.env` file in the repository root:

```bash
AGENTIC_MODE=claude
ANTHROPIC_API_KEY=your_key_here
ANTHROPIC_MODEL=claude-sonnet-4-6
```

Optional per-role model overrides:

```bash
ANTHROPIC_ENGINEER_MODEL=claude-sonnet-4-6
ANTHROPIC_REVIEWER_MODEL=claude-sonnet-4-6
ANTHROPIC_COORDINATOR_MODEL=claude-sonnet-4-6
```

## Prepare One Task Repository

Clone only the `requests` fixture first:

```bash
python scripts/setup_repos.py --repos requests --skip-install
```

The task runner checks out historical base commits. If the checkout fails
because the clone is shallow, fetch the full history for that repository:

```bash
git -C repos/requests fetch --unshallow --tags
```

For more tasks, repeat the same pattern for the relevant repository names, or
run `python scripts/setup_repos.py --skip-install` to clone all configured
repositories. The sandbox creates its own temporary workspace and installs task
dependencies there before validation.

If a task's repository is not listed by `scripts/setup_repos.py`, use
`src/agentic_research/sample_tasks.py` as the source of truth: clone the task's
`repository` URL into its `source_repo_path`, then fetch full history before
running the task.

## Run One Task

Single-agent run:

```bash
agentic-research --architecture single --task requests-netrc-empty-default --mode claude
```

Multi-agent run:

```bash
agentic-research --architecture multi --task requests-netrc-empty-default --mode claude
```

Compare both on the same task:

```bash
agentic-research --architecture compare --task requests-netrc-empty-default --mode claude
```

The command prints a compact JSON result to the terminal.

## Run A Small Benchmark

Example with two Python tasks and both architectures:

```bash
python scripts/setup_repos.py --repos requests click --skip-install
git -C repos/requests fetch --unshallow --tags
git -C repos/click fetch --unshallow --tags

agentic-benchmark --tasks requests-netrc-empty-default click-flag-value-optional --architectures single multi --repeats 1 --mode claude
```

Outputs are written to:

```text
benchmark_runs/<task-folder>/<architecture>/raw/*.json
benchmark_runs/<task-folder>/<architecture>/summary.json
```

## Run Harness Tests

These tests check the harness code and do not require an API key:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Notes For Reproducing The Paper

The paper evaluates the workflow design, not a new model. Both architectures use
the same model, task definitions, editable-file allow-lists, validation
commands, stopping rules, and deterministic test-based grading.

The reported pilot result was:

- Final success tied in the recorded runs.
- Multi-agent had better first-attempt success.
- Multi-agent used substantially more tokens because Coordinator, Analyst,
  Engineer, Tester, and Reviewer each receive repeated task context.

To reproduce a larger slice of the study, prepare the needed upstream
repositories under `repos/`, then pass the desired task IDs to
`agentic-benchmark`.

## Common Issues

- `ModuleNotFoundError: agentic_research`: run from the repo root after
  `pip install -e .`, or prefix commands with `PYTHONPATH=src`.
- `Fixture directory does not exist: repos/<name>`: run `scripts/setup_repos.py`
  for that repository.
- `Failed to checkout base_commit`: run `git -C repos/<name> fetch --unshallow --tags`.
- Missing `ANTHROPIC_API_KEY`: create `.env` or export the variable in your shell.
- JavaScript/Rust/Go task setup errors: install that ecosystem's toolchain, then
  rerun the same benchmark command.
