"""Real child execution pins selected-Figure export and inherited validator effects."""

import io
import json
import os
import random
import re
from pathlib import Path
from tempfile import TemporaryDirectory

import matplotlib.image as mpimg
import pytest

pytest.importorskip("fastmcp")
from dartwork_mpl.mcp import _capture
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


def test_export_refuses_caller_bounded_logs_through_declared_result(tmp_path):
    """A real child overrun returns a declared refusal without private wire flags."""
    from dartwork_mpl.mcp import execution

    assert "LogLimitRejected" in execution.__all__
    result = export_plot(
        "import os\nos.write(1, b'x' * 2048)\n",
        "fig",
        20,
        None,
        output_stem=tmp_path / "plot",
        log_limit_bytes=1024,
    )
    assert isinstance(result, execution.LogLimitRejected), result
    assert result.report["status"] == "exec_error"
    assert result.report["validation_complete"] is False
    assert "_artifact_logs_too_large" not in result.report
    assert not list(tmp_path.iterdir())


def test_export_cannot_disable_log_limit_before_child_launch(tmp_path):
    """The new keyword cannot switch an export to legacy capture by passing None."""
    marker = tmp_path / "executed"
    with pytest.raises(ValueError, match="positive integer"):
        export_plot(
            f"from pathlib import Path\nPath({str(marker)!r}).touch()\n",
            "fig",
            20,
            None,
            output_stem=tmp_path / "plot",
            log_limit_bytes=None,
        )
    assert not marker.exists()


@pytest.fixture
def input_workspace(tmp_path):
    """Remove every fixture input and output even when a mapping assertion fails."""
    with TemporaryDirectory(prefix="mapping-", dir=tmp_path) as directory:
        yield Path(directory)


def test_input_mapping_reads_distinct_csvs_and_exports_native_values(
    input_workspace,
):
    """Actual staged CSV bytes supply independent native artists through a read-only map."""
    first = input_workspace / "first.csv"
    second = input_workspace / "second.csv"
    first.write_text("x,y,include\n2,20,1\n1,,1\n3,30,0\n4,40,1\n")
    second.write_text("x,y\n5,50\n6,60\n")
    paths = {"measurements": str(first), "comparison": str(second)}
    code = (
        FIGURE
        + """import csv
from collections.abc import Mapping
assert isinstance(dartwork_inputs, Mapping)
assert set(dartwork_inputs) == {'measurements', 'comparison'}
try:
    dartwork_inputs['measurements'] = dartwork_inputs['comparison']
except TypeError:
    pass
else:
    raise AssertionError('mapping must be read-only')
with open(dartwork_inputs['measurements'], newline='') as stream:
    rows = [row for row in csv.DictReader(stream) if row['y'] and row['include'] == '1']
ax.lines[0].set_data([int(row['x']) for row in rows], [int(row['y']) for row in rows])
assert list(ax.lines[0].get_xdata()) == [2, 4]
assert list(ax.lines[0].get_ydata()) == [20, 40]
with open(dartwork_inputs['comparison'], newline='') as stream:
    rows = list(csv.DictReader(stream))
line, = ax.plot([int(row['x']) for row in rows], [int(row['y']) for row in rows], linewidth=dm.lw(0))
assert list(line.get_xdata()) == [5, 6]
assert list(line.get_ydata()) == [50, 60]
print('checked [2, 4] [20, 40]; [5, 6] [50, 60]')
"""
    )
    result = export_plot(
        code,
        "fig",
        20,
        "line",
        output_stem=input_workspace / "plot",
        input_paths=paths,
    )
    assert isinstance(result, ExportedPlot), result
    assert (
        result.report["stdout"] == "checked [2, 4] [20, 40]; [5, 6] [50, 60]\n"
    )
    assert result.report["semantic_warnings"] == []
    assert (
        (input_workspace / "plot.png")
        .read_bytes()
        .startswith(b"\x89PNG\r\n\x1a\n")
    )
    assert (input_workspace / "plot.pdf").read_bytes().startswith(b"%PDF-")
    assert paths == {"measurements": str(first), "comparison": str(second)}


