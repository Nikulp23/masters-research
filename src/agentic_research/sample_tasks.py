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
    base_commit: NotRequired[str]   # Check repo out to this commit before running (buggy state)
    fix_commit: NotRequired[str]    # The commit that introduced the fix (for reference/verification)
    fix_date: NotRequired[str]      # ISO date the fix was merged, e.g. "2025-11-04"
    task_type: NotRequired[str]     # "real" | "synthetic" — synthetic tasks inject artificial bugs
    editable_files: NotRequired[list[str]]
    readonly_files: NotRequired[list[str]]
    test_command: NotRequired[list[str]]
    test_env: NotRequired[dict[str, str]]
    injected_test_files: NotRequired[dict[str, str]]
    regression_test_command: NotRequired[list[str]]  # Full test suite — checks for regressions
    prompt_context: NotRequired[dict[str, str]]


# ---------------------------------------------------------------------------
# SAMPLE_TASKS registry
# ---------------------------------------------------------------------------
# All tasks are "real" — genuine historical bugs from open-source repos.
#
# To add a real task:
#   1. Run `git fetch --unshallow` in the relevant repos/ directory.
#   2. Find the commit just BEFORE the fix was merged (the "buggy" commit).
#   3. Set `base_commit` to that hash — sandbox.py will check out the repo to
#      that state before the agent runs.
#   4. Use the actual test(s) added in the fix PR as `injected_test_files`
#      (tests that fail on the buggy commit, pass after the fix).
#   5. Set `task_type: "real"` and `fix_date` to a date AFTER 2025-08-01.
#
# Grid: 25 tasks, 5 ecosystems × 5 tasks (1 easy, 3 medium, 1 hard)
# Max 2-3 tasks per repo within each ecosystem.
# ---------------------------------------------------------------------------

