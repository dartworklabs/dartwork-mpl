"""Real child execution pins selected-Figure export and inherited validator effects."""

import io
import re
from pathlib import Path

import matplotlib.image as mpimg
import pytest

pytest.importorskip("fastmcp")
from dartwork_mpl.mcp.execution import (
    ExecutionRejected,
    ExportedPlot,
    ExportRejected,
    export_plot,
    validate_plot,
)

FIGURE = """import matplotlib.pyplot as plt
import dartwork_mpl as dm
dm.style.use('scientific')
fig, ax = plt.subplots(figsize=dm.figsize('6cm', 'square'))
ax.plot([1,2], [2,3], linewidth=dm.lw(0))
dm.simple_layout(fig)
"""
FAULT = """from dartwork_mpl.validate._checks import register_check
@register_check('ORIGINAL_FAILURE', order=9999)
def fail(fig, renderer):
    raise ValueError('check failed')
"""


def test_single_execution_exports_the_validated_selected_figure(tmp_path):
    """One nondeterministic run saves the selected Figure without extra styling."""
    marker = tmp_path / "executions"
    code = (
        FIGURE
        + f"""from pathlib import Path
import random, sys
with Path({str(marker)!r}).open('a') as marker:
    marker.write('run\\n')
value = random.random()
ax.lines[0].set_ydata([value, value + 1])
print(value)
print('  stderr spaces  ', file=sys.stderr)
ax.set_facecolor('red')
other, other_ax = plt.subplots(figsize=dm.figsize('3cm', 'square'))
other_ax.set_facecolor('blue')
dm.save_formats(fig, {str(tmp_path / "reference")!r}, formats=('png',), validate=False, adopt_orphan_tick_font=False)
"""
    )
    result = export_plot(code, "fig", 20, None, output_stem=tmp_path / "plot")
    assert isinstance(result, ExportedPlot), result
    assert marker.read_text() == "run\n"
    assert float(result.report["stdout"].strip()) >= 0
    assert result.report["stderr"] == "  stderr spaces  \n"
    image = mpimg.imread(io.BytesIO((tmp_path / "plot.png").read_bytes()))
    assert (
        image[image.shape[0] // 3, image.shape[1] // 2, 0] > 0.9
        and image[image.shape[0] // 3, image.shape[1] // 2, 2] < 0.1
    )
    assert (tmp_path / "plot.pdf").read_bytes().startswith(b"%PDF-")
    assert (tmp_path / "plot.png").read_bytes() == (
        tmp_path / "reference.png"
    ).read_bytes()
    bounds = re.search(
        rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)",
        (tmp_path / "plot.pdf").read_bytes(),
    )
    assert bounds is not None
    assert float(bounds[1]) == pytest.approx(6 / 2.54 * 72)
    assert float(bounds[2]) == pytest.approx(6 / 2.54 * 72)


def test_validator_contract_survives_runner_extraction(tmp_path, monkeypatch):
    """Cwd, snippet saves, fallback and hint-dependent semantics remain native."""
    monkeypatch.chdir(tmp_path)
    result = validate_plot(
        FIGURE + "dm.save_formats(fig, 'native', formats=('png',))\ndel fig\n",
        "missing",
        chart_type_hint="line",
    )
    assert result["status"] == "ok"
    assert result["semantic_warnings"] == []
    assert Path("native.png").exists()
    assert "semantic_warnings" not in validate_plot(FIGURE)
    invalid = validate_plot("fig = 4")
    assert invalid["status"] == "exec_error"
    assert invalid["exc_type"] == "AttributeError"
    assert invalid["exc_msg"] == "'int' object has no attribute 'canvas'"


def test_export_failure_keeps_incomplete_check_ids(tmp_path):
    """Infrastructure export failure preserves acquired validation evidence safely."""
    code = (
        FIGURE
        + FAULT
        + "def fail_save(*args, **kwargs):\n    raise OSError('private /staging/path')\ndm.save_formats = fail_save\n"
    )
    result = export_plot(code, "fig", 20, None, output_stem=tmp_path / "plot")
    assert isinstance(result, ExportRejected), result
    assert result.report["failed_checks"] == ["ORIGINAL_FAILURE"]
    assert result.report["validation_complete"] is False
    assert "/staging/path" not in str(result)


@pytest.mark.parametrize(
    ("code", "status", "timeout"),
    [
        ("plt.tight_layout()", "lint_blocked", 20),
        ("bad syntax !", "exec_error", 20),
        ('raise ValueError("boom")', "exec_error", 20),
        ("fig = 4", "exec_error", 20),
        ('print("empty")', "no_figure", 20),
        ("import time; time.sleep(60)", "timeout", 0.2),
    ],
)
def test_failed_execution_never_exports(tmp_path, code, status, timeout):
    """Every early outcome rejects delivery and leaves no PNG/PDF."""
    result = export_plot(
        code, "fig", timeout, None, output_stem=tmp_path / "plot"
    )
    assert isinstance(result, ExecutionRejected)
    assert result.report["status"] == status
    assert not list(tmp_path.iterdir())


def test_export_preserves_configured_orphan_tick_fonts(tmp_path):
    """Opted-in global adoption cannot change the Figure after validation."""
    reference = tmp_path / "reference"
    code = (
        FIGURE
        + f"""ax.xaxis.label.set_fontsize(dm.fs(5))
for tick in ax.get_xticklabels():
    tick.set_fontsize(dm.fs(-2))
dm.config.adopt_orphan_tick_font = True
dm.save_formats(fig, {str(reference)!r}, formats=('png',), validate=False, adopt_orphan_tick_font=False)
"""
    )
    result = export_plot(code, "fig", 20, None, output_stem=tmp_path / "plot")
    assert isinstance(result, ExportedPlot)
    assert (tmp_path / "plot.png").read_bytes() == (
        tmp_path / "reference.png"
    ).read_bytes()


@pytest.mark.parametrize(
    "stderr", ["", "  user SyntaxWarning: keep this diagnostic  \n"]
)
def test_export_stderr_contains_only_original_user_output(tmp_path, stderr):
    """Runner compilation stays silent while exact user diagnostics survive."""
    code = FIGURE + f"import sys\nsys.stderr.write({stderr!r})\n"
    result = export_plot(code, "fig", 20, None, output_stem=tmp_path / "plot")
    assert isinstance(result, ExportedPlot), result
    assert result.report["stderr"] == stderr
    assert (tmp_path / "plot.png").exists()