@pytest.mark.parametrize("input_paths", [None, {}])
def test_no_inputs_leave_the_reserved_global_absent(
    input_workspace, input_paths
):
    """Neither omitted inputs nor an empty map introduces a snippet global."""
    code = FIGURE + "assert 'dartwork_inputs' not in globals()\n"
    result = export_plot(
        code,
        "fig",
        20,
        None,
        output_stem=input_workspace / "plot",
        input_paths=input_paths,
    )
    assert isinstance(result, ExportedPlot), result


def test_private_stdin_keeps_paths_out_of_argv_environment_and_source(
    input_workspace, monkeypatch
):
    """The real subprocess receives paths only in its private frame and exact source after it."""
    source_file = input_workspace / 'private-한글-"-\\-\n.csv'
    source_file.write_text("x,y\n7,70\n")
    paths = {"measurements": str(source_file)}
    submitted = (
        "# exact source: 한글, CRLF and trailing whitespace  \r\n"
        + FIGURE
        + """import os, sys
assert open(dartwork_inputs['measurements']).read() == 'x,y\\n7,70\\n'
for path in dartwork_inputs.values():
    assert all(path not in arg for arg in sys.orig_argv)
    assert all(path not in value for value in os.environ.values())
print('frame checked')
"""
    )
    before = submitted.encode("utf-8")
    observed = []
    real_run = _capture.run_child

    def observe_run(args, **kwargs):
        """Observe the subprocess adapter's wire bytes while still executing its real child."""
        observed.append((args, kwargs["stdin"], kwargs.get("env")))
        return real_run(args, **kwargs)

    monkeypatch.setattr(_capture, "run_child", observe_run)
    result = export_plot(
        submitted,
        "fig",
        20,
        None,
        output_stem=input_workspace / "plot",
        input_paths=paths,
    )
    assert isinstance(result, ExportedPlot), result
    assert result.report["stdout"] == "frame checked\n"
    assert submitted.encode("utf-8") == before
    assert len(observed) == 1
    args, wire, environment = observed[0]
    header, source = wire.split("\n", 1)
    assert json.loads(header) == paths
    assert source.encode("utf-8") == before
    assert all(str(source_file) not in arg for arg in args)
    assert environment is None
    assert not Path(args[3]).parent.exists()


def test_seeded_private_mapping_roundtrip_preserves_path_strings(
    input_workspace,
):
    """Seeded Unicode and code-like filenames survive framing as data, without evaluation."""
    rng = random.Random(2381)
    alphabet = "abc123한글é\"'\\\n\r()[]{}; "
    paths = {}
    for index in range(8):
        name = f"input_{index}"
        filename = "".join(rng.choice(alphabet) for _ in range(24))
        fixture = input_workspace / filename
        fixture.write_text(str(index))
        paths[name] = str(fixture)
    code = (
        FIGURE
        + """import json
for index in range(8):
    assert open(dartwork_inputs[f'input_{index}']).read() == str(index)
print(json.dumps(dict(dartwork_inputs), ensure_ascii=True))
"""
    )
    result = export_plot(
        code,
        "fig",
        20,
        None,
        output_stem=input_workspace / "plot",
        input_paths=paths,
    )
    assert isinstance(result, ExportedPlot), result
    assert json.loads(result.report["stdout"]) == paths, (2381, paths)


@pytest.mark.parametrize(
    "invalid", [[], {1: "path"}, {"data": 1}, {"data": Path("path")}]
)
def test_invalid_internal_mapping_types_fail_before_launch(
    input_workspace, invalid
):
    """Caller programming errors reject malformed map types without executing source."""
    marker = input_workspace / "executed"
    code = f"from pathlib import Path\nPath({str(marker)!r}).touch()"
    with pytest.raises(
        TypeError, match="input_paths must map string names to string paths"
    ):
        export_plot(
            code,
            "fig",
            20,
            None,
            output_stem=input_workspace / "plot",
            input_paths=invalid,
        )
    assert not list(input_workspace.iterdir())


