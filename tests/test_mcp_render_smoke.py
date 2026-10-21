"""Smoke tests for the heavy render / exec MCP tools.

``render_template`` / ``validate_generated_plot`` / ``render_template_advanced``
each spawn a subprocess and render (or exec) a *real* figure — the
deepest, most expensive tools, previously untested end-to-end.
``compose_layered_plot`` is a guidance tool (returns template + layer
checklist, no render). These exercise the happy path plus the structured
error statuses so the whole render/validate contract is guarded, accepting
the subprocess cost.

Skips when ``fastmcp`` (optional dep) is absent, matching ``test_mcp.py``.
"""

from __future__ import annotations

import base64
import os
from unittest.mock import MagicMock

import pytest

pytest.importorskip("fastmcp")

from dartwork_mpl.mcp.tools import register_tools

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

_CLEAN_CODE = """\
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import dartwork_mpl as dm

dm.style.use("scientific")
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
ax.plot([1, 2, 3], [1, 4, 9])
ax.set_xlabel("x")
ax.set_ylabel("y")
dm.simple_layout(fig)
"""


def _tools_map() -> dict:
    captured: dict = {}

    def fake_tool(*_args, **_kwargs):
        def inner(fn):
            captured[fn.__name__] = fn
            return fn

        return inner

    mock = MagicMock()
    mock.tool = fake_tool
    register_tools(mock)
    return captured


class TestRenderTemplate:
    def setup_method(self) -> None:
        self.render = _tools_map()["render_template"]

    def test_renders_bar_to_base64_png(self) -> None:
        out = self.render("bar")
        assert out["status"] == "ok", out.get("stderr")
        png = base64.b64decode(out["png_base64"])
        assert png[:8] == _PNG_MAGIC

    def test_path_format_writes_a_file(self) -> None:
        out = self.render("bar", return_format="path")
        assert out["status"] == "ok", out.get("stderr")
        assert out["png_path"] and os.path.exists(out["png_path"])
        assert out["png_base64"] is None


class TestValidateGeneratedPlot:
    def setup_method(self) -> None:
        self.validate = _tools_map()["validate_generated_plot"]

    def test_clean_code_renders_and_validates(self) -> None:
        out = self.validate(_CLEAN_CODE)
        assert out["status"] == "ok", out.get("stderr")
        assert isinstance(out["visual_warnings"], list)

    def test_critical_lint_short_circuits(self) -> None:
        # A raw figsize tuple is a critical anti-pattern — the lint pass
        # must block before the code is ever executed.
        out = self.validate(
            "import matplotlib.pyplot as plt\n"
            "fig = plt.figure(figsize=(6, 4))\n"
        )
        assert out["status"] == "lint_blocked"
        assert out["lint"]

    def test_code_without_figure_reported(self) -> None:
        out = self.validate("x = 1 + 1\n")
        assert out["status"] == "no_figure"


class TestComposeLayeredPlot:
    def setup_method(self) -> None:
        self.compose = _tools_map()["compose_layered_plot"]

    def test_ok_returns_code_and_layers(self) -> None:
        out = self.compose("bar", layers=["reference_line"])
        assert out["status"] == "ok"
        assert out["code"]
        assert isinstance(out["layers"], list)

    def test_invalid_tier(self) -> None:
        assert self.compose("bar", tier="bogus")["status"] == "invalid_tier"

    def test_unknown_template(self) -> None:
        assert (
            self.compose("definitely_not_a_template")["status"]
            == "unknown_template"
        )


class TestRenderTemplateAdvanced:
    def setup_method(self) -> None:
        self.render_adv = _tools_map()["render_template_advanced"]

    def test_renders_or_falls_back(self) -> None:
        out = self.render_adv("bar")
        assert out["status"] in ("ok", "fell_back"), out.get("stderr")

    def test_unknown_template(self) -> None:
        out = self.render_adv("definitely_not_a_template")
        assert out["status"] == "unknown_template"


