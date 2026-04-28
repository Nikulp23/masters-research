from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Protocol

from anthropic import Anthropic

from .brains import DeterministicResearchBrain
from .config import ResearchConfig
from .prompts import (
    coordinator_decision_prompt,
    coordinator_plan_prompt,
    diagnose_prompt,
    patch_prompt,
    review_prompt,
    summarize_prompt,
    validation_prompt,
)
from .state import ReviewRecommendation
from .transcript import append_transcript_entry


class BrainProtocol(Protocol):
    def summarize_issue(self, state: dict[str, Any], role: str) -> str: ...
    def coordinator_plan(self, state: dict[str, Any]) -> str: ...
    def diagnose_root_cause(self, state: dict[str, Any], role: str) -> str: ...
    def propose_patch(self, state: dict[str, Any], role: str, strategy: str = "") -> str: ...
    def validate(self, state: dict[str, Any], role: str) -> tuple[bool, str]: ...
    def review(self, state: dict[str, Any], role: str) -> tuple[ReviewRecommendation, str]: ...
    def coordinator_decision(self, state: dict[str, Any], branch_results: list[dict[str, Any]]) -> tuple[str, str]: ...


_ROLE_SYSTEM_PROMPTS: dict[str, str] = {
    "coordinator": (
        "You are a Tech Lead coordinating a multi-agent software engineering team. "
        "Your focus is planning, delegation, and making the final ship/no-ship decision. "
        "Be directive and concise. Do not implement; only plan and decide."
    ),
    "analyst": (
        "You are a Senior Software Engineer specializing in root-cause analysis. "
        "Your focus is understanding broken behavior and tracing it to its source in the code. "
        "Be precise and skeptical. Do not propose fixes; only diagnose."
    ),
    "engineer": (
        "You are a Software Engineer responsible for writing the actual code fix. "
        "Your focus is producing a minimal, correct patch that makes the failing test pass. "
        "Be implementation-focused. Do not over-engineer or broaden scope."
    ),
    "tester": (
        "You are a QA Engineer responsible for validating that the patch is correct. "
        "Your focus is evaluating real test output and patch coverage. "
        "Be skeptical. Do not accept a patch just because it compiles."
    ),
    "reviewer": (
        "You are a Senior Engineer doing a final code review before merge. "
        "Your focus is correctness, regression risk, and scope discipline. "
        "Recommend 'revise' if the patch is broader than necessary or hides problems."
    ),
    "single": (
        "You are a Senior Software Engineer working independently to fix a bug end-to-end. "
        "You are responsible for understanding the issue, diagnosing the root cause, "
        "implementing a fix, and verifying it against the test suite. Be precise and methodical."
    ),
}


@dataclass
class ClaudeResearchBrain:
    client: Anthropic
    model: str
    max_llm_calls: int
    system_prompt: str = ""
    max_output_tokens_default: int = 350
    # Per-phase output caps; overrides max_output_tokens_default when set.
    phase_token_caps: dict[str, int] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.phase_token_caps is None:
            self.phase_token_caps = {}

    def _ensure_budget(self, state: dict[str, Any]) -> None:
        max_calls = state.get("max_llm_calls", self.max_llm_calls)
        if max_calls is not None and max_calls > 0 and state.get("llm_calls_used", 0) >= max_calls:
            raise RuntimeError("LLM call budget exhausted.")

    def _record_call(self, state: dict[str, Any]) -> None:
        state["llm_calls_used"] = state.get("llm_calls_used", 0) + 1

    def _text_response(
        self,
        prompt: str,
        state: dict[str, Any],
        *,
        role: str,
        phase: str,
        max_output_tokens: int | None = None,
    ) -> str:
        self._ensure_budget(state)
        create_kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": (
                max_output_tokens
                if max_output_tokens is not None
                else self.phase_token_caps.get(phase, self.max_output_tokens_default)
            ),
        }
        if self.system_prompt:
            create_kwargs["system"] = self.system_prompt
        response = self.client.messages.create(**create_kwargs)
        self._record_call(state)
        usage = getattr(response, "usage", None)
        if usage is not None:
            input_tokens = getattr(usage, "input_tokens", 0) or 0
            output_tokens = getattr(usage, "output_tokens", 0) or 0
            call_tokens = input_tokens + output_tokens
            state["tokens_used"] = state.get("tokens_used", 0) + call_tokens
            state["input_tokens_used"] = state.get("input_tokens_used", 0) + input_tokens
            state["output_tokens_used"] = state.get("output_tokens_used", 0) + output_tokens
            by_role = state.get("tokens_by_role") or {}
            by_role[role] = by_role.get(role, 0) + call_tokens
            state["tokens_by_role"] = by_role
            # Track cache hits for observability
            cached = getattr(usage, "cache_read_input_tokens", 0) or 0
            state["cached_tokens"] = state.get("cached_tokens", 0) + cached
        text = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        ).strip()
        append_transcript_entry(
            state,
            role=role,
            phase=phase,
            kind="llm",
            prompt=prompt,
            response=text,
        )
        return text

    def _json_response(
        self,
        prompt: str,
        state: dict[str, Any],
        *,
        role: str,
        phase: str,
        max_output_tokens: int | None = None,
    ) -> dict[str, Any]:
        text = self._text_response(
            prompt,
            state,
            role=role,
            phase=phase,
            max_output_tokens=max_output_tokens,
        )
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise ValueError(f"Model did not return JSON: {text}")
        return json.loads(text[start : end + 1])

    def summarize_issue(self, state: dict[str, Any], role: str) -> str:
        return self._text_response(
            summarize_prompt(state, role),
            state,
            role=role,
            phase="summarize_issue",
        )

    def coordinator_plan(self, state: dict[str, Any]) -> str:
        return self._text_response(
            coordinator_plan_prompt(state),
            state,
            role="Coordinator",
            phase="plan",
        )

    def diagnose_root_cause(self, state: dict[str, Any], role: str) -> str:
        return self._text_response(
            diagnose_prompt(state, role),
            state,
            role=role,
            phase="diagnose_root_cause",
        )

    def propose_patch(self, state: dict[str, Any], role: str, strategy: str = "") -> str:
        return self._text_response(
            patch_prompt(state, role, strategy=strategy),
            state,
            role=role,
            phase="propose_patch",
        )

    def validate(self, state: dict[str, Any], role: str) -> tuple[bool, str]:
        payload = self._json_response(
            validation_prompt(state, role),
            state,
            role=role,
            phase="validate",
        )
        return bool(payload["passed"]), str(payload["report"])

    def review(self, state: dict[str, Any], role: str) -> tuple[ReviewRecommendation, str]:
        payload = self._json_response(
            review_prompt(state, role),
            state,
            role=role,
            phase="review",
        )
        recommendation = payload["recommendation"]
        if recommendation not in {"accept", "revise"}:
            raise ValueError(f"Invalid review recommendation: {recommendation}")
        return recommendation, str(payload["notes"])

    def coordinator_decision(self, state: dict[str, Any], branch_results: list[dict[str, Any]]) -> tuple[str, str]:
        payload = self._json_response(
            coordinator_decision_prompt(state, branch_results),
            state,
            role="Coordinator",
            phase="branch_selection",
        )
        selected = str(payload.get("selected_branch_id", ""))
        reasoning = str(payload.get("reasoning", ""))
        return selected, reasoning