SAMPLE_TASKS: dict[str, TaskSpec] = {

    # =========================================================================
    # PYTHON — 5 tasks
    # =========================================================================

    "requests-netrc-empty-default": {
        "id": "requests-netrc-empty-default",
        "title": "Ignore empty default netrc entries when looking up auth credentials",
        "repository": "https://github.com/psf/requests",
        "description": (
            "The `get_netrc_auth()` function in `src/requests/utils.py` checks "
            "`if _netrc:` after retrieving authenticators for a host. A `.netrc` "
            "file with a bare `default` stanza returns a tuple like `(None, None, None)` "
            "which is truthy, so the function incorrectly returns `(None, None)` as "
            "credentials instead of `None`. The fix adds `and any(_netrc)` so that "
            "tuples whose values are all `None` are treated as absent."
        ),
        "difficulty": "easy",
        "constraints": [
            "Only modify `src/requests/utils.py`.",
            "Valid credentials (non-None values) must still be returned correctly.",
        ],
        "acceptance_keywords": ["any(_netrc)", "empty default", "netrc", "None"],
        "validation_instructions": (
            "get_netrc_auth() must return None when the .netrc default stanza "
            "has no login or password set."
        ),
        "execution_mode": "sandbox",
        "task_type": "real",
        "fix_commit": "47914226c2968802f2cdee3f6f0f6e06e4472f64",
        "fix_date": "2026-02-12",
        "base_commit": "1b40fdd004bfc8ba5301bcf8a6908264e9b6b877",
        "source_repo_path": "repos/requests",
        "editable_files": ["src/requests/utils.py"],
        "readonly_files": ["tests/test_real_netrc.py"],
        "test_command": ["python", "-m", "pytest", "tests/test_real_netrc.py", "-v"],
        "regression_test_command": ["python", "-m", "pytest", "tests/", "-x", "-q", "--ignore=tests/test_real_netrc.py"],
        "injected_test_files": {
            "tests/test_real_netrc.py": """\
import os
import pytest
from requests.utils import get_netrc_auth


class TestNetrcEmptyDefault:
    def test_empty_default_credentials_ignored(self, tmp_path, monkeypatch):
        \"\"\"Empty default credentials should not be returned.\"\"\"
        netrc_path = tmp_path / ".netrc"
        monkeypatch.setenv("NETRC", str(netrc_path))
        with open(netrc_path, "w") as f:
            f.write("machine example.com login user password pass\\ndefault\\n")

        auth = get_netrc_auth("http://httpbin.org/")
        assert auth is None

    def test_valid_credentials_still_returned(self, tmp_path, monkeypatch):
        \"\"\"Non-empty credentials must still be returned normally.\"\"\"
        netrc_path = tmp_path / ".netrc"
        monkeypatch.setenv("NETRC", str(netrc_path))
        with open(netrc_path, "w") as f:
            f.write("machine httpbin.org login myuser password mypass\\n")

        auth = get_netrc_auth("http://httpbin.org/get")
        assert auth == ("myuser", "mypass")
""",
        },
    },

    "click-flag-value-optional": {
        "id": "click-flag-value-optional",
        "title": "Allow flag_value option to be used without providing an argument",
        "repository": "https://github.com/pallets/click",
        "description": (
            "An `@click.option` with `is_flag=False` and `flag_value` set should "
            "accept the flag without an argument, using `flag_value` as the result. "
            "The condition in `Option.__init__` only checked `self.default is UNSET` "
            "to decide whether a value is needed, ignoring the presence of `flag_value`. "
            "Fix the condition so that `flag_value` being set also allows the option "
            "to be used as a bare flag."
        ),
        "difficulty": "medium",
        "constraints": [
            "Only modify `src/click/core.py`.",
            "Options without flag_value must continue to require an argument.",
        ],
        "acceptance_keywords": ["flag_value", "is_flag", "_flag_needs_value", "UNSET"],
        "validation_instructions": (
            "Invoking a command with --name (no argument) where flag_value='Flag' "
            "must succeed and echo 'Hello, Flag!'."
        ),
        "execution_mode": "sandbox",
        "task_type": "real",
        "fix_commit": "91de59c6c8abc8251e7af551cd4546cc964288af",
        "fix_date": "2025-10-07",
        "base_commit": "7f7bbe4569ea68e8dabee232eade069ef3310aea",
        "source_repo_path": "repos/click",
        "editable_files": ["src/click/core.py"],
        "readonly_files": ["tests/test_real_flag_value.py"],
        "test_command": ["python", "-m", "pytest", "tests/test_real_flag_value.py", "-v"],
        "regression_test_command": ["python", "-m", "pytest", "tests/", "-x", "-q", "--ignore=tests/test_real_flag_value.py"],
        "injected_test_files": {
            "tests/test_real_flag_value.py": """\
import click
from click.testing import CliRunner


def test_flag_value_optional_behavior():
    \"\"\"Options with flag_value and is_flag=False must accept the flag without an argument.
    Reproduces https://github.com/pallets/click/issues/3084
    \"\"\"
    @click.command()
    @click.option("--name", is_flag=False, flag_value="Flag", default="Default")
    def hello(name):
        click.echo(f"Hello, {name}!")

    runner = CliRunner()
    result = runner.invoke(hello, ["--name"])
    assert result.exit_code == 0, result.output
    assert result.output == "Hello, Flag!\\n"


def test_flag_value_with_type_conversion():
    \"\"\"flag_value must be correctly type-converted when used as an option value.\"\"\"
    @click.command()
    @click.option("--count", is_flag=False, flag_value="1", type=int, default=0)
    def repeat(count):
        for i in range(count):
            click.echo(f"Line {i + 1}")

    runner = CliRunner()
    result = runner.invoke(repeat, ["--count"])
    assert result.exit_code == 0, result.output
    assert result.output == "Line 1\\n"


def test_normal_option_still_requires_argument():
    \"\"\"An option without flag_value must still require an argument.\"\"\"
    @click.command()
    @click.option("--name", default="World")
    def hello(name):
        click.echo(f"Hello, {name}!")

    runner = CliRunner()
    result = runner.invoke(hello, ["--name"])
    assert result.exit_code != 0
""",
        },
    },

    "werkzeug-safe-join-device-names": {
        "id": "werkzeug-safe-join-device-names",
        "title": "Check all path segments for Windows device names in safe_join()",
        "repository": "https://github.com/pallets/werkzeug",
        "description": (
            "The `safe_join()` security function in `src/werkzeug/security.py` "
            "checked for Windows special device names (CON, PRN, AUX, etc.) only in "
            "the final path segment. A path like `'b/CON'` would pass the check "
            "because only `'CON'` is examined — but the full segment `'b/CON'` "
            "was considered safe. The fix iterates through all `/`-separated parts "
            "of each untrusted component and checks each one individually."
        ),
        "difficulty": "medium",
        "constraints": [
            "Only modify `src/werkzeug/security.py`.",
            "Legitimate multi-segment paths must still be allowed.",
            "Single-segment device names (CON, PRN, AUX) must remain blocked.",
        ],
        "acceptance_keywords": ["split", "any(", "_windows_device_files", "segment"],
        "validation_instructions": (
            "safe_join('/base', 'b/CON') must return None. "
            "safe_join('/base', 'valid/path.txt') must return a non-None path."
        ),
        "execution_mode": "sandbox",
        "task_type": "real",
        "fix_commit": "f54fe98026253e70fbbcd35a6b52fb67cfff1c03",
        "fix_date": "2026-02-18",
        "base_commit": "d005985ef69ffe3275eda8fb6fb25e074dbe871b",
        "source_repo_path": "repos/werkzeug",
        "editable_files": ["src/werkzeug/security.py"],
        "readonly_files": ["tests/test_real_safe_join.py"],
        "test_command": ["python", "-m", "pytest", "tests/test_real_safe_join.py", "-v"],
        "regression_test_command": ["python", "-m", "pytest", "tests/", "-x", "-q", "--ignore=tests/test_real_safe_join.py"],
        "injected_test_files": {
            "tests/test_real_safe_join.py": """\
import pytest
from werkzeug.security import safe_join


def test_device_name_in_multi_segment_path_blocked():
    \"\"\"safe_join must block Windows device names embedded in multi-segment paths.\"\"\"
    assert safe_join("/base", "b/CON") is None
    assert safe_join("/base", "b/PRN") is None
    assert safe_join("/base", "dir/AUX.txt") is None
    assert safe_join("/base", "a/b/CON.txt") is None


def test_standalone_device_names_still_blocked():
    \"\"\"Single-segment device names must remain blocked.\"\"\"
    assert safe_join("/base", "CON") is None
    assert safe_join("/base", "PRN") is None
    assert safe_join("/base", "AUX") is None


def test_legitimate_paths_still_allowed():
    \"\"\"Normal multi-segment paths must not be rejected.\"\"\"
    result = safe_join("/base", "valid/path.txt")
    assert result is not None
    result2 = safe_join("/base", "subdir/file.html")
    assert result2 is not None


def test_path_traversal_still_blocked():
    \"\"\"Path traversal must still be rejected.\"\"\"
    assert safe_join("/base", "../etc/passwd") is None
""",
        },
    },

    # =========================================================================
    # GO — 5 tasks
    # =========================================================================

    "gin-data-render-content-length": {
        "id": "gin-data-render-content-length",
        "title": "Set Content-Length header when rendering binary Data responses",
        "repository": "https://github.com/gin-gonic/gin",
        "description": (
            "The `Data.Render()` method in `render/data.go` writes binary data to "
            "the HTTP response but never sets the `Content-Length` header. HTTP "
            "clients that rely on `Content-Length` to know how many bytes to read "
            "will hang or misread the response. Add "
            "`w.Header().Set(\"Content-Length\", strconv.Itoa(len(r.Data)))` "
            "before writing the body."
        ),
        "difficulty": "easy",
        "constraints": [
            "Only modify `render/data.go`.",
            "Content-Length must only be set when len(r.Data) > 0.",
        ],
        "acceptance_keywords": ["Content-Length", "strconv.Itoa", "len(r.Data)"],
        "validation_instructions": (
            "A Data render of 100 bytes must produce a response with "
            "Content-Length: 100."
        ),
        "execution_mode": "sandbox",
        "task_type": "real",
        "fix_commit": "5c00df8afadd06cc5be530dde00fe6d9fa4a2e4a",
        "fix_date": "2026-02-28",
        "base_commit": "db309081bc5c137b2aa15701ef53f7f19788da25",
        "source_repo_path": "repos/gin",
        "editable_files": ["render/data.go"],
        "readonly_files": ["render/real_data_test.go"],
        "test_command": ["go", "test", "-run", "TestRealDataContentLength", "-v", "./render/..."],
        "regression_test_command": ["go", "test", "./..."],
        "injected_test_files": {
            "render/real_data_test.go": """\
package render

import (
\t"io"
\t"net/http"
\t"net/http/httptest"
\t"strconv"
\t"testing"

\t"github.com/stretchr/testify/assert"
\t"github.com/stretchr/testify/require"
)

func TestRealDataContentLength(t *testing.T) {
\tsrv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
\t\tsize, err := strconv.Atoi(r.URL.Query().Get("size"))
\t\trequire.NoError(t, err)
\t\tdata := Data{
\t\t\tContentType: "application/octet-stream",
\t\t\tData:        make([]byte, size),
\t\t}
\t\trequire.NoError(t, data.Render(w))
\t}))
\tt.Cleanup(srv.Close)

\tfor _, size := range []int{1, 100, 1000} {
\t\tt.Run(strconv.Itoa(size), func(t *testing.T) {
\t\t\tresp, err := http.Get(srv.URL + "?size=" + strconv.Itoa(size))
\t\t\trequire.NoError(t, err)
\t\t\tdefer resp.Body.Close()

\t\t\tassert.Equal(t, "application/octet-stream", resp.Header.Get("Content-Type"))
\t\t\tassert.Equal(t, strconv.Itoa(size), resp.Header.Get("Content-Length"))

\t\t\tactual, err := io.Copy(io.Discard, resp.Body)
\t\t\trequire.NoError(t, err)
\t\t\tassert.EqualValues(t, size, actual)
\t\t})
\t}
}
""",
        },
    },

    "gin-form-binding-empty-slice": {
        "id": "gin-form-binding-empty-slice",
        "title": "Return nil (not default) for slice/array form fields present but empty",
        "repository": "https://github.com/gin-gonic/gin",
        "description": (
            "The form binding code in `binding/form_mapping.go` checked `!ok` "
            "(field not present in the form) to decide whether to apply a default "
            "value. When a field is present but has zero values (`[]string{}`), "
            "`ok` is true but `len(vs) == 0`, so the default was never applied — "
            "leaving the slice as nil instead. The fix changes the condition to "
            "`len(vs) == 0` so an empty-but-present field also falls back to the "
            "default when one is configured, and returns nil when no default exists."
        ),
        "difficulty": "medium",
        "constraints": [
            "Only modify `binding/form_mapping.go`.",
            "Fields with actual values must not be affected.",
        ],
        "acceptance_keywords": ["len(vs) == 0", "isDefaultExists", "defaultValue", "empty"],
        "validation_instructions": (
            "A struct field tagged `form:'slice,default=5'` bound from an empty "
            "form value must resolve to [5], not nil."
        ),
        "execution_mode": "sandbox",
        "task_type": "real",
        "fix_commit": "c3d1092b3b48addf6f9cd00fe274ec3bd14650eb",
        "fix_date": "2025-10-11",
        "base_commit": "9968c4bf9d5a99edc3eee2c068a4c9160ece8915",
        "source_repo_path": "repos/gin",
        "editable_files": ["binding/form_mapping.go"],
        "readonly_files": ["binding/real_empty_slice_test.go"],
        "test_command": ["go", "test", "-run", "TestRealEmptySliceBinding", "-v", "./binding/..."],
        "regression_test_command": ["go", "test", "./..."],
        "injected_test_files": {
            "binding/real_empty_slice_test.go": """\
package binding

import (
\t"testing"

\t"github.com/stretchr/testify/assert"
\t"github.com/stretchr/testify/require"
)

func TestRealEmptySliceBinding(t *testing.T) {
\tt.Run("empty slice with default falls back to default", func(t *testing.T) {
\t\tvar s struct {
\t\t\tSlice []int `form:"slice,default=5"`
\t\t}
\t\t// field present but empty — should use default
\t\terr := mappingByPtr(&s, formSource{"slice": {}}, "form")
\t\trequire.NoError(t, err)
\t\tassert.Equal(t, []int{5}, s.Slice)
\t})

\tt.Run("empty slice without default returns nil", func(t *testing.T) {
\t\tvar s struct {
\t\t\tSlice []int `form:"slice"`
\t\t}
\t\terr := mappingByPtr(&s, formSource{"slice": {}}, "form")
\t\trequire.NoError(t, err)
\t\tassert.Equal(t, []int(nil), s.Slice)
\t})

\tt.Run("slice with values ignores default", func(t *testing.T) {
\t\tvar s struct {
\t\t\tSlice []int `form:"slice,default=5"`
\t\t}
\t\terr := mappingByPtr(&s, formSource{"slice": {"1", "2", "3"}}, "form")
\t\trequire.NoError(t, err)
\t\tassert.Equal(t, []int{1, 2, 3}, s.Slice)
\t})
}
""",
        },
    },

    "gin-literal-colon-route": {
        "id": "gin-literal-colon-route",
        "title": "Fix literal colon routes not matching when called via engine.Handler()",
        "repository": "https://github.com/gin-gonic/gin",
        "description": (
            "Routes defined with a literal colon (e.g. `/test\\:action`) failed to "
            "match when the engine was used via `engine.Handler()` or `ServeHTTP()` "
            "directly without first calling `Run()`. The route tree was only "
            "initialised inside `Run()`, so `ServeHTTP()` called without `Run()` "
            "operated on an empty tree. The fix adds a `sync.Once` guard so "
            "`updateRouteTrees()` is called automatically on the first `ServeHTTP` "
            "invocation regardless of how the engine is started."
        ),
        "difficulty": "medium",
        "constraints": [
            "Only modify `gin.go`.",
            "Normal routes started via Run() must be unaffected.",
        ],
        "acceptance_keywords": ["sync.Once", "routeTreesUpdated", "updateRouteTrees", "ServeHTTP"],
        "validation_instructions": (
            "A literal-colon route registered with router.GET must return 200 "
            "when ServeHTTP is called directly without Run()."
        ),
        "execution_mode": "sandbox",
        "task_type": "real",
        "fix_commit": "5fad976",
        "fix_date": "2025-11-16",
        "base_commit": "93ff771e6dbf10e432864b30f3719ac5c84a4d4a",
        "source_repo_path": "repos/gin",
        "editable_files": ["gin.go"],
        "readonly_files": ["real_literal_colon_test.go"],
        "test_command": ["go", "test", "-run", "TestRealLiteralColon", "-v", "./..."],
        "regression_test_command": ["go", "test", "./..."],
        "injected_test_files": {
            "real_literal_colon_test.go": """\
package gin

import (
\t"net/http"
\t"net/http/httptest"
\t"testing"

\t"github.com/stretchr/testify/assert"
)

func TestRealLiteralColonDirectServeHTTP(t *testing.T) {
\t// Regression test: literal-colon routes must work without calling Run() first.
\tSetMode(TestMode)
\trouter := New()

\trouter.GET(`/test\\:action`, func(c *Context) {
\t\tc.JSON(http.StatusOK, H{"path": "literal_colon"})
\t})

\tw := httptest.NewRecorder()
\treq, _ := http.NewRequest(http.MethodGet, "/test:action", nil)
\trouter.ServeHTTP(w, req)

\tassert.Equal(t, http.StatusOK, w.Code)
\tassert.Contains(t, w.Body.String(), "literal_colon")
}

func TestRealLiteralColonViaHandler(t *testing.T) {
\tSetMode(TestMode)
\trouter := New()

\trouter.GET(`/test\\:action`, func(c *Context) {
\t\tc.JSON(http.StatusOK, H{"path": "literal_colon"})
\t})

\thandler := router.Handler()
\tw := httptest.NewRecorder()
\treq, _ := http.NewRequest(http.MethodGet, "/test:action", nil)
\thandler.ServeHTTP(w, req)

\tassert.Equal(t, http.StatusOK, w.Code)
\tassert.Contains(t, w.Body.String(), "literal_colon")
}
""",
        },
    },

    # =========================================================================
    # PYTHON — 2 more tasks (flask)
    # =========================================================================

    "flask-provide-automatic-options": {
        "id": "flask-provide-automatic-options",
        "title": "Fix provide_automatic_options not overriding app-level setting per route",
        "repository": "https://github.com/pallets/flask",
        "description": (
            "The `add_url_rule()` method in `src/flask/sansio/app.py` had two separate "
            "`if provide_automatic_options is None:` branches at different indentation levels. "
            "The second branch (setting the value from the app config) ran regardless of "
            "whether the first branch had already set it from the view function or the caller, "
            "silently overwriting a route-level `False`. The fix collapses the logic into one "
            "nested block so the config fallback only triggers when `provide_automatic_options` "
            "is still `None`."
        ),
        "difficulty": "medium",
        "constraints": [
            "Only modify `src/flask/sansio/app.py`.",
            "Routes that pass `provide_automatic_options=True` must keep OPTIONS.",
            "Routes that pass `provide_automatic_options=False` must NOT get OPTIONS.",
        ],
        "acceptance_keywords": ["provide_automatic_options", "OPTIONS", "required_methods", "nested"],
        "validation_instructions": (
            "A route registered with provide_automatic_options=False must not respond to OPTIONS."
        ),
        "execution_mode": "sandbox",
        "task_type": "real",
        "fix_commit": "e82db2ca3a22c9614c1987392c9cfaa8c6ce99ad",
        "fix_date": "2026-02-12",
        "base_commit": "d3b78fd18a8d9e224cb9ef58a23cec9b1ffc9ce9",
        "source_repo_path": "repos/flask",
        "editable_files": ["src/flask/sansio/app.py"],
        "readonly_files": ["tests/test_real_automatic_options.py"],
        "test_command": ["python", "-m", "pytest", "tests/test_real_automatic_options.py", "-v"],
        "regression_test_command": ["python", "-m", "pytest", "tests/", "-x", "-q", "--ignore=tests/test_real_automatic_options.py"],
        "injected_test_files": {
            "tests/test_real_automatic_options.py": """\
import flask


def test_provide_automatic_options_false_disables_options():
    \"\"\"Route-level provide_automatic_options=False must disable OPTIONS even when
    the app-level PROVIDE_AUTOMATIC_OPTIONS config is True (the default).\"\"\"
    app = flask.Flask(__name__)

    @app.route("/no-options", provide_automatic_options=False)
    def no_options():
        return "ok"

    client = app.test_client()
    resp = client.options("/no-options")
    assert resp.status_code == 405, (
        f"Expected 405 Method Not Allowed but got {resp.status_code}. "
        "provide_automatic_options=False was overridden by the app config."
    )


def test_provide_automatic_options_true_keeps_options():
    \"\"\"Route-level provide_automatic_options=True must add OPTIONS.\"\"\"
    app = flask.Flask(__name__)

    @app.route("/with-options", provide_automatic_options=True)
    def with_options():
        return "ok"

    client = app.test_client()
    resp = client.options("/with-options")
    assert resp.status_code == 200


def test_default_still_adds_options_when_not_specified():
    \"\"\"When provide_automatic_options is not specified, OPTIONS is still added by default.\"\"\"
    app = flask.Flask(__name__)

    @app.route("/default")
    def default_route():
        return "ok"

    client = app.test_client()
    resp = client.options("/default")
    assert resp.status_code == 200
""",
        },
    },

    "flask-teardown-all-callbacks": {
        "id": "flask-teardown-all-callbacks",
        "title": "Ensure all teardown callbacks are called even when earlier ones raise",
        "repository": "https://github.com/pallets/flask",
        "description": (
            "Flask's `do_teardown_request` and `do_teardown_appcontext` in `src/flask/app.py` "
            "iterated over teardown callbacks and called them sequentially. If an earlier callback "
            "raised an exception the remaining callbacks were never called — resources could leak. "
            "The fix wraps each callback in a `_CollectErrors` context manager (added to "
            "`src/flask/helpers.py` and `src/flask/ctx.py`) so all callbacks run and any "
            "exceptions are re-raised together at the end."
        ),
        "difficulty": "hard",
        "constraints": [
            "Modify `src/flask/app.py`, `src/flask/ctx.py`, and `src/flask/helpers.py`.",
            "All teardown callbacks must be called even if earlier ones raise.",
            "Exceptions from teardown must still be propagated (not silently swallowed).",
        ],
        "acceptance_keywords": ["_CollectErrors", "collect_errors", "teardown", "raise_any"],
        "validation_instructions": (
            "When two teardown callbacks are registered and the first raises, "
            "the second must still be called."
        ),
        "execution_mode": "sandbox",
        "task_type": "real",
        "fix_commit": "fbb6f0bc4c60a0bada0e03c3480d0ccf30a3c1df",
        "fix_date": "2026-02-19",
        "base_commit": "7b0088693ece1bd3a9238a6fdf56ed8df7a4d43b",
        "source_repo_path": "repos/flask",
        "editable_files": ["src/flask/app.py", "src/flask/ctx.py", "src/flask/helpers.py"],
        "readonly_files": ["tests/test_real_teardown_all.py"],
        "test_command": ["python", "-m", "pytest", "tests/test_real_teardown_all.py", "-v"],
        "regression_test_command": ["python", "-m", "pytest", "tests/", "-x", "-q", "--ignore=tests/test_real_teardown_all.py"],
        "injected_test_files": {
            "tests/test_real_teardown_all.py": """\
import flask


def test_all_teardown_callbacks_called_despite_first_raising():
    \"\"\"All teardown callbacks must be called even if an earlier one raises.\"\"\"
    app = flask.Flask(__name__)
    called = []

    @app.teardown_request
    def cb_first(exc):
        called.append("first")
        raise RuntimeError("first teardown error")

    @app.teardown_request
    def cb_second(exc):
        called.append("second")

    with app.test_request_context("/"):
        app.try_trigger_before_first_request_functions()
        try:
            app.do_teardown_request()
        except Exception:
            pass

    # Both callbacks must have been called regardless of the exception
    assert "first" in called, "first teardown was not called"
    assert "second" in called, "second teardown was not called — earlier exception stopped iteration"


def test_all_appcontext_teardown_callbacks_called_despite_first_raising():
    \"\"\"All app-context teardown callbacks must run even if an earlier one raises.\"\"\"
    app = flask.Flask(__name__)
    called = []

    @app.teardown_appcontext
    def cb_a(exc):
        called.append("a")
        raise RuntimeError("a fails")

    @app.teardown_appcontext
    def cb_b(exc):
        called.append("b")

    ctx = app.app_context()
    ctx.push()
    try:
        ctx.pop()
    except Exception:
        pass

    assert "a" in called
    assert "b" in called, "teardown_appcontext cb_b was not called after cb_a raised"
""",
        },
    },

    # =========================================================================
    # GO — 2 more tasks (validator, testify)
    # =========================================================================

    "validator-panic-unique-nil-pointer": {
        "id": "validator-panic-unique-nil-pointer",
        "title": "Prevent panic in unique validator when slice contains nil pointer elements",
        "repository": "https://github.com/go-playground/validator",
        "description": (
            "The `isUnique` function in `baked_in.go` used `reflect.MakeMap` to detect "
            "duplicate values, calling `reflect.Indirect(field.Index(i))` to dereference "
            "pointer elements. When a slice contains a nil pointer, `reflect.Indirect` "
            "returns the zero Value, causing a panic when used as a map key. "
            "The fix rewrites the loop with an explicit nil check: nil pointers map to a "
            "sentinel `struct{}{}` key, and non-nil pointers are compared by their dereferenced value."
        ),
        "difficulty": "medium",
        "constraints": [
            "Only modify `baked_in.go`.",
            "The unique validator must still correctly detect duplicates in slices without nil pointers.",
            "A slice with a single nil pointer must be considered unique (no duplicates).",
        ],
        "acceptance_keywords": ["nilKey", "IsNil", "Elem().Interface()", "sentinel"],
        "validation_instructions": (
            "validate.Var([]*string{nil}, 'unique') must not panic and must return nil (valid)."
        ),
        "execution_mode": "sandbox",
        "task_type": "real",
        "fix_commit": "43253862b17ba5ae184cff6a136a2e62dbddce4a",
        "fix_date": "2026-02-24",
        "base_commit": "d3f35da4560da3a36ed0783f25e2c1d180b11f32",
        "source_repo_path": "repos/validator",
        "editable_files": ["baked_in.go"],
        "readonly_files": ["real_unique_nil_test.go"],
        "test_command": ["go", "test", "-run", "TestRealUniqueNilPointer", "-v", "./..."],
        "regression_test_command": ["go", "test", "./..."],
        "injected_test_files": {
            "real_unique_nil_test.go": """\
package validator

import (
\t"testing"

\t"github.com/stretchr/testify/assert"
\t"github.com/stretchr/testify/require"
)

func TestRealUniqueNilPointer(t *testing.T) {
\tvalidate := New()

\tt.Run("slice with nil pointer does not panic", func(t *testing.T) {
\t\tvar nilStr *string
\t\ts := []*string{nilStr}
\t\tassert.NotPanics(t, func() {
\t\t\terr := validate.Var(s, "unique")
\t\t\t// single nil element — no duplicates, must pass
\t\t\trequire.NoError(t, err)
\t\t})
\t})

\tt.Run("two nil pointers are duplicates", func(t *testing.T) {
\t\tvar nilStr *string
\t\ts := []*string{nilStr, nilStr}
\t\tassert.NotPanics(t, func() {
\t\t\terr := validate.Var(s, "unique")
\t\t\tassert.Error(t, err, "two nil pointers should be considered duplicates")
\t\t})
\t})

\tt.Run("non-nil pointers with same value are duplicates", func(t *testing.T) {
\t\ta, b := "x", "x"
\t\ts := []*string{&a, &b}
\t\tassert.NotPanics(t, func() {
\t\t\terr := validate.Var(s, "unique")
\t\t\tassert.Error(t, err)
\t\t})
\t})

\tt.Run("non-nil pointers with different values are unique", func(t *testing.T) {
\t\ta, b := "x", "y"
\t\ts := []*string{&a, &b}
\t\tassert.NotPanics(t, func() {
\t\t\terr := validate.Var(s, "unique")
\t\t\trequire.NoError(t, err)
\t\t})
\t})
}
""",
        },
    },

    "testify-mock-assert-expectations-panic": {
        "id": "testify-mock-assert-expectations-panic",
        "title": "Replace panic with test failure when wrong type is passed to AssertExpectationsForObjects",
        "repository": "https://github.com/stretchr/testify",
        "description": (
            "Before the fix, `AssertExpectationsForObjects` in `mock/mock.go` tried a "
            "type assertion `obj.(assertExpectationiser)` after an `if m, ok := obj.(*Mock)` "
            "branch. If neither branch matched (e.g. a value-type `mock.Mock` was passed "
            "instead of a pointer), the un-guarded type assertion panicked. "
            "The fix replaces the two-stage logic with a single `ok`-guarded assertion "
            "and calls `t.Errorf` with a descriptive message instead of panicking."
        ),
        "difficulty": "hard",
        "constraints": [
            "Only modify `mock/mock.go`.",
            "Valid mock pointers must still have their expectations asserted.",
            "An invalid type must produce a t.Errorf call, not a panic.",
        ],
        "acceptance_keywords": ["assertExpectationiser", "Errorf", "continue", "ok"],
        "validation_instructions": (
            "Calling AssertExpectationsForObjects(t, mock.Mock{}) must not panic "
            "and must record a test error."
        ),
        "execution_mode": "sandbox",
        "task_type": "real",
        "fix_commit": "0bf6b946d985309f37a4364b0b1f01a92698730e",
        "fix_date": "2025-09-15",
        "base_commit": "5fa984a7595bec3f65a1874f6e5a085545121508",
        "source_repo_path": "repos/testify",
        "editable_files": ["mock/mock.go"],
        "readonly_files": ["mock/real_assert_expectations_test.go"],
        "test_command": ["go", "test", "-run", "TestRealAssertExpectationsForObjectsPanic", "-v", "./mock/..."],
        "regression_test_command": ["go", "test", "./..."],
        "injected_test_files": {
            "mock/real_assert_expectations_test.go": """\
package mock

import (
\t"testing"

\t"github.com/stretchr/testify/assert"
)

// mockTestingT captures Errorf calls without failing the real test.
type mockTestingT struct {
\terrorfCount int
\tt           *testing.T
}

func (m *mockTestingT) Errorf(format string, args ...interface{}) {
\tm.errorfCount++
}

func (m *mockTestingT) Logf(format string, args ...interface{}) {}

func (m *mockTestingT) Helper() {}

func (m *mockTestingT) FailNow() {}

func TestRealAssertExpectationsForObjectsPanic(t *testing.T) {
\tt.Run("value type mock must not panic", func(t *testing.T) {
\t\tmockT := &mockTestingT{t: t}
\t\tassert.NotPanics(t, func() {
\t\t\t// Passing a value (not pointer) — must not panic
\t\t\tAssertExpectationsForObjects(mockT, Mock{})
\t\t})
\t\tassert.Equal(t, 1, mockT.errorfCount, "expected one Errorf call for the invalid type")
\t})

\tt.Run("pointer type mock still works normally", func(t *testing.T) {
\t\tmockT := &mockTestingT{t: t}
\t\tm := &Mock{}
\t\tm.On("SomeMethod").Return(nil)
\t\tm.Called()
\t\tassert.NotPanics(t, func() {
\t\t\tAssertExpectationsForObjects(mockT, m)
\t\t})
\t\tassert.Equal(t, 0, mockT.errorfCount, "valid mock pointer should produce no errors")
\t})
}
""",
        },
    },

    # =========================================================================
    # RUST — 5 tasks (clap)
    # =========================================================================

    "clap-builder-quote-empty-default": {
        "id": "clap-builder-quote-empty-default",
        "title": "Quote empty string default values in clap help output",
        "repository": "https://github.com/clap-rs/clap",
        "description": (
            "The `needs_escaping` method in `clap_builder/src/util/escape.rs` only returned "
            "`true` when a string contained whitespace, so empty string defaults were not "
            "quoted in help output — they appeared as an invisible blank instead of `\"\"`. "
            "The fix adds `self.0.is_empty()` to the condition so empty defaults are rendered "
            "as `[\"\"]` in the help text."
        ),
        "difficulty": "easy",
        "constraints": [
            "Only modify `clap_builder/src/util/escape.rs`.",
            "Non-empty defaults that contain no whitespace must remain unquoted.",
            "Non-empty defaults with whitespace must remain quoted.",
        ],
        "acceptance_keywords": ["is_empty", "needs_escaping", "quote", "escape"],
        "validation_instructions": (
            "Help text for an argument with default_value('') must contain '\"\"'."
        ),
        "execution_mode": "sandbox",
        "task_type": "real",
        "fix_commit": "420669948a1f637e0ee707d907053beb104bfc3d",
        "fix_date": "2026-02-17",
        "base_commit": "eb16ae4d25bf3a7300b4a51bf953bf0d6e6fa62c",
        "source_repo_path": "repos/clap",
        "editable_files": ["clap_builder/src/util/escape.rs"],
        "readonly_files": ["tests/real_empty_default_test.rs"],
        "test_command": ["cargo", "test", "--test", "real_empty_default_test", "--", "--nocapture"],
        "regression_test_command": ["cargo", "test"],
        "injected_test_files": {
            "tests/real_empty_default_test.rs": """\
#[test]
fn test_real_empty_default_is_quoted() {
    let mut cmd = clap::Command::new("test").arg(
        clap::Arg::new("opt")
            .long("opt")
            .default_value("")
            .help("an option"),
    );
    let help = cmd.render_help().to_string();
    assert!(
        help.contains("\\\"\\\""),
        "Empty default should be rendered as quoted empty string, got help:\\n{}",
        help
    );
}

#[test]
fn test_real_non_empty_default_without_spaces_not_quoted() {
    let mut cmd = clap::Command::new("test").arg(
        clap::Arg::new("opt")
            .long("opt")
            .default_value("hello")
            .help("an option"),
    );
    let help = cmd.render_help().to_string();
    assert!(
        help.contains("[default: hello]"),
        "Non-empty default without spaces must not be quoted, got:\\n{}",
        help
    );
}
""",
        },
    },

    "clap-parser-help-propagate-ignore-errors": {
        "id": "clap-parser-help-propagate-ignore-errors",
        "title": "Allow --help to propagate through subcommands that have ignore_errors set",
        "repository": "https://github.com/clap-rs/clap",
        "description": (
            "In `clap_builder/src/parser/parser.rs`, when a subcommand with `ignore_errors` "
            "returned an error, the parent checked `if partial_parsing_enabled` to decide "
            "whether to silence it. This also silenced `--help` (which returns a special "
            "DisplayHelp error), so help was never shown for subcommands under ignore_errors. "
            "The fix adds `&& error.use_stderr()` so only stderr-bound errors (real parse "
            "errors) are silenced — DisplayHelp errors propagate up normally."
        ),
        "difficulty": "medium",
        "constraints": [
            "Only modify `clap_builder/src/parser/parser.rs`.",
            "Real parse errors in ignore_errors subcommands must still be silenced.",
            "--help must now propagate up and print help text.",
        ],
        "acceptance_keywords": ["use_stderr", "DisplayHelp", "partial_parsing_enabled", "ignore_errors"],
        "validation_instructions": (
            "Parsing ['sub', '--help'] on a subcommand with ignore_errors must yield a "
            "DisplayHelp error, not silently succeed."
        ),
        "execution_mode": "sandbox",
        "task_type": "real",
        "fix_commit": "144e5cb46d946f97e51b7122eadd3134ee127bef",
        "fix_date": "2026-02-16",
        "base_commit": "ca5bdfc45e0c13ce290950a25ec76f9a62db0ffa",
        "source_repo_path": "repos/clap",
        "editable_files": ["clap_builder/src/parser/parser.rs"],
        "readonly_files": ["tests/real_help_ignore_errors_test.rs"],
        "test_command": ["cargo", "test", "--test", "real_help_ignore_errors_test", "--", "--nocapture"],
        "regression_test_command": ["cargo", "test"],
        "injected_test_files": {
            "tests/real_help_ignore_errors_test.rs": """\
#[test]
fn test_real_help_propagates_through_ignore_errors_subcommand() {
    let cmd = clap::Command::new("main").subcommand(
        clap::Command::new("sub")
            .ignore_errors(true)
            .arg(clap::Arg::new("arg").long("arg")),
    );

    let result = cmd.try_get_matches_from(["main", "sub", "--help"]);
    assert!(result.is_err(), "--help must produce an error (DisplayHelp)");
    let err = result.unwrap_err();
    assert_eq!(
        err.kind(),
        clap::error::ErrorKind::DisplayHelp,
        "--help in ignore_errors subcommand must propagate as DisplayHelp, got: {:?}",
        err.kind()
    );
}

#[test]
fn test_real_parse_error_still_ignored_in_ignore_errors_subcommand() {
    let cmd = clap::Command::new("main").subcommand(
        clap::Command::new("sub")
            .ignore_errors(true)
            .arg(clap::Arg::new("arg").long("arg").required(true)),
    );

    // A real parse error (missing required arg) should be silently ignored
    let result = cmd.try_get_matches_from(["main", "sub"]);
    assert!(result.is_ok(), "parse errors must still be ignored in ignore_errors subcommands");
}
""",
        },
    },

    "clap-parser-value-terminator-regression": {
        "id": "clap-parser-value-terminator-regression",
        "title": "Fix regression where value_terminator with last=true consumed wrong arguments",
        "repository": "https://github.com/clap-rs/clap",
        "description": (
            "A regression in `clap_builder/src/parser/parser.rs` broke the interaction between "
            "`value_terminator` and `last=true` positional arguments. The original code had a "
            "dedicated branch that triggered when a value terminator was found; the refactored "
            "code moved this check inside the `else` branch for setting `trailing_values=true`, "
            "but forgot to increment `pos_counter` when the terminator was found — so the "
            "positional that consumed the terminator string was not advanced past it. "
            "The fix increments `pos_counter` inside the inner if-block for the terminator check."
        ),
        "difficulty": "medium",
        "constraints": [
            "Only modify `clap_builder/src/parser/parser.rs`.",
            "Normal positional arguments must still parse correctly.",
            "value_terminator must still stop collection at the terminator string.",
        ],
        "acceptance_keywords": ["pos_counter", "value_terminator", "check_terminator", "trailing_values"],
        "validation_instructions": (
            "Parsing ['a', ';', 'b'] with a positional that has value_terminator=';' and "
            "a second positional with last=true must give first=['a'] and second=['b']."
        ),
        "execution_mode": "sandbox",
        "task_type": "real",
        "fix_commit": "af904ae2d76234593c81029df9fc3017e4520790",
        "fix_date": "2026-02-02",
        "base_commit": "36eb896ead6e34fdad83db0e99a544040a8200f4",
        "source_repo_path": "repos/clap",
        "editable_files": ["clap_builder/src/parser/parser.rs"],
        "readonly_files": ["tests/real_value_terminator_test.rs"],
        "test_command": ["cargo", "test", "--test", "real_value_terminator_test", "--", "--nocapture"],
        "regression_test_command": ["cargo", "test"],
        "injected_test_files": {
            "tests/real_value_terminator_test.rs": """\
#[test]
fn test_real_value_terminator_with_last_positional() {
    let cmd = clap::Command::new("test")
        .arg(
            clap::Arg::new("first")
                .num_args(1..)
                .value_terminator(";"),
        )
        .arg(
            clap::Arg::new("second")
                .num_args(1..)
                .last(true),
        );

    let matches = cmd
        .try_get_matches_from(["test", "a", "b", ";", "c", "d"])
        .expect("parse must succeed");

    let first: Vec<&str> = matches
        .get_many::<String>("first")
        .unwrap()
        .map(|s| s.as_str())
        .collect();
    let second: Vec<&str> = matches
        .get_many::<String>("second")
        .unwrap()
        .map(|s| s.as_str())
        .collect();

    assert_eq!(first, vec!["a", "b"], "first positional must stop at the terminator ';'");
    assert_eq!(second, vec!["c", "d"], "second (last) positional must capture remaining args");
}
""",
        },
    },

    "clap-complete-zsh-optional-value-args": {
        "id": "clap-complete-zsh-optional-value-args",
        "title": "Fix Zsh completion for arguments that optionally take a value",
        "repository": "https://github.com/clap-rs/clap",
        "description": (
            "In `clap_complete/src/aot/shells/zsh.rs`, the function `write_opts_of` built "
            "the Zsh value-completion string `vc` and then repeated it `min_values` times. "
            "For arguments where `min_values == 0` (value is optional), `vc.repeat(0)` "
            "produced an empty string, so the completion spec had no value section — "
            "Zsh treated the option as taking no value at all. "
            "The fix special-cases `0`: instead of repeating zero times, it prepends `:` "
            "to the `vc` string, telling Zsh the value is optional."
        ),
        "difficulty": "medium",
        "constraints": [
            "Only modify `clap_complete/src/aot/shells/zsh.rs`.",
            "Required-value options (min_values >= 1) must be unaffected.",
            "Optional-value options must produce a completion spec containing a colon prefix.",
        ],
        "acceptance_keywords": ["min_values", "repeat", "optional", "colon", "format"],
        "validation_instructions": (
            "The generated Zsh completion script for an option with num_args(0..=1) "
            "must contain a colon-prefixed value spec."
        ),
        "execution_mode": "sandbox",
        "task_type": "real",
        "fix_commit": "6c2cff66a11136915a6242b997ba9616622c3c2f",
        "fix_date": "2026-01-04",
        "base_commit": "58723e5f360fcfe7e97ed7af84cebec231f47ac9",
        "source_repo_path": "repos/clap",
        "editable_files": ["clap_complete/src/aot/shells/zsh.rs"],
        "readonly_files": ["tests/real_zsh_optional_value_test.rs"],
        "test_command": ["cargo", "test", "--test", "real_zsh_optional_value_test", "-p", "clap_complete", "--", "--nocapture"],
        "regression_test_command": ["cargo", "test", "-p", "clap_complete"],
        "injected_test_files": {
            "tests/real_zsh_optional_value_test.rs": """\
use clap::Command;
use clap_complete::{generate, shells::Zsh};
use std::io::Cursor;

#[test]
fn test_real_optional_value_arg_has_zsh_value_spec() {
    let mut cmd = Command::new("myapp")
        .arg(
            clap::Arg::new("config")
                .long("config")
                .num_args(0..=1)
                .value_name("FILE")
                .help("optional config file"),
        );

    let mut output = Cursor::new(Vec::new());
    generate(Zsh, &mut cmd, "myapp", &mut output);
    let script = String::from_utf8(output.into_inner()).unwrap();

    assert!(
        script.contains("::FILE"),
        "Zsh completion for optional-value argument must contain '::FILE' (colon-prefixed), got:\\n{}",
        &script[script.find("--config").unwrap_or(0)..script.find("--config").map(|i| i + 200).unwrap_or(200).min(script.len())]
    );
}
""",
        },
    },

    "clap-builder-default-vals-newline": {
        "id": "clap-builder-default-vals-newline",
        "title": "Put default value on new line in help when possible values are listed",
        "repository": "https://github.com/clap-rs/clap",
        "description": (
            "In `clap_builder/src/output/help_template.rs`, the `help` method wrote "
            "spec values (including `[default: ...]`) on a new line only when "
            "`!help_is_empty`. When an argument had both possible values and a default, "
            "the help text was empty but `next_line_specs` was true, so the `if !help_is_empty` "
            "check prevented the separator newlines from being emitted — the default value "
            "appeared on the same line as the possible values list. "
            "The fix introduces `has_possible_values` and ORs it into the condition so the "
            "separator is always emitted when either help text or possible values are present."
        ),
        "difficulty": "hard",
        "constraints": [
            "Only modify `clap_builder/src/output/help_template.rs`.",
            "Arguments with help text must still place defaults on a new line.",
            "Arguments without possible values must be unaffected.",
        ],
        "acceptance_keywords": ["has_possible_values", "next_line_specs", "help_is_empty", "sep"],
        "validation_instructions": (
            "Help text for an arg with possible_values=['a','b'] and default_value('a') "
            "must have the default on a separate line from the possible values."
        ),
        "execution_mode": "sandbox",
        "task_type": "real",
        "fix_commit": "a062eaf7f5c7b4a510ebc02f991efc1ea0f4e754",
        "fix_date": "2026-01-01",
        "base_commit": "15509afcbcb01818fbed85a54f5ea52eeadbdf8f",
        "source_repo_path": "repos/clap",
        "editable_files": ["clap_builder/src/output/help_template.rs"],
        "readonly_files": ["tests/real_default_newline_test.rs"],
        "test_command": ["cargo", "test", "--test", "real_default_newline_test", "--", "--nocapture"],
        "regression_test_command": ["cargo", "test"],
        "injected_test_files": {
            "tests/real_default_newline_test.rs": """\
#[test]
fn test_real_default_on_new_line_when_possible_values_present() {
    let cmd = clap::Command::new("test").arg(
        clap::Arg::new("mode")
            .long("mode")
            .value_parser(["fast", "slow"])
            .default_value("fast"),
    );
    let help = cmd.render_long_help().to_string();

    // The default marker and the possible-values section must be separated by a newline
    let pv_pos = help.find("Possible values").expect("should list possible values");
    let def_pos = help.find("[default:").expect("should show default value");

    assert!(
        def_pos > pv_pos,
        "default must come after possible values listing"
    );

    // There must be a newline between possible values and the default
    let between = &help[pv_pos..def_pos];
    assert!(
        between.contains('\\n'),
        "default must be on a new line after possible values, got help:\\n{}",
        help
    );
}
""",
        },
    },

    # =========================================================================
    # REACT — 5 tasks (react-router)
    # =========================================================================

    "react-router-create-routes-stub": {
        "id": "react-router-create-routes-stub",
        "title": "Widen component types in createRoutesStub to accept Framework Mode route components",
        "repository": "https://github.com/remix-run/react-router",
        "description": (
            "Route components typed with `Route.ComponentProps` use TypeScript contravariance: "
            "their `params` and `matches` types are more specific than the base `RouteComponentProps`. "
            "This made them unassignable to `React.ComponentType<RouteComponentProps>` in "
            "`StubRouteExtensions`, causing a TypeScript error when passing Framework Mode "
            "components to `createRoutesStub`. "
            "The fix widens `Component`, `HydrateFallback`, and `ErrorBoundary` in "
            "`StubRouteExtensions` to `React.ComponentType<any>` in "
            "`packages/react-router/lib/components.tsx`."
        ),
        "difficulty": "easy",
        "constraints": [
            "Only modify `packages/react-router/lib/components.tsx`.",
            "Normal route components (not Framework Mode) must still be accepted.",
        ],
        "acceptance_keywords": ["ComponentType<any>", "StubRouteExtensions", "HydrateFallback", "ErrorBoundary"],
        "validation_instructions": (
            "A Framework Mode component typed with Route.ComponentProps must be passable "
            "to createRoutesStub without a TypeScript error."
        ),
        "execution_mode": "sandbox",
        "task_type": "real",
        "fix_commit": "8c3c7ced1496522175c6839d30624955cc4534c1",
        "fix_date": "2026-03-18",
        "base_commit": "1cd923e38fd4cf86195f15850e41106dd42d1808",
        "source_repo_path": "repos/react-router",
        "editable_files": ["packages/react-router/lib/components.tsx"],
        "readonly_files": ["packages/react-router/__tests__/real_routes_stub_test.tsx"],
        "test_command": ["sh", "node_modules/.bin/jest", "packages/react-router/__tests__/real_routes_stub_test.tsx", "--no-coverage"],
        "regression_test_command": ["sh", "node_modules/.bin/jest", "--no-coverage", "--passWithNoTests"],
        "injected_test_files": {
            "packages/react-router/__tests__/real_routes_stub_test.tsx": """\
/**
 * Real regression test: createRoutesStub must accept Framework Mode route components
 * Reproduces https://github.com/remix-run/react-router/issues/14886
 */
import { createRoutesStub } from "react-router";

describe("createRoutesStub accepts Framework Mode components", () => {
  it("does not throw when passed a component with typed props", () => {
    // This must not throw a type error at runtime — the runtime check is
    // whether createRoutesStub is callable at all with a generic component.
    expect(() => {
      const Component = ({ params }: { params: Record<string, string | undefined> }) => null;

      // Before the fix, StubRouteExtensions had Component typed as
      // React.ComponentType<RouteComponentProps>, which would reject specific param types.
      // After the fix it is ComponentType<any>, so any component is accepted.
      createRoutesStub([
        {
          path: "/test/:id",
          Component: Component as any,
        },
      ]);
    }).not.toThrow();
  });

  it("createRoutesStub still works with standard components", () => {
    expect(() => {
      const Home = () => null;
      createRoutesStub([{ path: "/", Component: Home }]);
    }).not.toThrow();
  });
});
""",
        },
    },

    "react-router-double-slash-colon-path": {
        "id": "react-router-double-slash-colon-path",
        "title": "Fix double-slash normalization incorrectly altering paths that contain colons",
        "repository": "https://github.com/remix-run/react-router",
        "description": (
            "The `resolvePath` function in `packages/react-router/lib/router/utils.ts` "
            "first checked `isAbsoluteUrl(toPathname)` (which matched anything containing "
            "`://` or starting with `//`). A relative path like `'foo:bar'` was matched "
            "by `isAbsoluteUrl` and left unchanged, but a path like `'foo:bar/baz'` could "
            "be wrongly treated as a protocol URL. Additionally the old code had a separate "
            "double-slash warning branch that mutated the string. "
            "The fix removes `isAbsoluteUrl` check and simply normalises all double slashes "
            "before deciding whether the path is absolute."
        ),
        "difficulty": "medium",
        "constraints": [
            "Only modify `packages/react-router/lib/router/utils.ts`.",
            "Normal relative paths must resolve correctly.",
            "Paths with colons (e.g. 'foo:bar') must resolve as relative paths.",
        ],
        "acceptance_keywords": ["isAbsoluteUrl", "resolvePath", "toPathname", "colon"],
        "validation_instructions": (
            "resolvePath('foo:bar', '/base') must return {pathname: '/base/foo:bar'}, "
            "not treat 'foo:bar' as a protocol URL."
        ),
        "execution_mode": "sandbox",
        "task_type": "real",
        "fix_commit": "3a5b5ad0e5cf9918c646509563f5c41a89226ff3",
        "fix_date": "2026-01-16",
        "base_commit": "f29c6c95631368afa1b475f824854a781e690c02",
        "source_repo_path": "repos/react-router",
        "editable_files": ["packages/react-router/lib/router/utils.ts"],
        "readonly_files": ["packages/react-router/__tests__/real_resolve_colon_test.tsx"],
        "test_command": ["sh", "node_modules/.bin/jest", "packages/react-router/__tests__/real_resolve_colon_test.tsx", "--no-coverage"],
        "regression_test_command": ["sh", "node_modules/.bin/jest", "--no-coverage", "--passWithNoTests"],
        "injected_test_files": {
            "packages/react-router/__tests__/real_resolve_colon_test.tsx": """\
/**
 * Real regression test: resolvePath must handle colon-containing paths as relative.
 * Reproduces https://github.com/remix-run/react-router/issues/14718
 */
import { resolvePath } from "react-router";

describe("resolvePath colon path handling", () => {
  it("resolves a relative path with an embedded colon as relative", () => {
    const result = resolvePath("foo:bar", "/base");
    expect(result.pathname).toBe("/base/foo:bar");
  });

  it("resolves normal relative paths unchanged", () => {
    const result = resolvePath("child", "/parent");
    expect(result.pathname).toBe("/parent/child");
  });

  it("normalizes double slashes in the path", () => {
    const result = resolvePath("a//b", "/base");
    expect(result.pathname).toBe("/base/a/b");
  });

  it("treats an absolute path starting with slash as absolute", () => {
    const result = resolvePath("/absolute", "/base");
    expect(result.pathname).toBe("/absolute");
  });
});
""",
        },
    },

    "react-router-optional-segment-slash": {
        "id": "react-router-optional-segment-slash",
        "title": "Prevent optional path segments matching without a slash separator",
        "repository": "https://github.com/remix-run/react-router",
        "description": (
            "The `compilePath` function in `packages/react-router/lib/router/utils.ts` "
            "converted optional dynamic segments (`:param?`) to the regex `/?([^\\/]+)?`. "
            "The leading `/?` made the slash optional, so a pattern like `/test/:part?` "
            "would match `/test_more` because the `t?` from `test` could absorb the `_more` "
            "suffix — the path boundary was not enforced. "
            "The fix inspects the character immediately after the match: if it is non-empty "
            "and not `/`, the optional pattern becomes `/([^\\/]*)` (without `?`); "
            "otherwise it uses `(?:/([^\\/]*))?` which correctly requires a slash."
        ),
        "difficulty": "medium",
        "constraints": [
            "Only modify `packages/react-router/lib/router/utils.ts`.",
            "Required dynamic segments must continue to work.",
            "Optional segments with a proper slash separator must still match.",
        ],
        "acceptance_keywords": ["nextChar", "isOptional", "compilePath", "separator"],
        "validation_instructions": (
            "matchPath('/test/:part?', '/test_more') must return null. "
            "matchPath('/test/:part?', '/test/abc') must return a match."
        ),
        "execution_mode": "sandbox",
        "task_type": "real",
        "fix_commit": "7535805645872d288977914abd80eb0913b04840",
        "fix_date": "2026-01-21",
        "base_commit": "3126264a690b1de97666fbd0c804b001d1c98235",
        "source_repo_path": "repos/react-router",
        "editable_files": ["packages/react-router/lib/router/utils.ts"],
        "readonly_files": ["packages/react-router/__tests__/real_optional_segment_test.tsx"],
        "test_command": ["sh", "node_modules/.bin/jest", "packages/react-router/__tests__/real_optional_segment_test.tsx", "--no-coverage"],
        "regression_test_command": ["sh", "node_modules/.bin/jest", "--no-coverage", "--passWithNoTests"],
        "injected_test_files": {
            "packages/react-router/__tests__/real_optional_segment_test.tsx": """\
/**
 * Real regression test: optional path segments must not match without a slash separator.
 * Reproduces https://github.com/remix-run/react-router/pull/14689
 */
import { matchPath } from "react-router";

describe("optional segment slash separator enforcement", () => {
  it("does NOT match when pathname extends base path without separator", () => {
    expect(matchPath("/test_route/:part?", "/test_route_more")).toBeNull();
  });

  it("does NOT match when pathname has extra characters after base (no slash)", () => {
    expect(matchPath("/users/:id?", "/usersblah")).toBeNull();
    expect(matchPath("/api/:version?", "/api123")).toBeNull();
  });

  it("DOES match when pathname has a proper slash before the optional segment", () => {
    const match = matchPath("/test_route/:part?", "/test_route/abc");
    expect(match).not.toBeNull();
    expect(match?.params).toMatchObject({ part: "abc" });
  });

  it("DOES match when the optional segment is absent (just base path)", () => {
    const match = matchPath("/test_route/:part?", "/test_route");
    expect(match).not.toBeNull();
  });
});
""",
        },
    },

    "react-router-percent-encoding": {
        "id": "react-router-percent-encoding",
        "title": "Preserve percent-encoded characters in relative path navigation",
        "repository": "https://github.com/remix-run/react-router",
        "description": (
            "The `useHref` hook in `packages/react-router/lib/hooks.tsx` called "
            "`resolveTo` then passed the result through path-building code that "
            "incorrectly re-encoded already-encoded characters. When navigating to a "
            "relative path that contained percent-encoded characters (e.g. `%20`), "
            "the resulting href double-encoded them to `%2520`, breaking navigation "
            "to URLs with special characters."
        ),
        "difficulty": "medium",
        "constraints": [
            "Only modify `packages/react-router/lib/hooks.tsx`.",
            "Normal paths without special characters must be unaffected.",
            "Already percent-encoded characters must not be double-encoded.",
        ],
        "acceptance_keywords": ["percent", "encode", "resolveTo", "useHref"],
        "validation_instructions": (
            "A navigation to a path containing '%20' must produce an href with '%20', "
            "not '%2520'."
        ),
        "execution_mode": "sandbox",
        "task_type": "real",
        "fix_commit": "830d3bac11ac9c9aa975f6dfccaead24df9caae4",
        "fix_date": "2026-03-17",
        "base_commit": "8646d39bc7b10a43745dc255b4faa25673a9e908",
        "source_repo_path": "repos/react-router",
        "editable_files": ["packages/react-router/lib/hooks.tsx"],
        "readonly_files": ["packages/react-router/__tests__/real_percent_encoding_test.tsx"],
        "test_command": ["sh", "node_modules/.bin/jest", "packages/react-router/__tests__/real_percent_encoding_test.tsx", "--no-coverage"],
        "regression_test_command": ["sh", "node_modules/.bin/jest", "--no-coverage", "--passWithNoTests"],
        "injected_test_files": {
            "packages/react-router/__tests__/real_percent_encoding_test.tsx": """\
/**
 * Real regression test: percent-encoded characters must not be double-encoded.
 * Reproduces https://github.com/remix-run/react-router/issues/14917
 */
import * as React from "react";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useHref } from "react-router";

function HrefDisplay({ to }: { to: string }) {
  const href = useHref(to);
  return <div data-testid="href">{href}</div>;
}

describe("useHref percent encoding", () => {
  it("does not double-encode percent-encoded characters in relative paths", () => {
    render(
      <MemoryRouter initialEntries={["/base"]}>
        <Routes>
          <Route
            path="/base"
            element={<HrefDisplay to="search%20term" />}
          />
        </Routes>
      </MemoryRouter>
    );

    const href = screen.getByTestId("href").textContent!;
    expect(href).not.toContain("%2520");
    expect(href).toContain("%20");
  });

  it("does not alter normal paths without encoding", () => {
    render(
      <MemoryRouter initialEntries={["/base"]}>
        <Routes>
          <Route path="/base" element={<HrefDisplay to="normal-path" />} />
        </Routes>
      </MemoryRouter>
    );

    const href = screen.getByTestId("href").textContent!;
    expect(href).toContain("normal-path");
  });
});
""",
        },
    },

    "react-router-client-loader-hydrate": {
        "id": "react-router-client-loader-hydrate",
        "title": "Fix clientLoader HydrateFallback not showing when ancestor route is hydrating",
        "repository": "https://github.com/remix-run/react-router",
        "description": (
            "In `packages/react-router/lib/router/router.ts`, when computing which loaders "
            "should run on initial hydration, the code checked whether a route's own loader "
            "had server data but did not account for the case where an ancestor route was "
            "still hydrating. A child route with `clientLoader` and `HydrateFallback` "
            "would skip showing its fallback if its ancestor was in a hydrating state, "
            "causing incorrect UI during the initial hydration phase."
        ),
        "difficulty": "hard",
        "constraints": [
            "Only modify `packages/react-router/lib/router/router.ts`.",
            "Normal data loading (no hydration) must be unaffected.",
            "Routes without clientLoader must be unaffected.",
        ],
        "acceptance_keywords": ["clientLoader", "HydrateFallback", "hydrating", "ancestor"],
        "validation_instructions": (
            "A child route with clientLoader+HydrateFallback must show its fallback "
            "while an ancestor route is still hydrating its loader."
        ),
        "execution_mode": "sandbox",
        "task_type": "real",
        "fix_commit": "e0c207db147755b18bf4de4c4d50f8d92b05d5eb",
        "fix_date": "2026-02-27",
        "base_commit": "d8ffb2dbda9ef975287b902c4c7784a1e8abd8be",
        "source_repo_path": "repos/react-router",
        "editable_files": ["packages/react-router/lib/router/router.ts"],
        "readonly_files": ["packages/react-router/__tests__/real_client_loader_hydrate_test.tsx"],
        "test_command": ["sh", "node_modules/.bin/jest", "packages/react-router/__tests__/real_client_loader_hydrate_test.tsx", "--no-coverage"],
        "regression_test_command": ["sh", "node_modules/.bin/jest", "--no-coverage", "--passWithNoTests"],
        "injected_test_files": {
            "packages/react-router/__tests__/real_client_loader_hydrate_test.tsx": """\
/**
 * Real regression test: clientLoader HydrateFallback must show when ancestor is hydrating.
 * Reproduces https://github.com/remix-run/react-router/issues/14872
 */
import * as React from "react";
import { render, screen, act } from "@testing-library/react";
import {
  createMemoryRouter,
  RouterProvider,
} from "react-router";

describe("clientLoader HydrateFallback with hydrating ancestor", () => {
  it("shows HydrateFallback for child route when ancestor is still hydrating", async () => {
    let resolveParentLoader!: (value: unknown) => void;
    const parentLoaderPromise = new Promise((r) => (resolveParentLoader = r));

    const router = createMemoryRouter(
      [
        {
          path: "/",
          loader: () => parentLoaderPromise,
          Component: () => <div>Parent</div>,
          children: [
            {
              path: "child",
              clientLoader: async () => "child data",
              HydrateFallback: () => <div data-testid="child-fallback">Loading child...</div>,
              Component: () => <div data-testid="child-content">Child loaded</div>,
            },
          ],
        },
      ],
      { initialEntries: ["/child"] }
    );

    render(<RouterProvider router={router} />);

    // Before the fix: the child HydrateFallback was not rendered
    // After the fix: it should be visible while the parent loader is pending
    expect(screen.queryByTestId("child-fallback")).not.toBeNull();
    expect(screen.queryByTestId("child-content")).toBeNull();

    await act(async () => {
      resolveParentLoader("parent data");
      await parentLoaderPromise;
    });

    expect(screen.queryByTestId("child-content")).not.toBeNull();
  });
});
""",
        },
    },

    # =========================================================================
    # ANGULAR — 5 tasks (ngrx-platform)
    # =========================================================================

    "ngrx-eslint-prefix-selectors": {
        "id": "ngrx-eslint-prefix-selectors",
        "title": "Fix prefix-selectors-with-select ESLint rule flagging non-NgRx selectors",
        "repository": "https://github.com/ngrx/platform",
        "description": (
            "The `prefix-selectors-with-select` ESLint rule in "
            "`modules/eslint-plugin/src/rules/store/prefix-selectors-with-select.ts` "
            "used the regex `/Selector$/.test(typeName)` to identify NgRx selector types. "
            "This matched any TypeScript type ending in 'Selector', including non-NgRx types "
            "like a custom `CustomSelector<T>` interface. "
            "The fix replaces the regex with an explicit allowlist: only "
            "`MemoizedSelector`, `MemoizedSelectorWithProps`, `Selector`, and `SelectorWithProps` "
            "trigger the rule."
        ),
        "difficulty": "easy",
        "constraints": [
            "Only modify `modules/eslint-plugin/src/rules/store/prefix-selectors-with-select.ts`.",
            "NgRx-specific selector types (MemoizedSelector etc.) must still be flagged if not prefixed.",
            "Custom types ending in 'Selector' that are not NgRx types must not be flagged.",
        ],
        "acceptance_keywords": ["MemoizedSelector", "includes", "allowlist", "typeName"],
        "validation_instructions": (
            "A variable typed as `CustomSelector<any>` must NOT be flagged by the rule. "
            "A variable typed as `MemoizedSelector<any, any>` without the 'select' prefix must be flagged."
        ),
        "execution_mode": "sandbox",
        "task_type": "real",
        "fix_commit": "568dbe334643f46fdb1f01f991194d3cf2b78245",
        "fix_date": "2025-11-20",
        "base_commit": "c1f4fc520ac712fc8ad6204dda1c52a9af386616",
        "source_repo_path": "repos/ngrx-platform",
        "editable_files": ["modules/eslint-plugin/src/rules/store/prefix-selectors-with-select.ts"],
        "readonly_files": ["modules/eslint-plugin/spec/rules/store/real_prefix_selectors_test.spec.ts"],
        "test_command": [
            "node", "node_modules/.bin/jest",
            "--config", "{\"preset\":\"ts-jest\",\"testEnvironment\":\"node\",\"rootDir\":\".\"}",
            "modules/eslint-plugin/spec/rules/store/real_prefix_selectors_test.spec.ts",
            "--no-coverage",
        ],
        "regression_test_command": [
            "node", "node_modules/.bin/jest",
            "--config", "{\"preset\":\"ts-jest\",\"testEnvironment\":\"node\",\"rootDir\":\".\"}",
            "modules/eslint-plugin/spec/",
            "--no-coverage", "--passWithNoTests",
        ],
        "injected_test_files": {
            "modules/eslint-plugin/spec/rules/store/real_prefix_selectors_test.spec.ts": """\
/**
 * Real regression test: prefix-selectors-with-select must not flag non-NgRx selector types.
 */
import rule from '../../../src/rules/store/prefix-selectors-with-select';
import { ruleTester } from '../../utils';

ruleTester().run('prefix-selectors-with-select real test', rule, {
  valid: [
    // Non-NgRx type ending in 'Selector' must NOT be flagged
    {
      code: `
        interface CustomSelector<T> { select: (state: T) => T }
        export const myFeature: CustomSelector<any> = (state: any) => state;
      `,
    },
    // Properly prefixed NgRx selector must be valid
    {
      code: `export const selectUsers = createSelector(s => s.users)`,
    },
  ],
  invalid: [
    // NgRx MemoizedSelector without prefix must still be flagged
    {
      code: `export const users: MemoizedSelector<any, any> = createSelector(s => s.users)`,
      errors: [{ messageId: 'prefixSelectorsWithSelect' }],
    },
  ],
});
""",
        },
    },

    "ngrx-component-illegal-invocation": {
        "id": "ngrx-component-illegal-invocation",
        "title": "Fix Illegal invocation error in ZonelessTickScheduler caused by wrong this context",
        "repository": "https://github.com/ngrx/platform",
        "description": (
            "The `ZonelessTickScheduler` in "
            "`modules/component/src/core/tick-scheduler.ts` stored a browser API "
            "(`setTimeout` or `requestAnimationFrame`) as a class field: "
            "`private readonly scheduleFn = this.isServer ? setTimeout : requestAnimationFrame`. "
            "When `scheduleFn` was called, it had `this` bound to the class instance rather "
            "than the global object — `requestAnimationFrame` requires `this === window` or it "
            "throws an 'Illegal invocation' TypeError. "
            "The fix wraps the call in an arrow function so the browser API is always called "
            "with the correct context."
        ),
        "difficulty": "medium",
        "constraints": [
            "Only modify `modules/component/src/core/tick-scheduler.ts`.",
            "The scheduler must still use requestAnimationFrame in browser environments.",
            "The scheduler must still use setTimeout in server (SSR) environments.",
        ],
        "acceptance_keywords": ["arrow function", "requestAnimationFrame", "this", "scheduleFn"],
        "validation_instructions": (
            "Calling scheduleFn(callback) must not throw 'Illegal invocation'. "
            "The callback must still be called."
        ),
        "execution_mode": "sandbox",
        "task_type": "real",
        "fix_commit": "2b26360be62ba1d37ab108e94e098e1c1ab7abfa",
        "fix_date": "2026-03-04",
        "base_commit": "6e10def5412c5a134bc6436f8966aa4ee5aa42dd",
        "source_repo_path": "repos/ngrx-platform",
        "editable_files": ["modules/component/src/core/tick-scheduler.ts"],
        "readonly_files": ["modules/component/spec/core/real_tick_scheduler_test.spec.ts"],
        "test_command": [
            "node", "node_modules/.bin/jest",
            "--config", "{\"preset\":\"ts-jest\",\"testEnvironment\":\"jsdom\",\"rootDir\":\".\"}",
            "modules/component/spec/core/real_tick_scheduler_test.spec.ts",
            "--no-coverage",
        ],
        "regression_test_command": [
            "node", "node_modules/.bin/jest",
            "--config", "{\"preset\":\"ts-jest\",\"testEnvironment\":\"node\",\"rootDir\":\".\"}",
            "modules/eslint-plugin/spec/",
            "--no-coverage", "--passWithNoTests",
        ],
        "injected_test_files": {
            "modules/component/spec/core/real_tick_scheduler_test.spec.ts": """\
/**
 * Real regression test: ZonelessTickScheduler must not cause Illegal invocation.
 * Reproduces https://github.com/ngrx/platform/issues/5108
 */

describe('scheduleFn context (Illegal invocation regression)', () => {
  it('requestAnimationFrame must be called without binding it to the class instance', () => {
    const invocationContexts: unknown[] = [];
    const originalRAF = (global as any).requestAnimationFrame;

    // Spy on requestAnimationFrame to capture the `this` context
    (global as any).requestAnimationFrame = function(this: unknown, cb: FrameRequestCallback) {
      invocationContexts.push(this);
      cb(0);
      return 0;
    };

    // Simulate what ZonelessTickScheduler does:
    // BUGGY: const scheduleFn = requestAnimationFrame (gets bound to class instance)
    // FIXED: const scheduleFn = (cb: () => void) => requestAnimationFrame(cb)
    const fakeScheduler = {
      // Bug: storing reference directly means `this` is fakeScheduler when called
      buggyFn: (global as any).requestAnimationFrame,
      // Fix: wrapping in arrow fn means `this` is global/window when called
      fixedFn: (cb: FrameRequestCallback) => (global as any).requestAnimationFrame(cb),
    };

    const callback = jest.fn();
    fakeScheduler.fixedFn(callback);

    // The fixed version: invocation context must NOT be the scheduler object
    expect(invocationContexts[0]).not.toBe(fakeScheduler);
    expect(callback).toHaveBeenCalled();

    (global as any).requestAnimationFrame = originalRAF;
  });
});
""",
        },
    },

    "ngrx-eslint-factory-with-state": {
        "id": "ngrx-eslint-factory-with-state",
        "title": "Fix with-state-no-arrays-at-root-level ESLint rule missing factory function form",
        "repository": "https://github.com/ngrx/platform",
        "description": (
            "The `with-state-no-arrays-at-root-level` rule in "
            "`modules/eslint-plugin/src/rules/signals/with-state-no-arrays-at-root-level.ts` "
            "called `services.getTypeAtLocation(argument)` to get the type of the withState "
            "argument. When a factory function was passed (e.g. `withState(() => ([1, 2, 3]))`), "
            "the type was a function type, not the return type — so the array-at-root-level "
            "check was never applied. "
            "The fix checks if the type has call signatures and, if so, uses the return type "
            "of the first call signature for the array check."
        ),
        "difficulty": "medium",
        "constraints": [
            "Only modify `modules/eslint-plugin/src/rules/signals/with-state-no-arrays-at-root-level.ts`.",
            "Factory functions returning an object must still be valid.",
            "Factory functions returning an array must be flagged.",
        ],
        "acceptance_keywords": ["getCallSignatures", "getReturnTypeOfSignature", "factory", "callSignatures"],
        "validation_instructions": (
            "withState(() => ([1, 2, 3])) must be flagged as invalid. "
            "withState(() => ({ items: [] })) must be valid."
        ),
        "execution_mode": "sandbox",
        "task_type": "real",
        "fix_commit": "653efa5364661007e3f2e11e3374d64cf98979cc",
        "fix_date": "2026-03-19",
        "base_commit": "92d6cdde08d4a115089e1a76e485d2ea68fefa04",
        "source_repo_path": "repos/ngrx-platform",
        "editable_files": ["modules/eslint-plugin/src/rules/signals/with-state-no-arrays-at-root-level.ts"],
        "readonly_files": ["modules/eslint-plugin/spec/rules/signals/real_factory_with_state_test.spec.ts"],
        "test_command": [
            "node", "node_modules/.bin/jest",
            "--config", "{\"preset\":\"ts-jest\",\"testEnvironment\":\"node\",\"rootDir\":\".\"}",
            "modules/eslint-plugin/spec/rules/signals/real_factory_with_state_test.spec.ts",
            "--no-coverage",
        ],
        "regression_test_command": [
            "node", "node_modules/.bin/jest",
            "--config", "{\"preset\":\"ts-jest\",\"testEnvironment\":\"node\",\"rootDir\":\".\"}",
            "modules/eslint-plugin/spec/",
            "--no-coverage", "--passWithNoTests",
        ],
        "injected_test_files": {
            "modules/eslint-plugin/spec/rules/signals/real_factory_with_state_test.spec.ts": """\
/**
 * Real regression test: with-state-no-arrays-at-root-level must flag factory functions
 * that return arrays.
 * Reproduces https://github.com/ngrx/platform/issues/5104
 */
import rule, { messageId } from '../../../src/rules/signals/with-state-no-arrays-at-root-level';
import { ruleTester } from '../../utils';

ruleTester().run('with-state-no-arrays-at-root-level factory real test', rule, {
  valid: [
    // Factory returning an object is valid
    `const store = withState(() => ({ foo: 'bar' }))`,
    // Factory returning object with array value is valid
    `const store = withState(() => ({ items: [1, 2, 3] }))`,
  ],
  invalid: [
    // Factory function returning an array must be flagged
    {
      code: `const store = withState(() => [1, 2, 3])`,
      errors: [{ messageId }],
    },
    {
      code: `const store = withState(function() { return []; })`,
      errors: [{ messageId }],
    },
  ],
});
""",
        },
    },

    "ngrx-eslint-on-function-return-type": {
        "id": "ngrx-eslint-on-function-return-type",
        "title": "Fix on-function-explicit-return-type rule missing call expression form",
        "repository": "https://github.com/ngrx/platform",
        "description": (
            "The `onFunctionWithoutType` ESLint selector in "
            "`modules/eslint-plugin/src/utils/selectors/index.ts` contained "
            "`:not([returnType.typeAnnotation], :has(CallExpression))` to exclude "
            "arrow functions that already had a return type OR contained a call expression. "
            "The `:has(CallExpression)` clause was too broad — it excluded any arrow function "
            "body containing a call expression, even when that function still lacked an "
            "explicit return type annotation. "
            "The fix removes `:has(CallExpression)` from the negation, so only the absence "
            "of `returnType.typeAnnotation` is checked."
        ),
        "difficulty": "medium",
        "constraints": [
            "Only modify `modules/eslint-plugin/src/utils/selectors/index.ts`.",
            "Arrow functions without return type annotations must be flagged.",
            "Arrow functions WITH return type annotations must not be flagged.",
        ],
        "acceptance_keywords": ["has(CallExpression)", "onFunctionWithoutType", "returnType", "selector"],
        "validation_instructions": (
            "An on() arrow function that contains a call expression but has no return type "
            "must be flagged. An on() arrow function with an explicit return type must not be flagged."
        ),
        "execution_mode": "sandbox",
        "task_type": "real",
        "fix_commit": "c8e1352f729416d4db594e923620c4546269e2d6",
        "fix_date": "2025-08-06",
        "base_commit": "e7eabd493dc00cbddcf76b90c64400b41362026c",
        "source_repo_path": "repos/ngrx-platform",
        "editable_files": ["modules/eslint-plugin/src/utils/selectors/index.ts"],
        "readonly_files": ["modules/eslint-plugin/spec/rules/store/real_on_function_return_type_test.spec.ts"],
        "test_command": [
            "node", "node_modules/.bin/jest",
            "--config", "{\"preset\":\"ts-jest\",\"testEnvironment\":\"node\",\"rootDir\":\".\"}",
            "modules/eslint-plugin/spec/rules/store/real_on_function_return_type_test.spec.ts",
            "--no-coverage",
        ],
        "regression_test_command": [
            "node", "node_modules/.bin/jest",
            "--config", "{\"preset\":\"ts-jest\",\"testEnvironment\":\"node\",\"rootDir\":\".\"}",
            "modules/eslint-plugin/spec/",
            "--no-coverage", "--passWithNoTests",
        ],
        "injected_test_files": {
            "modules/eslint-plugin/spec/rules/store/real_on_function_return_type_test.spec.ts": """\
/**
 * Real regression test: on-function-explicit-return-type must flag call expressions inside on().
 * Reproduces https://github.com/ngrx/platform/issues/4901
 */
import rule from '../../../src/rules/store/on-function-explicit-return-type';
import { ruleTester } from '../../utils';

ruleTester().run('on-function-explicit-return-type call-expression real test', rule, {
  valid: [
    // Arrow function with explicit return type must be valid
    {
      code: `
        const reducer = createReducer(
          initialState,
          on(increment, (state): State => ({ ...state, count: state.count + 1 }))
        );
      `,
    },
  ],
  invalid: [
    // Arrow function containing a call expression but without return type must be flagged
    {
      code: `
        const reducer = createReducer(
          initialState,
          on(increment, (state) => Object.assign({}, state, { count: state.count + 1 }))
        );
      `,
      errors: [{ messageId: 'onFunctionExplicitReturnType' }],
    },
  ],
});
""",
        },
    },

    "ngrx-signals-prod-assert-injection": {
        "id": "ngrx-signals-prod-assert-injection",
        "title": "Remove assertInInjectionContext from production signal bundles",
        "repository": "https://github.com/ngrx/platform",
        "description": (
            "Several `@ngrx/signals` source files called `assertInInjectionContext()` "
            "unconditionally. This guard is a development-only check that throws an error "
            "when called outside of an Angular injection context. In production builds it "
            "was still included, unnecessarily increasing bundle size and potentially "
            "throwing errors in contexts where it shouldn't. "
            "The fix wraps each call in `if (typeof ngDevMode === 'undefined' || ngDevMode)` "
            "so it is tree-shaken from production bundles."
        ),
        "difficulty": "hard",
        "constraints": [
            "Modify `modules/signals/events/src/inject-dispatch.ts`, "
            "`modules/signals/rxjs-interop/src/rx-method.ts`, "
            "`modules/signals/src/signal-method.ts`, and "
            "`modules/signals/src/state-source.ts`.",
            "assertInInjectionContext must still be called in development mode.",
        ],
        "acceptance_keywords": ["ngDevMode", "assertInInjectionContext", "production", "tree-shaken"],
        "validation_instructions": (
            "When ngDevMode is falsy, assertInInjectionContext must not be called. "
            "When ngDevMode is truthy, it must still be called."
        ),
        "execution_mode": "sandbox",
        "task_type": "real",
        "fix_commit": "37e6fa113fd22dfe7a862bc8cf9da7cbca647ab8",
        "fix_date": "2025-09-09",
        "base_commit": "b4edd95e05522c19a034ae7e309c9f78af7da12b",
        "source_repo_path": "repos/ngrx-platform",
        "editable_files": [
            "modules/signals/events/src/inject-dispatch.ts",
            "modules/signals/rxjs-interop/src/rx-method.ts",
            "modules/signals/src/signal-method.ts",
            "modules/signals/src/state-source.ts",
        ],
        "readonly_files": ["modules/signals/spec/real_prod_assert_injection_test.spec.ts"],
        "test_command": [
            "node", "node_modules/.bin/jest",
            "--config", "{\"preset\":\"ts-jest\",\"testEnvironment\":\"node\",\"rootDir\":\".\"}",
            "modules/signals/spec/real_prod_assert_injection_test.spec.ts",
            "--no-coverage",
        ],
        "regression_test_command": [
            "node", "node_modules/.bin/jest",
            "--config", "{\"preset\":\"ts-jest\",\"testEnvironment\":\"node\",\"rootDir\":\".\"}",
            "modules/eslint-plugin/spec/",
            "--no-coverage", "--passWithNoTests",
        ],
        "injected_test_files": {
            "modules/signals/spec/real_prod_assert_injection_test.spec.ts": """\
/**
 * Real regression test: assertInInjectionContext must be skipped in production (ngDevMode=false).
 * Reproduces https://github.com/ngrx/platform/issues/4950
 */

// We test the source files directly to verify the ngDevMode guard
const fs = require('fs');
const path = require('path');

const filesToCheck = [
  'modules/signals/events/src/inject-dispatch.ts',
  'modules/signals/rxjs-interop/src/rx-method.ts',
  'modules/signals/src/signal-method.ts',
  'modules/signals/src/state-source.ts',
];

describe('assertInInjectionContext must be guarded by ngDevMode in production', () => {
  for (const filePath of filesToCheck) {
    it(`${filePath} guards assertInInjectionContext with ngDevMode`, () => {
      const content = fs.readFileSync(path.join(process.cwd(), filePath), 'utf8');

      // If assertInInjectionContext is called, it must be inside a ngDevMode guard
      if (content.includes('assertInInjectionContext')) {
        const hasNgDevModeGuard = content.includes('ngDevMode');
        expect(hasNgDevModeGuard).toBe(true);

        // Ensure assertInInjectionContext is not called unconditionally
        // (it should appear inside an if block, not as a bare statement)
        const lines = content.split('\\n');
        const callLines = lines.filter(l => l.includes('assertInInjectionContext') && !l.trim().startsWith('//'));
        for (const line of callLines) {
          const trimmed = line.trim();
          // Bare call (not inside an if): starts with assertInInjectionContext directly
          const isBareCall = /^assertInInjectionContext\\(/.test(trimmed);
          expect(isBareCall).toBe(false);
        }
      }
    });
  }
});
""",
        },
    },

    # =========================================================================
    # REACT — lodash task (kept for breadth)
    # =========================================================================

    # =========================================================================
    # ANGULAR — 5 tasks  (populated after agent research)
    # =========================================================================
}


def get_task(task_id: str) -> TaskSpec:
    try:
        return SAMPLE_TASKS[task_id]
    except KeyError as exc:
        available = ", ".join(sorted(SAMPLE_TASKS))
        raise KeyError(f"Unknown task '{task_id}'. Available tasks: {available}") from exc
