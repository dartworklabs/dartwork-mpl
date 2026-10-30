"""Real MCP and subprocess observations pin plot-validation result contracts."""

import asyncio
import json
from pathlib import Path
from typing import Any

import matplotlib.image as mpimg
import pytest

fastmcp = pytest.importorskip("fastmcp")

from dartwork_mpl.mcp import resources, tools  # noqa: E402

_FIGURE = """\
import matplotlib.pyplot as plt
import dartwork_mpl as dm
dm.style.use('scientific')
fig, ax = plt.subplots(figsize=dm.figsize('13cm', 'standard'))
dm.simple_layout(fig)
"""
_FAULT = """\
from dartwork_mpl.validate._checks import register_check
@register_check('FAULT_ORIGINAL', order=9999)
def fail(fig, renderer):
    raise ValueError('controlled bbox failure')
"""


def _server() -> Any:
    """Register genuine FastMCP tools and resources for protocol-level checks."""
    server = fastmcp.FastMCP("validation-contract-test")
    resources.register_resources(server)
    tools.register_tools(server)
    return server


def _validate(code: str, **kwargs: Any) -> dict[str, Any]:
    """Invoke the genuine registered callback while running its child for real."""
    tool = asyncio.run(_server().get_tool("validate_generated_plot"))
    return tool.fn(code, **kwargs)


def test_validate_print_and_save_output(tmp_path: Path, monkeypatch) -> None:
    """Discovery, template read, logs and relative PNG saves work over MCP."""
    monkeypatch.chdir(tmp_path)

    async def workflow() -> dict[str, Any]:
        """Traverse MCP discovery/resource/tool boundaries with a real client."""
        async with fastmcp.Client(_server()) as client:
            names = {tool.name for tool in await client.list_tools()}
            assert "validate_generated_plot" in names
            listing = await client.read_resource(
                "dartwork-mpl://templates/list"
            )
            assert "line" in "".join(item.text for item in listing)
            template = await client.read_resource(
                "dartwork-mpl://templates/line"
            )
            assert "dm.figsize" in "".join(item.text for item in template)
            result = await client.call_tool(
                "validate_generated_plot",
                {
                    "code": _FIGURE
                    + """\
import os
import sys
ax.plot([1, 2, 3], [4, 5, 6], linewidth=dm.lw(0))
dm.simple_layout(fig)
print('first line\\n{"status": "pretend"}', flush=True)
os.write(1, b'raw stdout\\n')
os.write(1, b'\\xff\\n')
os.write(2, b'\\xff\\n')
print('diagnostic stderr', file=sys.stderr)
dm.save_formats(fig, 'saved_plot', formats=('png',))
"""
                },
            )
            return json.loads(result.content[0].text)

    result = asyncio.run(workflow())
    assert result["status"] == "ok", result
    assert result["validation_complete"] is True
    assert result["failed_checks"] == []
    assert 'first line\n{"status": "pretend"}\nraw stdout\n' in result["stdout"]
    assert "diagnostic stderr" in result["stderr"]
    assert "\ufffd\n" in result["stdout"]
    assert "\ufffd" in result["stderr"]
    assert "semantic_warnings" not in result
    image = mpimg.imread(tmp_path / "saved_plot.png")
    assert image.shape[0] > 0 and image.shape[1] > 0


@pytest.mark.parametrize("hint", [None, "line"])
def test_mcp_failed_check_is_incomplete(hint) -> None:
    """A registered failed check retains real warnings and optional semantics."""
    result = _validate(_FIGURE + _FAULT, chart_type_hint=hint)
    assert result["status"] == "validation_incomplete", result
    assert result["validation_complete"] is False
    assert result["failed_checks"] == ["FAULT_ORIGINAL"]
    ids = [item["check_id"] for item in result["visual_warnings"]]
    assert "EMPTY_AXES" in ids
    assert ids[-1] == "CHECK_FAILED"
    assert result["visual_warnings"][-1]["detail"] == {
        "check_id": "FAULT_ORIGINAL"
    }
    assert ("semantic_warnings" in result) == (hint is not None)
    if hint:
        assert result["semantic_warnings"][0]["check_id"] == "line_no_lines"
    assert isinstance(result["stdout"], str)


