"""Pin deterministic docs assets and retire disconnected color generators.

The usage-guide, API-reference, and color-theory asset generators pin a
per-file ``svg.hashsalt`` and pass ``metadata={"Date": None}`` on every
save, so a re-render is byte-identical unless the plotted data actually
changed. A regressed generator (one that drops those controls) would
bake a wall-clock ``<dc:date>`` into the SVG and churn the tracked asset
on every run — defeating the "pictures are the proof" contract and
producing noisy, meaningless diffs.

This guards every tracked docs SVG under the three asset directories —
plus the ``preset_compare.html`` widget, which inlines SVGs directly —
against that regression cheaply, by reading the files (no rendering, so
no slow generator invocation). It is the sibling of
``test_docs_theory_figures.py``, which enforces the same invariant for
the ``theory_figures`` set specifically.
"""

import ast
import os
import re
import subprocess
from pathlib import Path
from typing import Any

import pytest

from tests.support.excluded_dirs import watch_access

_ROOT = Path(__file__).resolve().parents[2]
_DOCS = Path(__file__).resolve().parents[2] / "docs"

_PRESET_COMPARE = _DOCS / "usage_guide" / "images" / "preset_compare.html"
_STALE_COLOR_GENERATORS = (
    _DOCS / "_static" / "scripts" / "gen_palettes.py",
    _DOCS / "_static" / "scripts" / "dm_palettes_gen.json",
)
_GENERATE_COLOR_ASSETS = _DOCS / "color_system" / "generate_assets.py"
_PYPROJECT = _ROOT / "pyproject.toml"
_UV_LOCK = _ROOT / "uv.lock"


def _tracked_docs_svgs() -> list[Path]:
    """Return tracked docs SVGs without walking ignored render directories."""
    result = subprocess.run(
        ["git", "ls-files", "--", "docs"],
        cwd=_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    svgs = []
    for path in result.stdout.splitlines():
        full_path = _ROOT / path
        if path.endswith(".svg") and full_path.exists():
            # During this cleanup, deleted tracked SVGs remain in
            # ``git ls-files`` until the orchestrator stages them.
            svgs.append(full_path)
    return sorted(svgs)


def _live_python_sources() -> tuple[Path, ...]:
    """Return executable repository Python sources, excluding history."""
    # The exclude pathspec keeps git from listing internal design names at
    # all; the ``parts`` check below stays as a second line.
    result = subprocess.run(
        ["git", "ls-files", "--", "*.py", ":(exclude,glob)**/superpowers/**"],
        cwd=_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    live_roots = frozenset({"docs", "scripts", "src"})
    return tuple(
        sorted(
            _ROOT / relative
            for relative in result.stdout.splitlines()
            if relative
            and relative.split("/", maxsplit=1)[0] in live_roots
            and "superpowers" not in Path(relative).parts
            and (_ROOT / relative).exists()
        )
    )


def test_live_python_sources_never_list_internal_design_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ask git for live sources only: no ``superpowers`` name is listed."""
    for name in [name for name in os.environ if name.startswith("GIT_")]:
        monkeypatch.delenv(name)
    live = ["docs/page.py", "scripts/tool.py", "src/pkg/mod.py"]
    internal = [tmp_path / "docs/superpowers", tmp_path / "src/pkg/superpowers"]
    tracked = [*live, "evals/run.py", "docs/superpowers/decoy.py"]
    tracked.append("src/pkg/superpowers/decoy.py")
    for name in tracked:
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text("synthetic = 1\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "add", "--", *tracked], check=True
    )
    listed: list[str] = []
    run = subprocess.run

    def recording_run(*args: Any, **kwargs: Any) -> Any:
        result = run(*args, **kwargs)
        listed.extend(result.stdout.splitlines())
        return result

    monkeypatch.setattr(subprocess, "run", recording_run)
    monkeypatch.setitem(globals(), "_ROOT", tmp_path)

    with watch_access(*internal) as accesses:
        sources = _live_python_sources()

    assert (accesses, sorted(listed)) == ([], sorted([*live, "evals/run.py"]))
    assert sources == tuple(tmp_path / name for name in live)


def _imports_package(path: Path, package: str) -> bool:
    """Return whether one Python file imports the named package."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(
            alias.name == package for alias in node.names
        ):
            return True
        if (
            isinstance(node, ast.ImportFrom)
            and node.module is not None
            and (
                node.module == package or node.module.startswith(f"{package}.")
            )
        ):
            return True
    return False


def test_all_tracked_docs_svgs_have_no_embedded_date() -> None:
    svgs = _tracked_docs_svgs()
    assert svgs, "no tracked docs SVGs found"
    dated = [
        str(p.relative_to(_ROOT))
        for p in svgs
        if "<dc:date" in p.read_text(encoding="utf-8")
    ]
    assert not dated, f"non-deterministic (timestamped) docs SVGs: {dated}"


def test_preset_compare_html_has_no_embedded_date() -> None:
    assert _PRESET_COMPARE.exists(), f"missing {_PRESET_COMPARE}"
    text = _PRESET_COMPARE.read_text(encoding="utf-8")
    assert "<dc:date" not in text, (
        "preset_compare.html inlines a timestamped SVG "
        "(non-deterministic generator regression)"
    )


def test_disconnected_colorspacious_generator_is_removed() -> None:
    """Delete both outputs of the superseded standalone generator."""
    remaining = [
        str(path.relative_to(_ROOT))
        for path in _STALE_COLOR_GENERATORS
        if path.exists()
    ]
    assert not remaining, f"stale color generators remain: {remaining}"


def test_colorspacious_has_no_live_python_consumer() -> None:
    """Keep colorspacious out of executable source after migration."""
    consumers = [
        str(path.relative_to(_ROOT))
        for path in _live_python_sources()
        if _imports_package(path, "colorspacious")
    ]
    assert not consumers, f"live colorspacious consumers: {consumers}"


def test_colorspacious_is_not_a_declared_or_locked_dependency() -> None:
    """Remove the unused development dependency and its lock entry."""
    pyproject = _PYPROJECT.read_text(encoding="utf-8")
    declaration = re.search(
        r'^\s*"colorspacious(?:[^"\n]*)"\s*,?\s*$',
        pyproject,
        flags=re.MULTILINE,
    )
    assert declaration is None
    assert 'name = "colorspacious"' not in _UV_LOCK.read_text(encoding="utf-8")


def test_generate_assets_has_no_duplicate_oklab_conversion_kernel() -> None:
    """Use the package conversion SSOT instead of a docs-only duplicate."""
    source = _GENERATE_COLOR_ASSETS.read_text(encoding="utf-8")
    assert "def _oklch_lightness(" not in source


def test_swatch_ink_uses_the_package_wcag_rule_not_a_brightness_copy() -> None:
    """Docs swatch labels pick ink with ``dm.readable_text_color``.

    The colour sheets and the interpolation widget used to carry their own
    gamma-weighted brightness with a 0.45 threshold, a second luminance that
    disagreed with the package's WCAG rule on mid-tones.
    """
    source = _GENERATE_COLOR_ASSETS.read_text(encoding="utf-8")
    assert "def _text_brightness_rgb(" not in source
    assert "dm.readable_text_color(" in source
    js = (_DOCS / "_static" / "custom.js").read_text(encoding="utf-8")
    assert "lum < 0.45" not in js
    assert "function wcagLuminance(" in js