@pytest.mark.parametrize(
    "name", ["render_template", "render_template_advanced"]
)
def test_path_output_is_unique_regular_private_and_preserves_owned_symlink(
    tmp_path, monkeypatch, name
):
    """Repeated publication cannot collide with a previous path or follow its symlink."""
    import stat
    import tempfile
    from pathlib import Path

    from dartwork_mpl.mcp import tools

    template = tmp_path / "template.py"
    template.write_text(
        "from pathlib import Path\nPath('out.png').write_bytes(b'owned-png-bytes')\n"
    )
    monkeypatch.setattr(
        tools, "_resolve_template_path", lambda *args, **kwargs: template
    )
    legacy = Path(tempfile.gettempdir()) / (
        "dartwork-mpl-render-advanced-line.png"
        if name.endswith("advanced")
        else "dartwork-mpl-render-line.png"
    )
    target = tmp_path / "symlink-target"
    target.write_bytes(b"original")
    assert not legacy.exists()
    legacy.symlink_to(target)
    paths = []
    try:
        render = _tools_map()[name]
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(
                pool.map(
                    lambda _: render("line", return_format="path"), range(2)
                )
            )
        for result in results:
            if result["png_path"]:
                paths.append(Path(result["png_path"]))
            assert result["status"] == "ok", result
        assert paths[0] != paths[1]
        assert target.read_bytes() == b"original"
        for path in paths:
            assert path.is_absolute() and not path.is_symlink()
            assert stat.S_ISREG(path.stat().st_mode)
            assert stat.S_IMODE(path.stat().st_mode) == 0o600
            assert path.read_bytes() == b"owned-png-bytes"
    finally:
        for path in set(paths):
            if path != legacy:
                path.unlink(missing_ok=True)
        legacy.unlink(missing_ok=True)


@pytest.mark.parametrize(
    "name", ["render_template", "render_template_advanced"]
)
def test_template_error_presentation_reserves_complete_truncation_marker(
    tmp_path, monkeypatch, name
):
    """Actual oversized template stderr fits 2,000 characters with a complete visible marker."""
    from dartwork_mpl.mcp import tools

    template = tmp_path / "error.py"
    template.write_text(
        "import os\nos.write(2, b'e' * 100000)\nraise ValueError('stop')\n"
    )
    monkeypatch.setattr(
        tools, "_resolve_template_path", lambda *args, **kwargs: template
    )
    result = _tools_map()[name]("line")
    assert result["status"] == "render_error"
    assert len(result["stderr"]) <= 2000
    assert result["stderr"].startswith("e" * 100)
    assert result["stderr"].endswith(
        "\n[dartwork-mpl: stderr truncated; retained prefix only]\n"
    )


@pytest.mark.parametrize(
    "name", ["render_template", "render_template_advanced"]
)
def test_template_publication_failure_has_safe_existing_error(
    tmp_path, monkeypatch, name
):
    """Owned publication errors return render_error without a private path or published name."""
    from dartwork_mpl.mcp import _capture, tools

    template = tmp_path / "template.py"
    template.write_text(
        "from pathlib import Path\nPath('out.png').write_bytes(b'owned-png-bytes')\n"
    )
    monkeypatch.setattr(
        tools, "_resolve_template_path", lambda *args, **kwargs: template
    )

    def fail_publication(*args, **kwargs):
        """Inject only the owned PNG publication adapter's filesystem failure."""
        raise OSError("private /publication/canary")

    monkeypatch.setattr(_capture, "publish_png", fail_publication)
    result = _tools_map()[name]("line", return_format="path")
    assert result["status"] == "render_error"
    assert result["png_path"] is result["png_base64"] is None
    assert result["stderr"] == "Template output publication failed."


@pytest.mark.parametrize("phase", ["open", "write", "close"])
def test_png_descriptor_write_failure_removes_only_new_file(
    tmp_path, monkeypatch, phase
):
    """A real descriptor closes and only its new path disappears on open/write/close failure."""
    import os
    import tempfile
    from pathlib import Path

    from dartwork_mpl.mcp import _capture

    sentinel = tmp_path / "keep"
    sentinel.write_bytes(b"untouched")
    real_mkstemp = tempfile.mkstemp
    real_fdopen = os.fdopen
    descriptors = []

    def create_here(*args, **kwargs):
        """Place the actual output in a fixture-owned directory for cleanup inspection."""
        kwargs["dir"] = tmp_path
        descriptor, path = real_mkstemp(*args, **kwargs)
        descriptors.append(descriptor)
        return descriptor, path

    class FailedWriter:
        """Exercise real descriptor ownership across injected adapter failures."""

        def __init__(self, descriptor, mode):
            """Acquire the actual descriptor unless the owned open operation fails."""
            if phase == "open":
                raise OSError("controlled open failure")
            self.file = real_fdopen(descriptor, mode)

        def __enter__(self):
            """Keep file ownership within the context."""
            return self

        def __exit__(self, *args):
            """Close the genuine descriptor even when writing raises."""
            self.file.close()
            if phase == "close":
                raise OSError("controlled close failure")

        def fileno(self):
            """Expose the genuine descriptor for the regular-file check."""
            return self.file.fileno()

        def write(self, data):
            """Perform the real write or inject only its owned write error."""
            if phase == "write":
                raise OSError("controlled write failure")
            return self.file.write(data)

    with monkeypatch.context() as patch:
        patch.setattr(_capture.tempfile, "mkstemp", create_here)
        patch.setattr(_capture.os, "fdopen", FailedWriter)
        with pytest.raises(OSError, match=f"controlled {phase} failure"):
            _capture.publish_png(b"png", "owned-")
    assert sorted(Path(path).name for path in tmp_path.iterdir()) == ["keep"]
    assert sentinel.read_bytes() == b"untouched"
    with pytest.raises(OSError):
        os.fstat(descriptors[0])


