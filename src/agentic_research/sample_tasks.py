from __future__ import annotations

from typing import NotRequired, TypedDict


class TaskSpec(TypedDict):
    id: str
    title: str
    repository: str
    description: str
    difficulty: str
    constraints: list[str]
    acceptance_keywords: list[str]
    validation_instructions: str
    execution_mode: NotRequired[str]
    fixture_dir: NotRequired[str]
    source_repo_path: NotRequired[str]
    editable_files: NotRequired[list[str]]
    readonly_files: NotRequired[list[str]]
    test_command: NotRequired[list[str]]
    test_env: NotRequired[dict[str, str]]
    injected_test_files: NotRequired[dict[str, str]]
    prompt_context: NotRequired[dict[str, str]]


SAMPLE_TASKS: dict[str, TaskSpec] = {
    "rerun-teardown": {
        "id": "rerun-teardown",
        "title": "rerun-except ignores teardown error",
        "repository": "pytest-dev/pytest-rerunfailures",
        "description": (
            "The plugin should respect teardown failures when rerun-except is configured. "
            "The task needs a fixture-based reproducer and the rerun filtering logic must "
            "handle teardown reporting correctly."
        ),
        "difficulty": "hard",
        "constraints": [
            "Keep the fix bounded to plugin logic and tests.",
            "Preserve current CLI option semantics.",
            "Use regression tests to prove the fix.",
        ],
        "acceptance_keywords": [
            "teardown",
            "rerun-except",
            "regression test",
        ],
        "validation_instructions": (
            "Validation passes when the proposed patch addresses teardown handling, "
            "mentions rerun-except behavior, and includes a regression test strategy."
        ),
    },
    "rich-alignment": {
        "id": "rich-alignment",
        "title": "Option group columns do not align",
        "repository": "ewels/rich-click",
        "description": (
            "Option groups rendered in the help output drift out of alignment. The task "
            "should update formatting behavior and add a rendering-oriented regression test."
        ),
        "difficulty": "medium",
        "constraints": [
            "Keep formatting changes local to help rendering.",
            "Avoid broad API changes.",
        ],
        "acceptance_keywords": [
            "alignment",
            "option group",
            "snapshot test",
        ],
        "validation_instructions": (
            "Validation passes when the proposal fixes column alignment and covers the "
            "rendered help output with a regression-style test."
        ),
    },
    "no-color": {
        "id": "no-color",
        "title": "Support NO_COLOR environment variable",
        "repository": "local-fixture/no-color-demo",
        "description": (
            "Add standards-driven support for the NO_COLOR environment variable without "
            "changing unrelated rendering behavior."
        ),
        "difficulty": "easy",
        "constraints": [
            "Keep behavior standards-driven.",
            "Use environment-variable tests instead of broad feature additions.",
        ],
        "acceptance_keywords": [
            "NO_COLOR",
            "environment variable",
        ],
        "validation_instructions": (
            "Validation passes when the patch respects the NO_COLOR environment variable "
            "and the real test suite passes in the sandbox."
        ),
        "execution_mode": "sandbox",
        "fixture_dir": "fixtures/no_color_repo",
        "editable_files": ["src/no_color_app.py"],
        "readonly_files": ["tests/test_no_color_app.py"],
        "test_command": ["python3", "-m", "unittest", "discover", "-s", "tests", "-v"],
    },
    "negative-flag-fixture": {
        "id": "negative-flag-fixture",
        "title": "Negative flag should keep the true default when omitted",
        "repository": "local-fixture/negative-flag-demo",
        "description": (
            "Fix the local negative-flag demo so omitting the negative flag preserves the "
            "default True value while an explicit negative flag still resolves to False."
        ),
        "difficulty": "easy",
        "constraints": [
            "Keep the fix local to the flag resolution helper.",
            "Do not broaden the API beyond the existing helper function.",
        ],
        "acceptance_keywords": [
            "negative flag",
            "default true",
        ],
        "validation_instructions": (
            "Validation passes when the omitted negative flag keeps True and the explicit "
            "negative flag returns False in the real sandbox test."
        ),
        "execution_mode": "sandbox",
        "fixture_dir": "fixtures/negative_flag_repo",
        "editable_files": ["src/negative_flag_app.py"],
        "readonly_files": ["tests/test_negative_flag_app.py"],
        "test_command": ["python3", "-m", "unittest", "discover", "-s", "tests", "-p", "test_negative_flag_app.py", "-v"],
    },
    "plugin-loader-fixture": {
        "id": "plugin-loader-fixture",
        "title": "Plugin loader should skip classes without kernel functions",
        "repository": "local-fixture/plugin-loader-demo",
        "description": (
            "Fix the local plugin loader so it skips classes with no kernel-decorated methods "
            "and loads the first valid plugin class instead."
        ),
        "difficulty": "easy",
        "constraints": [
            "Keep the patch local to the plugin loader module.",
            "Do not change the decorator contract or test shape.",
        ],
        "acceptance_keywords": [
            "plugin loader",
            "kernel function",
        ],
        "validation_instructions": (
            "Validation passes when the loader skips the empty class and returns an instance "
            "of the valid plugin class in the real sandbox test."
        ),
        "execution_mode": "sandbox",
        "fixture_dir": "fixtures/plugin_loader_repo",
        "editable_files": ["src/plugin_loader.py"],
        "readonly_files": ["tests/test_plugin_loader.py"],
        "test_command": ["python3", "-m", "unittest", "discover", "-s", "tests", "-p", "test_plugin_loader.py", "-v"],
    },
    "click-no-color-real": {
        "id": "click-no-color-real",
        "title": "Support NO_COLOR environment variable",
        "repository": "pallets/click",
        "description": (
            "Implement support for the NO_COLOR environment variable in the real click "
            "repository so color defaults are disabled when NO_COLOR is set."
        ),
        "difficulty": "medium",
        "constraints": [
            "Keep the patch tightly scoped to color-default resolution.",
            "Do not add broad new APIs or config layers.",
            "Make the issue-specific real test pass in the sandbox.",
        ],
        "acceptance_keywords": [
            "NO_COLOR",
            "color default",
            "real test",
        ],
        "validation_instructions": (
            "Validation passes only if the real issue-specific unittest passes in the cloned "
            "click sandbox and the patch stays bounded to the targeted source file."
        ),
        "execution_mode": "sandbox",
        "source_repo_path": "/tmp/agentic-click-real",
        "editable_files": ["src/click/globals.py"],
        "readonly_files": ["tests/test_issue_no_color.py"],
        "injected_test_files": {
            "tests/test_issue_no_color.py": """from __future__ import annotations

import os
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from click.globals import resolve_color_default


class NoColorIssueTests(unittest.TestCase):
    def test_resolve_color_default_returns_false_when_no_color_is_set(self) -> None:
        os.environ["NO_COLOR"] = "1"
        try:
            self.assertFalse(resolve_color_default(None))
        finally:
            os.environ.pop("NO_COLOR", None)


if __name__ == "__main__":
    unittest.main()
""",
        },
        "test_command": ["python3", "-m", "unittest", "discover", "-s", "tests", "-p", "test_issue_no_color.py", "-v"],
    },
    "click-negative-flag-real": {
        "id": "click-negative-flag-real",
        "title": "Negative boolean flags keep the wrong default",
        "repository": "pallets/click",
        "description": (
            "Fix the Click 8.3.x default=True special case so a negative boolean flag "
            "with flag_value=False does not force the parameter to False when the flag "
            "is omitted."
        ),
        "difficulty": "medium",
        "constraints": [
            "Keep the patch tightly scoped to option default handling.",
            "Do not rewrite unrelated parsing behavior.",
            "Make the issue-specific real test pass in the sandbox.",
        ],
        "acceptance_keywords": [
            "negative flag",
            "default=True",
            "flag_value=False",
        ],
        "validation_instructions": (
            "Validation passes only if the real unittest shows the omitted flag keeps the "
            "parameter True while the explicit negative flag still sets it to False."
        ),
        "execution_mode": "sandbox",
        "source_repo_path": "/tmp/agentic-click-real",
        "editable_files": ["src/click/core.py"],
        "readonly_files": ["tests/test_issue_negative_flag.py"],
        "prompt_context": {
            "src/click/core.py": """        # Support the special case of aligning the default value with the flag_value
        # for flags whose default is explicitly set to True. Note that as long as we
        # have this condition, there is no way a flag can have a default set to True,
        # and a flag_value set to something else. Refs:
        # https://github.com/pallets/click/issues/3024#issuecomment-3146199461
        # https://github.com/pallets/click/pull/3030/commits/06847da
        if self.default is True and self.flag_value is not UNSET:
            self.default = self.flag_value

        # Set the default flag_value if it is not set.
        if self.flag_value is UNSET:
            if self.is_flag:
                self.flag_value = True
            else:
                self.flag_value = None
""",
        },
        "injected_test_files": {
            "tests/test_issue_negative_flag.py": """from __future__ import annotations

import unittest

import click
from click.testing import CliRunner


@click.command("foo")
@click.option(
    "--without-xyz",
    "enable_xyz",
    help="Disable xyz",
    flag_value=False,
    default=True,
    show_default=True,
)
def foo(enable_xyz: bool) -> None:
    click.echo(f"enable_xyz = {enable_xyz!r}")


class NegativeFlagIssueTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()

    def test_omitted_negative_flag_keeps_true_default(self) -> None:
        result = self.runner.invoke(foo, [])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(result.output.strip(), "enable_xyz = True")

    def test_explicit_negative_flag_sets_false(self) -> None:
        result = self.runner.invoke(foo, ["--without-xyz"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(result.output.strip(), "enable_xyz = False")


if __name__ == "__main__":
    unittest.main()
""",
        },
        "test_command": ["python3", "-m", "unittest", "discover", "-s", "tests", "-p", "test_issue_negative_flag.py", "-v"],
    },
    "click-class-flag-default-real": {
        "id": "click-class-flag-default-real",
        "title": "Class flag_value should not instantiate default",
        "repository": "pallets/click",
        "description": (
            "Fix the default=True flag special case so using a class as flag_value does "
            "not instantiate the class when the option is omitted."
        ),
        "difficulty": "medium",
        "constraints": [
            "Keep the patch tightly scoped to option default handling.",
            "Preserve explicit --foo and --bar behavior.",
            "Make the issue-specific real test pass in the sandbox.",
        ],
        "acceptance_keywords": [
            "flag_value",
            "class default",
            "UNPROCESSED",
        ],
        "validation_instructions": (
            "Validation passes only if the omitted option returns the class object and "
            "not an instantiated object, while explicit flags still return the class."
        ),
        "execution_mode": "sandbox",
        "source_repo_path": "/tmp/agentic-click-real",
        "editable_files": ["src/click/core.py"],
        "readonly_files": ["tests/test_issue_class_flag_default.py"],
        "prompt_context": {
            "src/click/core.py": """        # Support the special case of aligning the default value with the flag_value
        # for flags whose default is explicitly set to True. Note that as long as we
        # have this condition, there is no way a flag can have a default set to True,
        # and a flag_value set to something else. Refs:
        # https://github.com/pallets/click/issues/3024#issuecomment-3146199461
        # https://github.com/pallets/click/pull/3030/commits/06847da
        if self.default is True and self.flag_value is not UNSET:
            self.default = self.flag_value

        # Set the default flag_value if it is not set.
        if self.flag_value is UNSET:
            if self.is_flag:
                self.flag_value = True
            else:
                self.flag_value = None
""",
        },
        "injected_test_files": {
            "tests/test_issue_class_flag_default.py": """from __future__ import annotations

import unittest

import click
from click.testing import CliRunner


class Foo:
    pass


class Bar:
    pass


@click.command()
@click.option("--foo", "ty", flag_value=Foo, type=click.UNPROCESSED, default=True)
@click.option("--bar", "ty", flag_value=Bar, type=click.UNPROCESSED)
def main(ty: object) -> None:
    click.echo(repr(ty))


class ClassFlagDefaultIssueTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()

    def test_omitted_option_returns_class_not_instance(self) -> None:
        result = self.runner.invoke(main, [])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(result.output.strip(), "<class 'tests.test_issue_class_flag_default.Foo'>")

    def test_explicit_other_flag_still_returns_bar_class(self) -> None:
        result = self.runner.invoke(main, ["--bar"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(result.output.strip(), "<class 'tests.test_issue_class_flag_default.Bar'>")


if __name__ == "__main__":
    unittest.main()
""",
        },
        "test_command": ["python3", "-m", "unittest", "discover", "-s", "tests", "-p", "test_issue_class_flag_default.py", "-v"],
    },
    "markitdown-docx-equations-real": {
        "id": "markitdown-docx-equations-real",
        "title": "DOCX equations should render into Markdown",
        "repository": "microsoft/markitdown",
        "description": (
            "Fix the DOCX conversion path so equation content in a real MarkItDown DOCX "
            "fixture is preserved as Markdown math instead of being dropped during conversion."
        ),
        "difficulty": "medium",
        "constraints": [
            "Keep the patch tightly scoped to DOCX conversion.",
            "Use the existing DOCX pre-processing utility instead of broad converter rewrites.",
            "Make the real issue-specific pytest regression pass in the sandbox.",
        ],
        "acceptance_keywords": [
            "docx",
            "equations",
            "markdown math",
        ],
        "validation_instructions": (
            "Validation passes only if the real pytest regression shows inline and block "
            "equations are preserved in the DOCX-to-Markdown output."
        ),
        "execution_mode": "sandbox",
        "source_repo_path": "/tmp/agentic-markitdown-docx-equations-buggy",
        "editable_files": ["src/markitdown/converters/_docx_converter.py"],
        "readonly_files": [
            "src/markitdown/converter_utils/docx/pre_process.py",
            "tests/test_issue_docx_equations.py",
            "tests/test_files/equations.docx",
        ],
        "prompt_context": {
            "src/markitdown/converters/_docx_converter.py": """import sys

from typing import BinaryIO, Any

from ._html_converter import HtmlConverter
from .._base_converter import DocumentConverter, DocumentConverterResult
from .._stream_info import StreamInfo
from .._exceptions import MissingDependencyException, MISSING_DEPENDENCY_MESSAGE

# Try loading optional (but in this case, required) dependencies
# Save reporting of any exceptions for later
_dependency_exc_info = None
try:
    import mammoth
except ImportError:
    # Preserve the error and stack trace for later
    _dependency_exc_info = sys.exc_info()


class DocxConverter(HtmlConverter):
    def convert(
        self,
        file_stream: BinaryIO,
        stream_info: StreamInfo,
        **kwargs: Any,
    ) -> DocumentConverterResult:
        style_map = kwargs.get("style_map", None)
        return self._html_converter.convert_string(
            mammoth.convert_to_html(file_stream, style_map=style_map).value, **kwargs
        )
""",
        },
        "injected_test_files": {
            "tests/test_issue_docx_equations.py": """from __future__ import annotations

from pathlib import Path
import re

from markitdown import MarkItDown


def test_docx_equations_are_preserved() -> None:
    docx_file = Path(__file__).parent / "test_files" / "equations.docx"
    result = MarkItDown().convert(str(docx_file))

    assert "$m=1$" in result.text_content, "Inline equation $m=1$ not found"

    block_equations = re.findall(r"\\$\\$(.+?)\\$\\$", result.text_content)
    assert block_equations, "No block equations found in the document."
""",
        },
        "test_command": ["python3", "-m", "pytest", "tests/test_issue_docx_equations.py", "-q"],
        "test_env": {"PYTHONPATH": "src"},
    },
    "semantic-kernel-plugin-init-real": {
        "id": "semantic-kernel-plugin-init-real",
        "title": "from_python_file should skip classes without @kernel_function methods",
        "repository": "microsoft/semantic-kernel",
        "description": (
            "Fix KernelPlugin.from_python_file so it does not instantiate classes that "
            "have no @kernel_function methods when loading a plugin from a Python file."
        ),
        "difficulty": "medium",
        "constraints": [
            "Keep the patch tightly scoped to class selection in from_python_file.",
            "Do not change unrelated plugin-loading behavior.",
            "Make the real issue-specific unittest pass in the sandbox.",
        ],
        "acceptance_keywords": [
            "kernel_function",
            "skip classes",
            "from_python_file",
        ],
        "validation_instructions": (
            "Validation passes only if the sandbox unittest proves classes without "
            "@kernel_function methods are skipped and the decorated class is still loaded."
        ),
        "execution_mode": "sandbox",
        "source_repo_path": "/tmp/agentic-semantic-kernel-buggy/python",
        "editable_files": ["semantic_kernel/functions/kernel_plugin.py"],
        "readonly_files": ["tests/test_issue_kernel_plugin.py"],
        "prompt_context": {
            "semantic_kernel/functions/kernel_plugin.py": """    @classmethod
    def from_python_file(
        cls: type[_T],
        plugin_name: str,
        py_file: str,
        description: str | None = None,
        class_init_arguments: dict[str, dict[str, Any]] | None = None,
        encoding: str = "utf-8",
    ) -> _T:
        module_name = os.path.basename(py_file).replace(".py", "")
        spec = importlib.util.spec_from_file_location(module_name, py_file)
        if not spec:
            raise PluginInitializationError(f"Could not load spec from file {py_file}")
        module = importlib.util.module_from_spec(spec)
        if not module or not spec.loader:
            raise PluginInitializationError(f"No module found in file {py_file}")
        spec.loader.exec_module(module)

        for name, cls_instance in inspect.getmembers(module, inspect.isclass):
            if cls_instance.__module__ != module_name:
                continue
            instance = getattr(module, name)(**class_init_arguments.get(name, {}) if class_init_arguments else {})
            return cls.from_object(plugin_name=plugin_name, description=description, plugin_instance=instance)
        raise PluginInitializationError(f"No class found in file: {py_file}")
""",
        },
        "injected_test_files": {
            "tests/test_issue_kernel_plugin.py": """from __future__ import annotations

import importlib.util
import sys
import tempfile
import textwrap
import types
import unittest
from pathlib import Path


def _install_semantic_kernel_stubs() -> None:
    module_names = [
        "semantic_kernel",
        "semantic_kernel.data",
        "semantic_kernel.data.text_search",
        "semantic_kernel.data.text_search.text_search",
        "semantic_kernel.exceptions",
        "semantic_kernel.exceptions.function_exceptions",
        "semantic_kernel.functions",
        "semantic_kernel.functions.kernel_function",
        "semantic_kernel.functions.kernel_function_from_method",
        "semantic_kernel.functions.kernel_function_from_prompt",
        "semantic_kernel.functions.types",
        "semantic_kernel.kernel_pydantic",
        "semantic_kernel.kernel_types",
        "semantic_kernel.utils",
        "semantic_kernel.utils.validation",
    ]
    for name in module_names:
        sys.modules.setdefault(name, types.ModuleType(name))

    class PluginInitializationError(Exception):
        pass

    class FunctionInitializationError(Exception):
        pass

    class KernelFunction:
        pass

    class KernelFunctionFromMethod:
        def __init__(self, method=None, plugin_name=None):
            self.name = getattr(method, "__name__", "kernel_function")
            self.metadata = types.SimpleNamespace(name=self.name, plugin_name=plugin_name)

    class KernelFunctionFromPrompt:
        pass

    class KernelBaseModel:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    class TextSearch:
        pass

    def Field(*args, default_factory=None, default=None, **kwargs):
        if default_factory is not None:
            return default_factory()
        return default

    class StringConstraints:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    sys.modules["semantic_kernel.data.text_search.text_search"].TextSearch = TextSearch
    sys.modules["semantic_kernel.exceptions"].PluginInitializationError = PluginInitializationError
    sys.modules["semantic_kernel.exceptions.function_exceptions"].FunctionInitializationError = (
        FunctionInitializationError
    )
    sys.modules["semantic_kernel.functions.kernel_function"].KernelFunction = KernelFunction
    sys.modules["semantic_kernel.functions.kernel_function_from_method"].KernelFunctionFromMethod = (
        KernelFunctionFromMethod
    )
    sys.modules["semantic_kernel.functions.kernel_function_from_prompt"].KernelFunctionFromPrompt = (
        KernelFunctionFromPrompt
    )
    sys.modules["semantic_kernel.functions.types"].KERNEL_FUNCTION_TYPE = object
    sys.modules["semantic_kernel.kernel_pydantic"].KernelBaseModel = KernelBaseModel
    sys.modules["semantic_kernel.kernel_types"].OptionalOneOrMany = object
    sys.modules["semantic_kernel.utils.validation"].PLUGIN_NAME_REGEX = r".+"

    pydantic_module = types.ModuleType("pydantic")
    pydantic_module.Field = Field
    pydantic_module.StringConstraints = StringConstraints
    sys.modules["pydantic"] = pydantic_module


class KernelPluginIssueTests(unittest.TestCase):
    def test_classes_without_kernel_functions_are_skipped(self) -> None:
        _install_semantic_kernel_stubs()

        plugin_path = (
            Path(__file__).resolve().parents[1]
            / "semantic_kernel"
            / "functions"
            / "kernel_plugin.py"
        )
        spec = importlib.util.spec_from_file_location("kernel_plugin_under_test", plugin_path)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)

        source = textwrap.dedent(
            '''
            class A_NoKernelMethods:
                def __init__(self):
                    raise RuntimeError("should not instantiate")

                def helper(self):
                    return "nope"

            class B_GoodPlugin:
                def __init__(self):
                    self.loaded = True

                def run(self):
                    return "ok"

            B_GoodPlugin.run.__kernel_function__ = True
            '''
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_file = Path(tmpdir) / "demo_plugin.py"
            plugin_file.write_text(source, encoding="utf-8")

            original = module.KernelPlugin.from_object
            module.KernelPlugin.from_object = classmethod(
                lambda cls, plugin_name, description=None, plugin_instance=None: plugin_instance
            )
            try:
                plugin = module.KernelPlugin.from_python_file("demo", str(plugin_file))
            finally:
                module.KernelPlugin.from_object = original

        self.assertEqual(type(plugin).__name__, "B_GoodPlugin")
        self.assertTrue(plugin.loaded)


if __name__ == "__main__":
    unittest.main()
""",
        },
        "test_command": ["python3", "-m", "unittest", "discover", "-s", "tests", "-p", "test_issue_kernel_plugin.py", "-v"],
    },
}


def get_task(task_id: str) -> TaskSpec:
    try:
        return SAMPLE_TASKS[task_id]
    except KeyError as exc:
        available = ", ".join(sorted(SAMPLE_TASKS))
        raise KeyError(f"Unknown task '{task_id}'. Available tasks: {available}") from exc
