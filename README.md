# Masters Research

## Real Repo. Real Fix. Real Test.

### Single-Agent vs Multi-Agent AI on real coding issues.

This project takes a real issue from a real repository, lets both architectures try to fix it in a sandbox, runs real tests, and compares which one actually did better.

- View Results: `results.html`
- Browse Conversations: `conversations.html`
- See How It Works: `index.html`

## Research Question

### Which architecture performs better on real coding issues?

This project studies whether multi-agent coding systems perform better than single-agent systems on real software-fix tasks.

The project also measures:

- Success rate
- Failure categories
- Latency
- Iteration count
- LLM call usage

## Workflow

### How each experiment works

**01 Choose a real issue**  
Pick an issue from a real open-source Python repository.

**02 Create a sandbox**  
Clone or copy the repo into an isolated workspace so the original source is untouched.

**03 Run both architectures**  
Let the single-agent system and the multi-agent system try to fix the same task.

**04 Run real tests**  
Execute the actual validation command and treat that output as the result.

**05 Compare outcomes**  
Measure success, latency, iterations, revisions, and LLM call usage.

## Architectures

### Single-Agent

The single-agent baseline handles the whole task in one loop. It reads the issue, summarizes the broken behavior, reasons about the likely root cause, proposes a patch, applies that patch in the sandbox, and then checks whether the real test passed.

If the test fails, the same agent gets the failure feedback and tries again until it either succeeds or hits the configured revision and call limits. This is the lowest-coordination path in the project, which makes it the clean baseline for measuring efficiency, latency, and patch quality.

### Multi-Agent

The multi-agent system is built as true role-isolated workers. The Coordinator only plans and decides. The Analyst only summarizes the issue and isolates the likely root cause. Separate Engineer workers then run in parallel, each producing its own patch candidate in its own branch. The Tester and Reviewer evaluate each branch, and the coordinator chooses the best branch or stops the run if the workflow is stuck.

This means one agent is not switching roles anymore. Each role stays fixed, and the parallel engineer branches let the system try multiple implementation paths at the same time. The research question is whether that extra specialization and parallel search helps enough to justify the higher coordination cost and additional LLM calls.

## Workflow Graph

### The graph built in this repo

The single-agent path is one revision loop. The multi-agent path adds role isolation, parallel engineer branches, deterministic test-based validation, direct question-and-answer messaging between agents, and a coordinator that can stop early when the run stalls.

### Single-Agent baseline

1 agent instance owns the whole cycle and reuses failure feedback on the next attempt.

`Summarize` → `Diagnose` → `Patch` → `Run Tests` → `Review` → `Retry or Finish`

If validation fails or review says revise, the loop continues until it succeeds or hits revision limits.

### Multi-Agent workflow

6 different agent instances are used by default: 1 coordinator, 1 analyst, 2 engineers, 1 tester, and 1 reviewer.

`Coordinator` → `Analyst` → `Engineer Fanout`

Parallel branches:

- `Engineer 1` → `Test + Review`
- `Engineer 2` → `Test + Review`

Direct messages when needed:

- `Engineer ↔ Analyst`
- `Tester ↔ Engineer`
- `Reviewer ↔ Engineer`
- `Coordinator ↔ Any role`

`Coordinator Decision` → `Finish or Retry`

Agents still have fixed responsibilities, but they can directly ask other agents questions during execution instead of relying only on one-way handoffs.

## Useful Commands

Run tests:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Run single-agent:

```bash
PYTHONPATH=src python3 -m agentic_research.cli --architecture single --task no-color --mode openai
```

Run multi-agent:

```bash
PYTHONPATH=src python3 -m agentic_research.cli --architecture multi --task no-color --mode openai
```

Run a benchmark suite:

```bash
PYTHONPATH=src python3 -m agentic_research.benchmark_cli --tasks no-color click-no-color-real --architectures single multi --repeats 2 --mode deterministic
```
