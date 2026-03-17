# Research Project

This project compares a `single-agent` baseline and a `multi-agent` workflow on real coding issues.

## In Simple Terms

What this project does:

1. pick a real issue from a real repository
2. clone or copy that repo into a sandbox
3. let a `single-agent` baseline try to fix it
4. let a `multi-agent` workflow try to fix it
5. run real tests
6. compare which system did better

That is the core idea.

## What “working” means

A run counts as working only if:

- the agent edits real code
- the code is written into a sandbox copy of the repo
- the real test command is executed
- the test passes

This is not supposed to be only “the model suggested a solution.”
It is supposed to be:

- real repo
- real code edits
- real tests
- real pass/fail result

## Research Pipeline

The pipeline is now set up to support repeatable experiments:

1. choose one or more tasks
2. run both architectures against the same repo snapshot
3. save a per-run JSON record
4. save a suite-level `manifest.json`, `summary.json`, and `summary.csv`
5. classify failures like:
   - `success`
   - `invalid_patch_payload`
   - `patch_target_mismatch`
   - `patch_application_failed`
   - `llm_budget_exhausted`
   - `test_failed`

This gives you a proper benchmark folder for each suite under `benchmark_runs/`.

## Current Status

The project already has:

- a runnable `single-agent` workflow
- a runnable `multi-agent` workflow with explicit role handoffs
- OpenAI-backed execution
- deterministic fallback mode
- a real local sandbox repo demo
- one real repo issue run against `pallets/click`
- OpenAI model configured via `OPENAI_MODEL` and now defaulting to `gpt-5.2-codex`
- multi-agent LLM call budget can be disabled with `AGENTIC_MULTI_MAX_LLM_CALLS=0` and is now unset by default

## What was already proven

We already ran a real issue-style test:

- repo: `pallets/click`
- issue type: `NO_COLOR` support
- both the `single-agent` baseline and the `multi-agent` workflow edited real code
- both were tested with a real sandboxed unittest
- both passed

This means the project is now doing the right kind of work.

## Main Files

- `index.html`: main project website
- `results.html`: result summary page for real runs
- `styles.css`: shared website styling
- `.env`: local OpenAI config
- `src/agentic_research/`: main code
- `fixtures/no_color_repo/`: local sandbox demo repo
- `tests/test_graphs.py`: automated tests

## Useful Commands

Run tests:

- `PYTHONPATH=src python3 -m unittest discover -s tests -v`

Clean previous benchmark and website data:

- `./clean-data.sh`

Run single-agent:

- `PYTHONPATH=src python3 -m agentic_research.cli --architecture single --task no-color --mode openai`

Run multi-agent:

- `PYTHONPATH=src python3 -m agentic_research.cli --architecture multi --task no-color --mode openai`

Run a real issue comparison:

- `PYTHONPATH=src python3 -m agentic_research.cli --architecture single --task click-no-color-real --mode openai`
- `PYTHONPATH=src python3 -m agentic_research.cli --architecture multi --task click-no-color-real --mode openai`

Run a benchmark suite:

- `PYTHONPATH=src python3 -m agentic_research.benchmark_cli --tasks no-color click-no-color-real --architectures single multi --repeats 2 --mode deterministic`

Export website conversation data:

- `PYTHONPATH=src python3 -m agentic_research.site_export --benchmark-root benchmark_runs --output-dir site-data`

## Safety

- `.env` is local
- API usage is bounded by call limits and iteration limits
- runs happen in sandbox copies, not the original repo
