from __future__ import annotations

from typing import Any

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


class DeterministicResearchBrain:
    """Local deterministic simulator for the first runnable prototype."""

    def summarize_issue(self, state: dict[str, Any], role: str) -> str:
        constraints = "; ".join(state["constraints"])
        response = (
            f"{role} summary: {state['title']} in {state['repository']}. "
            f"Difficulty={state['difficulty']}. Constraints: {constraints}"
        )
        append_transcript_entry(
            state,
            role=role,
            phase="summarize_issue",
            kind="llm",
            prompt=summarize_prompt(state, role),
            response=response,
        )
        return response

    def coordinator_plan(self, state: dict[str, Any]) -> str:
        response = (
            "Coordinator plan: delegate issue analysis to the analyst, hand the root cause to the engineer, "
            "then require tester validation and reviewer acceptance before shipping."
        )
        append_transcript_entry(
            state,
            role="Coordinator",
            phase="plan",
            kind="llm",
            prompt=coordinator_plan_prompt(state),
            response=response,
        )
        return response

    def diagnose_root_cause(self, state: dict[str, Any], role: str) -> str:
        difficulty_note = {
            "easy": "The bug is likely local and behavior-driven.",
            "medium": "The bug likely crosses a small module boundary.",
            "hard": "The bug likely involves state handling and report semantics.",
        }[state["difficulty"]]
        response = f"{role} diagnosis: {difficulty_note}"
        append_transcript_entry(
            state,
            role=role,
            phase="diagnose_root_cause",
            kind="llm",
            prompt=diagnose_prompt(state, role),
            response=response,
        )
        return response

    def propose_patch(self, state: dict[str, Any], role: str) -> str:
        if state.get("execution_mode") == "sandbox" and state["task_id"] == "no-color":
            fixed_source = """from __future__ import annotations

import os

ANSI_COLORS = {
    "green": "\\033[32m",
    "red": "\\033[31m",
}
ANSI_RESET = "\\033[0m"


def color_enabled() -> bool:
    no_color = os.getenv("NO_COLOR")
    return not no_color


def render_message(message: str, color: str = "green") -> str:
    if not color_enabled():
        return message
    prefix = ANSI_COLORS.get(color, "")
    if not prefix:
        return message
    return f"{prefix}{message}{ANSI_RESET}"
"""
            response = (
                '{\n'
                '  "summary": "Add a NO_COLOR check to disable ANSI color output in the sandbox demo.",\n'
                '  "files": {\n'
                '    "src/no_color_app.py": ' + json_string(fixed_source) + "\n"
                "  }\n"
                "}"
            )
            append_transcript_entry(
                state,
                role=role,
                phase="propose_patch",
                kind="llm",
                prompt=patch_prompt(state, role),
                response=response,
            )
            return response
        if state.get("execution_mode") == "sandbox" and state["task_id"] == "negative-flag-fixture":
            fixed_source = """from __future__ import annotations


def resolve_negative_flag(default: bool, flag_value: bool | None) -> bool:
    if flag_value is None:
        return default
    return flag_value
"""
            response = (
                '{\n'
                '  "summary": "Preserve the true default when the negative flag is omitted.",\n'
                '  "files": {\n'
                '    "src/negative_flag_app.py": ' + json_string(fixed_source) + "\n"
                "  }\n"
                "}"
            )
            append_transcript_entry(
                state,
                role=role,
                phase="propose_patch",
                kind="llm",
                prompt=patch_prompt(state, role),
                response=response,
            )
            return response
        if state.get("execution_mode") == "sandbox" and state["task_id"] == "plugin-loader-fixture":
            fixed_source = """from __future__ import annotations

from typing import Any


def kernel_function(func: Any) -> Any:
    func.__kernel_function__ = True
    return func


def _has_kernel_function(cls: type[Any]) -> bool:
    for name in dir(cls):
        value = getattr(cls, name)
        if getattr(value, "__kernel_function__", False):
            return True
    return False


def load_plugin(plugin_classes: list[type[Any]]) -> object:
    for cls in plugin_classes:
        if not _has_kernel_function(cls):
            continue
        return cls()
    raise ValueError("No plugin classes found")
"""
            response = (
                '{\n'
                '  "summary": "Skip classes without kernel-decorated methods before loading a plugin.",\n'
                '  "files": {\n'
                '    "src/plugin_loader.py": ' + json_string(fixed_source) + "\n"
                "  }\n"
                "}"
            )
            append_transcript_entry(
                state,
                role=role,
                phase="propose_patch",
                kind="llm",
                prompt=patch_prompt(state, role),
                response=response,
            )
            return response
        if state.get("execution_mode") == "sandbox" and state["task_id"] == "click-no-color-real":
            fixed_source = """from __future__ import annotations

import os
import typing as t
from threading import local

if t.TYPE_CHECKING:
    from .core import Context

_local = local()


@t.overload
def get_current_context(silent: t.Literal[False] = False) -> Context: ...


@t.overload
def get_current_context(silent: bool = ...) -> Context | None: ...


def get_current_context(silent: bool = False) -> Context | None:
    \"\"\"Returns the current click context.  This can be used as a way to
    access the current context object from anywhere.  This is a more implicit
    alternative to the :func:`pass_context` decorator.  This function is
    primarily useful for helpers such as :func:`echo` which might be
    interested in changing its behavior based on the current context.

    To push the current context, :meth:`Context.scope` can be used.

    .. versionadded:: 5.0

    :param silent: if set to `True` the return value is `None` if no context
                   is available.  The default behavior is to raise a
                   :exc:`RuntimeError`.
    \"\"\"
    try:
        return t.cast("Context", _local.stack[-1])
    except (AttributeError, IndexError) as e:
        if not silent:
            raise RuntimeError("There is no active click context.") from e

    return None


def push_context(ctx: Context) -> None:
    \"\"\"Pushes a new context to the current stack.\"\"\"
    _local.__dict__.setdefault("stack", []).append(ctx)


def pop_context() -> None:
    \"\"\"Removes the top level from the stack.\"\"\"
    _local.stack.pop()


def resolve_color_default(color: bool | None = None) -> bool | None:
    \"\"\"Internal helper to get the default value of the color flag.  If a
    value is passed it's returned unchanged, otherwise it's looked up from
    the current context.
    \"\"\"
    if color is not None:
        return color

    if os.environ.get("NO_COLOR"):
        return False

    ctx = get_current_context(silent=True)

    if ctx is not None:
        return ctx.color

    return None
"""
            response = (
                '{\n'
                '  "summary": "Honor NO_COLOR in click.globals.resolve_color_default for the real click issue sandbox.",\n'
                '  "files": {\n'
                '    "src/click/globals.py": ' + json_string(fixed_source) + "\n"
                "  }\n"
                "}"
            )
            append_transcript_entry(
                state,
                role=role,
                phase="propose_patch",
                kind="llm",
                prompt=patch_prompt(state, role),
                response=response,
            )
            return response
        if state.get("execution_mode") == "sandbox" and state["task_id"] in {
            "click-negative-flag-real",
            "click-class-flag-default-real",
        }:
            find_block = """        # Support the special case of aligning the default value with the flag_value
        # for flags whose default is explicitly set to True. Note that as long as we
        # have this condition, there is no way a flag can have a default set to True,
        # and a flag_value set to something else. Refs:
        # https://github.com/pallets/click/issues/3024#issuecomment-3146199461
        # https://github.com/pallets/click/pull/3030/commits/06847da
        if self.default is True and self.flag_value is not UNSET:
            self.default = self.flag_value
"""
            replace_block = """        # Support the special case of aligning the default value with the flag_value
        # for flags whose default is explicitly set to True. Negative boolean flags
        # should keep their default=True behavior, and callable flag values should
        # return the object itself instead of invoking it as a default factory.
        if self.default is True and self.flag_value is not UNSET:
            if self.flag_value is False:
                pass
            elif callable(self.flag_value):
                self.default = lambda: self.flag_value
            else:
                self.default = self.flag_value
"""
            response = (
                '{\n'
                '  "summary": "Refine Click flag default handling for negative boolean flags and callable flag values.",\n'
                '  "edits": [\n'
                '    {\n'
                '      "path": "src/click/core.py",\n'
                '      "find": ' + json_string(find_block) + ",\n"
                '      "replace": ' + json_string(replace_block) + "\n"
                "    }\n"
                "  ]\n"
                "}"
            )
            append_transcript_entry(
                state,
                role=role,
                phase="propose_patch",
                kind="llm",
                prompt=patch_prompt(state, role),
                response=response,
            )
            return response
        if state.get("execution_mode") == "sandbox" and state["task_id"] == "markitdown-docx-equations-real":
            find_block = """import sys

from typing import BinaryIO, Any

from ._html_converter import HtmlConverter
from .._base_converter import DocumentConverter, DocumentConverterResult
from .._stream_info import StreamInfo
from .._exceptions import MissingDependencyException, MISSING_DEPENDENCY_MESSAGE
"""
            replace_block = """import sys

from typing import BinaryIO, Any

from ._html_converter import HtmlConverter
from ..converter_utils.docx.pre_process import pre_process_docx
from .._base_converter import DocumentConverter, DocumentConverterResult
from .._stream_info import StreamInfo
from .._exceptions import MissingDependencyException, MISSING_DEPENDENCY_MESSAGE
"""
            find_convert = """        style_map = kwargs.get("style_map", None)
        return self._html_converter.convert_string(
            mammoth.convert_to_html(file_stream, style_map=style_map).value, **kwargs
        )
"""
            replace_convert = """        style_map = kwargs.get("style_map", None)
        pre_process_stream = pre_process_docx(file_stream)
        return self._html_converter.convert_string(
            mammoth.convert_to_html(pre_process_stream, style_map=style_map).value, **kwargs
        )
"""
            response = (
                '{\n'
                '  "summary": "Pre-process DOCX XML before Mammoth conversion so equation markup is preserved as Markdown math.",\n'
                '  "edits": [\n'
                '    {\n'
                '      "path": "src/markitdown/converters/_docx_converter.py",\n'
                '      "find": ' + json_string(find_block) + ",\n"
                '      "replace": ' + json_string(replace_block) + "\n"
                "    },\n"
                '    {\n'
                '      "path": "src/markitdown/converters/_docx_converter.py",\n'
                '      "find": ' + json_string(find_convert) + ",\n"
                '      "replace": ' + json_string(replace_convert) + "\n"
                "    }\n"
                "  ]\n"
                "}"
            )
            append_transcript_entry(
                state,
                role=role,
                phase="propose_patch",
                kind="llm",
                prompt=patch_prompt(state, role),
                response=response,
            )
            return response
        if state.get("execution_mode") == "sandbox" and state["task_id"] == "semantic-kernel-plugin-init-real":
            find_block = """        for name, cls_instance in inspect.getmembers(module, inspect.isclass):
            if cls_instance.__module__ != module_name:
                continue
            instance = getattr(module, name)(**class_init_arguments.get(name, {}) if class_init_arguments else {})
            return cls.from_object(plugin_name=plugin_name, description=description, plugin_instance=instance)
"""
            replace_block = """        for name, cls_instance in inspect.getmembers(module, inspect.isclass):
            if cls_instance.__module__ != module_name:
                continue
            has_kernel_function = False
            for _, method in inspect.getmembers(cls_instance, inspect.isfunction):
                if getattr(method, "__kernel_function__", False):
                    has_kernel_function = True
                    break
            if not has_kernel_function:
                continue
            init_args = class_init_arguments.get(name, {}) if class_init_arguments else {}
            instance = getattr(module, name)(**init_args)
            return cls.from_object(plugin_name=plugin_name, description=description, plugin_instance=instance)
"""
            response = (
                '{\n'
                '  "summary": "Skip classes without kernel-decorated methods before instantiating a plugin class from a Python file.",\n'
                '  "edits": [\n'
                '    {\n'
                '      "path": "semantic_kernel/functions/kernel_plugin.py",\n'
                '      "find": ' + json_string(find_block) + ",\n"
                '      "replace": ' + json_string(replace_block) + "\n"
                "    }\n"
                "  ]\n"
                "}"
            )
            append_transcript_entry(
                state,
                role=role,
                phase="propose_patch",
                kind="llm",
                prompt=patch_prompt(state, role),
                response=response,
            )
            return response

        keywords = list(state["acceptance_keywords"])
        revision = state["revision_count"]
        difficulty = state["difficulty"]

        # Harder tasks initially miss one requirement to force the revision path.
        if role == "Single Agent":
            if difficulty in {"medium", "hard"} and revision == 0 and len(keywords) > 1:
                included = keywords[:-1]
            else:
                included = keywords
        else:
            if difficulty == "hard" and revision == 0 and len(keywords) > 2:
                included = keywords[:-1]
            else:
                included = keywords

        bullets = "\n".join(f"- address {item}" for item in included)
        feedback = state["latest_feedback"]
        feedback_line = f"\nFeedback addressed: {feedback}" if feedback else ""
        response = (
            f"{role} patch proposal for '{state['title']}':\n"
            f"{bullets}\n"
            "- update tests to capture the regression"
            f"{feedback_line}"
        )
        append_transcript_entry(
            state,
            role=role,
            phase="propose_patch",
            kind="llm",
            prompt=patch_prompt(state, role),
            response=response,
        )
        return response

    def validate(self, state: dict[str, Any], role: str) -> tuple[bool, str]:
        if state.get("execution_mode") == "sandbox":
            passed = state.get("test_returncode", 1) == 0
            if passed:
                report = (
                    f"{role} validation passed. Real test command exited with code 0 for "
                    f"{', '.join(state.get('changed_files', [])) or 'no changed files'}."
                )
                append_transcript_entry(
                    state,
                    role=role,
                    phase="validate",
                    kind="llm",
                    prompt=validation_prompt(state, role),
                    response=json_string({"passed": True, "report": report}),
                )
                return True, report
            report = (
                f"{role} validation failed. Real test command exited with code "
                f"{state.get('test_returncode')}.\nSTDOUT:\n{state.get('test_stdout', '')}\n"
                f"STDERR:\n{state.get('test_stderr', '')}"
            )
            append_transcript_entry(
                state,
                role=role,
                phase="validate",
                kind="llm",
                prompt=validation_prompt(state, role),
                response=json_string({"passed": False, "report": report}),
            )
            return False, report

        patch = state["current_patch"].lower()
        missing = [item for item in state["acceptance_keywords"] if item.lower() not in patch]
        if missing:
            report = (
                f"{role} validation failed. Missing acceptance keywords: {', '.join(missing)}. "
                f"Validation rule: {state['validation_instructions']}"
            )
            append_transcript_entry(
                state,
                role=role,
                phase="validate",
                kind="llm",
                prompt=validation_prompt(state, role),
                response=json_string({"passed": False, "report": report}),
            )
            return False, report

        report = (
            f"{role} validation passed. Patch covers {', '.join(state['acceptance_keywords'])} "
            "and includes an explicit regression-testing story."
        )
        append_transcript_entry(
            state,
            role=role,
            phase="validate",
            kind="llm",
            prompt=validation_prompt(state, role),
            response=json_string({"passed": True, "report": report}),
        )
        return True, report

    def review(self, state: dict[str, Any], role: str) -> tuple[ReviewRecommendation, str]:
        if state.get("execution_mode") == "sandbox":
            if not state["validation_passed"]:
                notes = f"{role} review: test execution is still failing."
                append_transcript_entry(
                    state,
                    role=role,
                    phase="review",
                    kind="llm",
                    prompt=review_prompt(state, role),
                    response=json_string({"recommendation": "revise", "notes": notes}),
                )
                return "revise", notes
            if not state.get("changed_files"):
                notes = f"{role} review: no files were changed."
                append_transcript_entry(
                    state,
                    role=role,
                    phase="review",
                    kind="llm",
                    prompt=review_prompt(state, role),
                    response=json_string({"recommendation": "revise", "notes": notes}),
                )
                return "revise", notes
            notes = (
                f"{role} review: patch updated {', '.join(state['changed_files'])} and the real test "
                "suite passed."
            )
            append_transcript_entry(
                state,
                role=role,
                phase="review",
                kind="llm",
                prompt=review_prompt(state, role),
                response=json_string({"recommendation": "accept", "notes": notes}),
            )
            return "accept", notes

        if not state["validation_passed"]:
            notes = f"{role} review: reject until validation passes."
            append_transcript_entry(
                state,
                role=role,
                phase="review",
                kind="llm",
                prompt=review_prompt(state, role),
                response=json_string({"recommendation": "revise", "notes": notes}),
            )
            return "revise", notes

        patch = state["current_patch"].lower()
        if "update tests" not in patch and "regression test" not in patch:
            notes = f"{role} review: patch still needs explicit regression-test coverage."
            append_transcript_entry(
                state,
                role=role,
                phase="review",
                kind="llm",
                prompt=review_prompt(state, role),
                response=json_string({"recommendation": "revise", "notes": notes}),
            )
            return "revise", notes

        notes = f"{role} review: patch is acceptable with bounded regression risk."
        append_transcript_entry(
            state,
            role=role,
            phase="review",
            kind="llm",
            prompt=review_prompt(state, role),
            response=json_string({"recommendation": "accept", "notes": notes}),
        )
        return "accept", notes


def build_log_entry(role: str, state: dict[str, Any], message: str) -> dict[str, Any]:
    payload = {
        "role": role,
        "iteration": state["iteration_count"],
        "revision": state["revision_count"],
        "message": message,
    }
    if state.get("branch_id"):
        payload["branch_id"] = state["branch_id"]
    return payload


def json_string(value: str) -> str:
    import json

    return json.dumps(value)