@pytest.mark.parametrize("hint", [None, "line"])
@pytest.mark.parametrize(
    ("code", "status", "timeout"),
    [
        ("plt.tight_layout()\n", "lint_blocked", 20),
        (
            "print('before error', flush=True)\nraise ValueError('boom')\n",
            "exec_error",
            20,
        ),
        ("print('no figure', flush=True)\n", "no_figure", 20),
        (
            "import time\nimport sys\nprint('before timeout', flush=True)\nprint('timeout stderr', file=sys.stderr, flush=True)\ntime.sleep(60)\n",
            "timeout",
            5,
        ),
    ],
)
def test_validation_not_complete_on_early_exit(code, status, timeout, hint):
    """Every early status has string logs and a consistent incomplete envelope."""
    result = _validate(code, timeout_seconds=timeout, chart_type_hint=hint)
    assert result["status"] == status, result
    assert result["validation_complete"] is False
    assert result["failed_checks"] == []
    assert isinstance(result["stdout"], str)
    assert isinstance(result["stderr"], str)
    assert ("semantic_warnings" in result) == (hint is not None)
    if status == "exec_error":
        assert "before error" in result["stdout"]
        assert result["exc_type"] == "ValueError"
        assert result["exc_msg"] == "boom"
    elif status == "timeout":
        assert "before timeout" in result["stdout"]
        assert "timeout stderr" in result["stderr"]
    elif status == "no_figure":
        assert "no figure" in result["stdout"]
    else:
        assert result["stdout"] == ""


def test_unexpected_validation_exception_is_error():
    """A validation defect is a visible execution error with preserved logs."""
    result = _validate(
        _FIGURE
        + _FAULT.replace("ValueError", "KeyError")
        + "print('before validation', flush=True)\n",
        chart_type_hint="line",
    )
    assert result["status"] == "exec_error", result
    assert result["exc_type"] == "KeyError"
    assert "controlled bbox failure" in result["exc_msg"]
    assert "before validation" in result["stdout"]
    assert result["validation_complete"] is False
    assert result["failed_checks"] == []
    assert result["semantic_warnings"] == []


def test_failed_checks_survive_later_semantic_error():
    """A later semantic defect cannot erase failures already returned natively."""
    code = (
        _FIGURE
        + "ax.bar([1], [2])\nax.text(1, 1, 'label')\n"
        + _FAULT.replace(
            "raise ValueError",
            "fig.axes[0].texts[0].get_text = lambda: {}['semantic defect']\n    raise ValueError",
        )
    )
    result = _validate(code, chart_type_hint="bar")
    assert result["status"] == "exec_error", result
    assert result["validation_complete"] is False
    assert result["failed_checks"] == ["FAULT_ORIGINAL"]
    assert result["exc_type"] == "KeyError"
    assert result["visual_warnings"][-1]["check_id"] == "CHECK_FAILED"


def test_pyplot_fallback_remains_supported():
    """The last tracked figure is validated when the named variable is absent."""
    result = _validate(
        _FIGURE + "del fig\n", figure_var="missing", chart_type_hint="line"
    )
    assert result["status"] == "ok", result
    assert result["validation_complete"] is True
    assert result["failed_checks"] == []
    assert result["semantic_warnings"][0]["check_id"] == "line_no_lines"


@pytest.mark.parametrize("fails", [False, True])
def test_process_control_exit_during_semantics_is_not_success(fails):
    """A zero exit before completion cannot turn a partial checkpoint into ok."""
    outcome = "raise ValueError('bbox fault')" if fails else "return []"
    code = (
        _FIGURE
        + "ax.bar([1], [2])\nax.text(1, 1, 'label')\n"
        + f"""\
from dartwork_mpl.validate._checks import register_check
@register_check('FAULT_ORIGINAL', order=9999)
def interrupt_semantics(fig, renderer):
    def leave():
        raise SystemExit(0)
    fig.axes[0].texts[0].get_text = leave
    {outcome}
"""
    )
    result = _validate(code, chart_type_hint="bar")
    assert result["status"] == "exec_error", result
    assert result["validation_complete"] is False
    assert result["failed_checks"] == (["FAULT_ORIGINAL"] if fails else [])
    if fails:
        assert result["visual_warnings"][-1]["check_id"] == "CHECK_FAILED"


