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
