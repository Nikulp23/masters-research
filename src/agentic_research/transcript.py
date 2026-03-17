from __future__ import annotations

from typing import Any


def append_transcript_entry(
    state: dict[str, Any],
    *,
    role: str,
    phase: str,
    kind: str,
    prompt: str | None = None,
    response: str | None = None,
    message: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    entry = {
        "role": role,
        "phase": phase,
        "kind": kind,
        "iteration": state.get("iteration_count", 0),
        "revision": state.get("revision_count", 0),
    }
    if state.get("branch_id"):
        entry["branch_id"] = state["branch_id"]
    if prompt is not None:
        entry["prompt"] = prompt
    if response is not None:
        entry["response"] = response
    if message is not None:
        entry["message"] = message
    if extra:
        entry.update(extra)

    transcript = list(state.get("transcript", []))
    transcript.append(entry)
    state["transcript"] = transcript
    return entry
