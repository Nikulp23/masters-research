from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Protocol

from openai import OpenAI

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
class OpenAIResearchBrain:
    client: OpenAI
    model: str
    max_llm_calls: int
    system_prompt: str = ""

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
        max_output_tokens: int = 350,
    ) -> str:
        self._ensure_budget(state)
        create_kwargs: dict[str, Any] = {
            "model": self.model,
            "input": prompt,
            "max_output_tokens": max_output_tokens,
        }
        if self.system_prompt:
            create_kwargs["instructions"] = self.system_prompt
        response = self.client.responses.create(**create_kwargs)
        self._record_call(state)
        usage = getattr(response, "usage", None)
        if usage is not None:
            state["tokens_used"] = state.get("tokens_used", 0) + getattr(usage, "total_tokens", 0)
        text = response.output_text.strip()
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
        max_output_tokens: int = 350,
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
        max_tokens = 2000 if state.get("execution_mode") == "sandbox" else 350
        return self._text_response(
            patch_prompt(state, role, strategy=strategy),
            state,
            role=role,
            phase="propose_patch",
            max_output_tokens=max_tokens,
        )

    def validate(self, state: dict[str, Any], role: str) -> tuple[bool, str]:
        payload = self._json_response(
            validation_prompt(state, role),
            state,
            role=role,
            phase="validate",
            max_output_tokens=1000,
        )
        return bool(payload["passed"]), str(payload["report"])

    def review(self, state: dict[str, Any], role: str) -> tuple[ReviewRecommendation, str]:
        payload = self._json_response(
            review_prompt(state, role),
            state,
            role=role,
            phase="review",
            max_output_tokens=1000,
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
            max_output_tokens=300,
        )
        selected = str(payload.get("selected_branch_id", ""))
        reasoning = str(payload.get("reasoning", ""))
        return selected, reasoning


def build_brain(config: ResearchConfig, role: str = "single") -> BrainProtocol:
    if config.mode == "deterministic":
        return DeterministicResearchBrain()

    if config.mode != "openai":
        raise ValueError(f"Unsupported AGENTIC_MODE: {config.mode}")

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required when AGENTIC_MODE=openai.")

    client = OpenAI()
    return OpenAIResearchBrain(
        client=client,
        model=config.openai_model,
        max_llm_calls=config.max_llm_calls,
        system_prompt=_ROLE_SYSTEM_PROMPTS.get(role, ""),
    )


def build_multi_worker_brains(config: ResearchConfig) -> dict[str, Any]:
    """Build a set of role-specialised brains for the multi-agent workflow."""
    if config.mode == "deterministic":
        det = DeterministicResearchBrain()
        return {
            "coordinator": det,
            "analyst": det,
            "engineers": [det for _ in range(max(config.multi_engineer_workers, 1))],
            "tester": det,
            "reviewer": det,
        }

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required when AGENTIC_MODE=openai.")

    client = OpenAI()

    def _brain(role: str) -> OpenAIResearchBrain:
        return OpenAIResearchBrain(
            client=client,
            model=config.openai_model,
            max_llm_calls=config.multi_max_llm_calls,
            system_prompt=_ROLE_SYSTEM_PROMPTS.get(role, ""),
        )

    return {
        "coordinator": _brain("coordinator"),
        "analyst": _brain("analyst"),
        "engineers": [_brain("engineer") for _ in range(max(config.multi_engineer_workers, 1))],
        "tester": _brain("tester"),
        "reviewer": _brain("reviewer"),
    }