def build_brain(config: ResearchConfig, role: str = "single") -> BrainProtocol:
    if config.mode == "deterministic":
        return DeterministicResearchBrain()

    if config.mode != "claude":
        raise ValueError(f"Unsupported AGENTIC_MODE: {config.mode}")

    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is required when AGENTIC_MODE=claude.")

    # Single-agent brain handles all phases; cap each phase explicitly.
    return ClaudeResearchBrain(
        client=Anthropic(),
        model=config.claude_model,
        max_llm_calls=config.max_llm_calls,
        system_prompt=_ROLE_SYSTEM_PROMPTS.get(role, ""),
        max_output_tokens_default=config.max_tokens_engineer,
        phase_token_caps={
            "validate": config.max_tokens_tester,
            "review": config.max_tokens_reviewer,
            "branch_selection": config.max_tokens_coordinator,
            "plan": config.max_tokens_coordinator,
        },
    )


_ROLE_MODEL_ATTR = {
    "engineer": "engineer_model",
    "tester": "reviewer_model",   # cheap tier
    "reviewer": "reviewer_model",
    "coordinator": "coordinator_model",
    "analyst": "coordinator_model",
}

_ROLE_MAX_TOKENS_ATTR = {
    "engineer": "max_tokens_engineer",
    "tester": "max_tokens_tester",
    "reviewer": "max_tokens_reviewer",
    "coordinator": "max_tokens_coordinator",
    "analyst": "max_tokens_coordinator",
}


def build_multi_worker_brains(config: ResearchConfig) -> dict[str, Any]:
    """Build a set of role-specialised brains for the multi-agent workflow."""
    if config.mode == "deterministic":
        det = DeterministicResearchBrain()
        n = max(config.multi_engineer_workers, 1)
        return {
            "coordinator": det,
            "analyst": det,
            "engineers": [det for _ in range(n)],
            "testers": [det for _ in range(n)],
            "reviewers": [det for _ in range(n)],
        }

    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is required when AGENTIC_MODE=claude.")

    def _brain(role: str) -> ClaudeResearchBrain:
        model = getattr(config, _ROLE_MODEL_ATTR.get(role, "claude_model"), config.claude_model)
        max_tokens = getattr(config, _ROLE_MAX_TOKENS_ATTR.get(role, "max_tokens_engineer"), config.max_tokens_engineer)
        return ClaudeResearchBrain(
            client=Anthropic(),
            model=model,
            max_llm_calls=config.multi_max_llm_calls,
            system_prompt=_ROLE_SYSTEM_PROMPTS.get(role, ""),
            max_output_tokens_default=max_tokens,
        )

    n_branches = max(config.multi_engineer_workers, 1)
    return {
        "coordinator": _brain("coordinator"),
        "analyst": _brain("analyst"),
        "engineers": [_brain("engineer") for _ in range(n_branches)],
        "testers": [_brain("tester") for _ in range(n_branches)],
        "reviewers": [_brain("reviewer") for _ in range(n_branches)],
    }