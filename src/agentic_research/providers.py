from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Protocol

from openai import OpenAI

from .brains import DeterministicResearchBrain
from .config import ResearchConfig
from .prompts import (
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
    def propose_patch(self, state: dict[str, Any], role: str) -> str: ...
    def validate(self, state: dict[str, Any], role: str) -> tuple[bool, str]: ...
    def review(self, state: dict[str, Any], role: str) -> tuple[ReviewRecommendation, str]: ...


@dataclass
class OpenAIResearchBrain:
    client: OpenAI
    model: str
    max_llm_calls: int

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
        response = self.client.responses.create(
            model=self.model,
            input=prompt,
            max_output_tokens=max_output_tokens,
        )
        self._record_call(state)
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

    def propose_patch(self, state: dict[str, Any], role: str) -> str:
        max_tokens = 2000 if state.get("execution_mode") == "sandbox" else 350
        return self._text_response(
            patch_prompt(state, role),
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


def build_brain(config: ResearchConfig) -> BrainProtocol:
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
    )