from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class ResearchConfig:
    mode: str
    claude_model: str
    engineer_model: str
    reviewer_model: str
    coordinator_model: str
    max_iterations: int
    max_revision_rounds: int
    max_llm_calls: int
    multi_max_llm_calls: int
    multi_engineer_workers: int
    # Per-role output token caps
    max_tokens_engineer: int
    max_tokens_reviewer: int
    max_tokens_coordinator: int
    max_tokens_tester: int
    # Transcript / message history window
    transcript_tail_k: int


def load_config() -> ResearchConfig:
    base_model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    cheap_model = os.getenv("ANTHROPIC_CHEAP_MODEL", "claude-sonnet-4-6")
    return ResearchConfig(
        mode=os.getenv("AGENTIC_MODE", "deterministic"),
        claude_model=base_model,
        engineer_model=os.getenv("ANTHROPIC_ENGINEER_MODEL", base_model),
        reviewer_model=os.getenv("ANTHROPIC_REVIEWER_MODEL", cheap_model),
        coordinator_model=os.getenv("ANTHROPIC_COORDINATOR_MODEL", cheap_model),
        max_iterations=int(os.getenv("AGENTIC_MAX_ITERATIONS", "15")),
        max_revision_rounds=int(os.getenv("AGENTIC_MAX_REVISIONS", "5")),
        max_llm_calls=int(os.getenv("AGENTIC_MAX_LLM_CALLS", "80")),
        multi_max_llm_calls=int(os.getenv("AGENTIC_MULTI_MAX_LLM_CALLS", "120")),
        multi_engineer_workers=int(os.getenv("AGENTIC_MULTI_ENGINEER_WORKERS", "1")),
        max_tokens_engineer=int(os.getenv("AGENTIC_MAX_TOKENS_ENGINEER", "16000")),
        max_tokens_reviewer=int(os.getenv("AGENTIC_MAX_TOKENS_REVIEWER", "400")),
        max_tokens_coordinator=int(os.getenv("AGENTIC_MAX_TOKENS_COORDINATOR", "300")),
        max_tokens_tester=int(os.getenv("AGENTIC_MAX_TOKENS_TESTER", "500")),
        transcript_tail_k=int(os.getenv("AGENTIC_TRANSCRIPT_TAIL_K", "6")),
    )