@pytest.mark.parametrize(
    ("ending", "status", "timeout"),
    [
        ("", "ok", 20),
        ("raise ValueError('stop')\n", "exec_error", 20),
        ("import time\ntime.sleep(60)\n", "timeout", 5),
    ],
)
def test_private_channel_is_absolute_and_cleaned(ending, status, timeout):
    """The private channel leaves no result artifact after any runner outcome."""
    result = _validate(
        _FIGURE + "import sys\nprint(sys.argv[1], flush=True)\n" + ending,
        timeout_seconds=timeout,
    )
    assert result["status"] == status, result
    channel = Path(result["stdout"].splitlines()[0])
    assert channel.is_absolute()
    assert not channel.exists()
    assert not channel.parent.exists()


@pytest.mark.parametrize(
    ("code", "timeout"),
    [(None, 20), ("\ud800", 20), ("#" * (512 * 1024 + 1), 20)]
    + [
        ("pass", value)
        for value in (
            True,
            "2",
            0,
            -1,
            121,
            float("nan"),
            float("inf"),
            10**1000,
        )
    ],
    ids=[
        "nontext",
        "surrogate",
        "oversource",
        "bool",
        "string",
        "zero",
        "negative",
        "over120",
        "nan",
        "infinity",
        "huge_integer",
    ],
)
def test_source_timeout_refusal_precedes_execution(code, timeout):
    """Malformed admission returns the legacy safe envelope before lint or launch."""
    try:
        result = _validate(
            code, timeout_seconds=timeout, chart_type_hint="line"
        )
    except Exception as exc:
        result = exc
    assert isinstance(result, dict), type(result).__name__
    assert result["status"] == "exec_error", result
    assert result["validation_complete"] is False
    assert (
        result["lint"]
        == result["visual_warnings"]
        == result["failed_checks"]
        == []
    )
    assert result["stdout"] == ""
    assert result["semantic_warnings"] == []
    assert "code:" in result["stderr"] or "timeout_seconds:" in result["stderr"]


@pytest.mark.parametrize("fault", [MemoryError, RecursionError])
def test_handleable_ast_failure_never_executes_source(
    tmp_path, monkeypatch, fault
):
    """MCP preflight recognizes resource failures even when lint swallows them."""
    import ast

    marker = tmp_path / "executed"
    code = f"from pathlib import Path\nPath({str(marker)!r}).touch()"

    def fail_parse(*args, **kwargs):
        """Inject a handleable parser fault without exhausting host resources."""
        raise fault("private parser diagnostic must not leak")

    tool = asyncio.run(_server().get_tool("validate_generated_plot"))
    with monkeypatch.context() as patch:
        patch.setattr(ast, "parse", fail_parse)
        try:
            result = tool.fn(code)
        except Exception as exc:
            result = exc
    assert not marker.exists()
    assert isinstance(result, dict), type(result).__name__
    assert result["status"] == "exec_error"
    assert result["exc_type"] == fault.__name__
    assert "private parser diagnostic" not in result["stderr"]
    assert result["validation_complete"] is False


def test_legacy_log_overrun_retains_bounded_marked_prefixes():
    """Actual low-level writes cannot accumulate unbounded validator diagnostics."""
    result = _validate(
        "import os\nos.write(1, b'x' * 200000)\nos.write(2, b'y' * 200000)\n"
    )
    assert result["status"] == "no_figure", result
    for channel, prefix in (("stdout", "x"), ("stderr", "y")):
        assert len(result[channel].encode("utf-8")) <= 65536
        assert result[channel].startswith(prefix * 100)
        assert result[channel].endswith(
            f"\n[dartwork-mpl: {channel} truncated; retained prefix only]\n"
        )