@pytest.mark.parametrize(
    "header",
    [
        "not JSON",
        "[]",
        '{"data": 1}',
        "__import__('builtins').print('EVALUATED') or {}",
    ],
)
def test_malformed_private_frame_rejects_without_executing_source(
    input_workspace, monkeypatch, header
):
    """Damaged private transport returns the existing exec_error and removes its checkpoint."""
    marker = input_workspace / "executed"
    code = f"from pathlib import Path\nPath({str(marker)!r}).touch()"
    real_run = _capture.run_child
    channels = []

    def damage_frame(args, **kwargs):
        """Inject a damaged wire header at this subprocess adapter while running its real child."""
        channels.append(Path(args[3]).parent)
        _, source = kwargs["stdin"].split("\n", 1)
        kwargs["stdin"] = header + "\n" + source
        return real_run(args, **kwargs)

    monkeypatch.setattr(_capture, "run_child", damage_frame)
    result = export_plot(
        code,
        "fig",
        20,
        None,
        output_stem=input_workspace / "plot",
        input_paths={"data": "unused"},
    )
    assert isinstance(result, ExecutionRejected), result
    assert result.report["status"] == "exec_error"
    assert result.report["exc_type"] in {"JSONDecodeError", "TypeError"}
    assert len(channels) == 1
    assert not channels[0].exists()
    assert not list(input_workspace.iterdir())


def test_mapping_preserves_controlled_legacy_report_and_logs(
    input_workspace, monkeypatch
):
    """Opt-in injection preserves stable report bytes, cwd/environment and original logs."""
    monkeypatch.chdir(input_workspace)
    monkeypatch.setenv("DARTWORK_MAPPING_TEST", "inherited")
    code = (
        FIGURE
        + """import os, sys
assert os.environ['DARTWORK_MAPPING_TEST'] == 'inherited'
with open('relative.txt', 'w') as stream:
    stream.write('cwd inherited')
print('  stdout spaces  ')
print('  stderr spaces  ', file=sys.stderr)
"""
    )
    legacy = export_plot(
        code, "fig", 20, None, output_stem=input_workspace / "legacy"
    )
    mapped = export_plot(
        code,
        "fig",
        20,
        None,
        output_stem=input_workspace / "mapped",
        input_paths={"unused": str(input_workspace / "relative.txt")},
    )
    assert isinstance(legacy, ExportedPlot), legacy
    assert isinstance(mapped, ExportedPlot), mapped
    assert (
        json.dumps(mapped.report, sort_keys=True).encode()
        == json.dumps(legacy.report, sort_keys=True).encode()
    )
    assert mapped.report["stdout"] == "  stdout spaces  \n"
    assert mapped.report["stderr"] == "  stderr spaces  \n"
    assert (input_workspace / "relative.txt").read_text() == "cwd inherited"
    assert (input_workspace / "legacy.png").read_bytes() == (
        input_workspace / "mapped.png"
    ).read_bytes()
    validated = validate_plot(code)
    assert validated["status"] == "ok"
    assert validated["stdout"] == "  stdout spaces  \n"
    assert validated["stderr"] == "stderr spaces"


@pytest.mark.parametrize(
    ("ending", "status", "timeout"),
    [
        ("raise ValueError('mapping failure')", "exec_error", 20),
        ("import time; time.sleep(60)", "timeout", 4),
        ("pass", "no_figure", 20),
    ],
)
def test_mapping_failure_reaps_child_and_removes_private_channel(
    input_workspace, ending, status, timeout
):
    """After mapped execution fails or times out, its child and checkpoint directory are gone."""
    fixture = input_workspace / "fixture.csv"
    fixture.write_text("x,y\n1,10\n")
    code = (
        """import json, os, sys
assert open(dartwork_inputs['data']).read() == 'x,y\\n1,10\\n'
print(json.dumps({'pid': os.getpid(), 'channel': sys.argv[1]}), flush=True)
"""
        + ending
    )
    result = export_plot(
        code,
        "fig",
        timeout,
        None,
        output_stem=input_workspace / "plot",
        input_paths={"data": str(fixture)},
    )
    assert isinstance(result, ExecutionRejected), result
    assert result.report["status"] == status
    evidence = json.loads(result.report["stdout"])
    assert not Path(evidence["channel"]).parent.exists()
    with pytest.raises(ProcessLookupError):
        os.kill(evidence["pid"], 0)
    assert sorted(path.name for path in input_workspace.iterdir()) == [
        "fixture.csv"
    ]
    if status == "exec_error":
        assert result.report["exc_type"] == "ValueError"
        assert result.report["exc_msg"] == "mapping failure"