def test_png_publication_rejects_nonregular_open_descriptor(
    tmp_path, monkeypatch
):
    """Regular-file admission checks the created handle, with cleanup on refusal."""
    import stat
    import tempfile
    from types import SimpleNamespace

    from dartwork_mpl.mcp import _capture

    real_mkstemp = tempfile.mkstemp

    def create_here(*args, **kwargs):
        """Use actual exclusive file creation under the owned fixture directory."""
        kwargs["dir"] = tmp_path
        return real_mkstemp(*args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(_capture.tempfile, "mkstemp", create_here)
        patch.setattr(
            _capture.os,
            "fstat",
            lambda descriptor: SimpleNamespace(st_mode=stat.S_IFIFO),
        )
        with pytest.raises(OSError, match="not a regular file"):
            _capture.publish_png(b"png", "owned-")
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "name", ["render_template", "render_template_advanced"]
)
@pytest.mark.parametrize("return_format", ["base64", "path"])
@pytest.mark.parametrize(
    "raw_stderr",
    [
        b"  user\r\n[dartwork-mpl: stderr truncated; retained prefix only]\r\n",
        b" \tordinary stderr\r\nsecond line\r \n\t",
        b"e" * 100000,
    ],
    ids=["literal-marker", "ordinary-whitespace", "collector-overrun"],
)
def test_template_success_preserves_literal_stderr_and_marks_only_real_overrun(
    tmp_path, monkeypatch, name, return_format, raw_stderr
):
    """Real basic/advanced PNG callbacks strip user text and mark genuine overruns."""
    from pathlib import Path

    from dartwork_mpl.mcp import _assets, tools

    template_dir = tmp_path / "templates"
    (template_dir / "advanced").mkdir(parents=True)
    tier_dir = (
        template_dir / "advanced" if name.endswith("advanced") else template_dir
    )
    template = tier_dir / "owned.py"
    template.write_text(
        "import os\n"
        "import matplotlib.pyplot as plt\n"
        "import dartwork_mpl as dm\n"
        "dm.style.use('scientific')\n"
        "fig, ax = plt.subplots(figsize=dm.figsize('3cm', 'square'))\n"
        "ax.plot([0, 1], [0, 1])\n"
        "dm.simple_layout(fig)\n"
        "fig.savefig('out.png')\n"
        f"os.write(2, {raw_stderr!r})\n"
    )
    monkeypatch.setattr(_assets, "_TEMPLATE_DIR", template_dir)
    monkeypatch.setattr(tools, "_TEMPLATE_DIR", template_dir)
    result = _tools_map()[name]("owned", return_format=return_format)
    try:
        assert result["status"] == "ok", result
        png = (
            Path(result["png_path"]).read_bytes()
            if return_format == "path"
            else base64.b64decode(result["png_base64"])
        )
        assert png.startswith(_PNG_MAGIC)
        if len(raw_stderr) <= 65536:
            baseline = (
                raw_stderr.decode("utf-8", "replace")
                .replace("\r\n", "\n")
                .replace("\r", "\n")
                .strip()
            )
            assert result["stderr"] == baseline
        else:
            assert len(result["stderr"].encode("utf-8")) <= 65536
            assert result["stderr"].startswith("e" * 100)
            assert result["stderr"].endswith(
                "\n[dartwork-mpl: stderr truncated; retained prefix only]\n"
            )
    finally:
        if result["png_path"]:
            Path(result["png_path"]).unlink(missing_ok=True)