@pytest.mark.parametrize("artifact", [False, True])
@pytest.mark.parametrize("times_out", [False, True])
def test_completed_and_timeout_logs_equal_finite_baseline_rules(
    tmp_path, artifact, times_out
):
    """Real children retain CR/LF/invalid-UTF8/space semantics for the selected outcome."""
    from dartwork_mpl.mcp.execution import ExecutionRejected, export_plot

    stdout = b"A\r\nB\rC\xe2\x82\xac\xff"
    stderr = b" \r\nE\rF\xe2\x82\xac\xff \r\n"
    code = (
        f"import os, time\nos.write(1, {stdout[:8]!r})\ntime.sleep(0.01)\nos.write(1, {stdout[8:]!r})\nos.write(2, {stderr!r})\n"
        + ("time.sleep(60)\n" if times_out else "")
    )
    timeout = 3 if times_out else 20
    if artifact:
        outcome = export_plot(
            code, "fig", timeout, None, output_stem=tmp_path / "plot"
        )
        assert isinstance(outcome, ExecutionRejected), outcome
        result = outcome.report
    else:
        result = _validate(code, timeout_seconds=timeout)
    expected_out = stdout.decode("utf-8", "replace")
    expected_err = stderr.decode("utf-8", "replace")
    if not times_out:
        expected_out = expected_out.replace("\r\n", "\n").replace("\r", "\n")
        expected_err = expected_err.replace("\r\n", "\n").replace("\r", "\n")
    if not artifact:
        expected_err = expected_err.strip()
        if times_out:
            expected_err += "\nSubprocess exceeded 3s timeout."
    assert result["status"] == ("timeout" if times_out else "no_figure"), result
    assert result["stdout"] == expected_out
    assert result["stderr"] == expected_err


def test_seeded_source_timeout_parser_is_total_and_boundary_controls_execute():
    """Independent render/execution admission agrees, including legal legacy options."""
    import random

    from dartwork_mpl.mcp import execution
    from dartwork_mpl.mcp.artifacts.policy import (
        InvalidRequest,
        RenderRequest,
        parse_render_request,
    )

    rng = random.Random(49822)
    assert hasattr(execution, "_source_timeout_error")
    values = [
        None,
        True,
        False,
        "3",
        {},
        [],
        0,
        -1,
        121,
        float("nan"),
        float("inf"),
        10**1000,
    ]
    for _ in range(100):
        code = rng.choice(["pass", "#한글", "\udfff", 5, None])
        timeout = rng.choice([*values, rng.uniform(0.01, 120)])
        result = parse_render_request(code, timeout_seconds=timeout)
        assert isinstance(result, (RenderRequest, InvalidRequest)), (
            49822,
            repr(code),
            timeout,
        )
        expected = (
            f"{result.field}: {result.message}"
            if isinstance(result, InvalidRequest)
            else None
        )
        assert execution._source_timeout_error(code, timeout) == expected
    assert isinstance(
        parse_render_request("#" * 524288, timeout_seconds=120), RenderRequest
    )
    assert isinstance(parse_render_request("#" * 524289), InvalidRequest)
    result = _validate(
        "#" * 524288,
        figure_var="not an identifier",
        chart_type_hint=False,
        timeout_seconds=120,
    )
    assert result["status"] == "no_figure", result
    assert result["semantic_warnings"] == []


def test_timeout_diagnostic_counts_marker_and_timeout_decoration_inside_byte_cap():
    """Actual invalid-byte expansion and timeout decoration share the selected channel budget."""
    result = _validate(
        "import os, time\nos.write(2, b'\\xff' * 30000)\ntime.sleep(60)\n",
        timeout_seconds=2,
    )
    assert result["status"] == "timeout", result
    assert len(result["stderr"].encode()) <= 65536
    assert "stderr truncated; retained prefix only]" in result["stderr"]
    assert result["stderr"].endswith("Subprocess exceeded 2s timeout.")


@pytest.mark.parametrize("fault", [MemoryError, RecursionError])
def test_escaping_lint_resource_failure_returns_safe_incomplete_error(
    monkeypatch, fault
):
    """Resource exceptions escaping lint are also refused after a successful preflight."""
    import dartwork_mpl.lint as lint_module

    def failed_lint(code):
        """Inject only the existing lint surface's handleable resource error."""
        raise fault("private lint details")

    monkeypatch.setattr(lint_module, "lint", failed_lint)
    result = _validate("pass")
    assert result["status"] == "exec_error"
    assert result["exc_type"] == fault.__name__
    assert result["validation_complete"] is False
    assert "private lint details" not in result["stderr"]


def test_legacy_nonidentifier_and_false_hint_keep_last_pyplot_fallback():
    """Source/timeout reuse does not import render's unrelated option restrictions."""
    result = _validate(
        _FIGURE, figure_var="not an identifier", chart_type_hint=False
    )
    assert result["status"] == "ok", result
    assert result["validation_complete"] is True
    assert result["semantic_warnings"] == []
