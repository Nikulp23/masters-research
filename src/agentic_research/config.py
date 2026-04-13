from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class ResearchConfig:
    mode: str
    openai_model: str
    max_iterations: int
    max_revision_rounds: int
    max_llm_calls: int
    multi_max_llm_calls: int
    multi_engineer_workers: int


def load_config() -> ResearchConfig:
    return ResearchConfig(
        mode=os.getenv("AGENTIC_MODE", "deterministic"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5.1-codex-mini"),
        max_iterations=int(os.getenv("AGENTIC_MAX_ITERATIONS", "50")),
        max_revision_rounds=int(os.getenv("AGENTIC_MAX_REVISIONS", "30")),
        max_llm_calls=int(os.getenv("AGENTIC_MAX_LLM_CALLS", "0")),
        multi_max_llm_calls=int(os.getenv("AGENTIC_MULTI_MAX_LLM_CALLS", "0")),
        multi_engineer_workers=int(os.getenv("AGENTIC_MULTI_ENGINEER_WORKERS", "1")),
    )
