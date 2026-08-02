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
import re
import subprocess
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_DOCS = Path(__file__).resolve().parents[1] / "docs"

# Kept as a smoke check for the three generator-owned asset dirs covered by
# the original PR. The whole-docs guard below is the net contract.
_SVG_DIRS = (
    _DOCS / "usage_guide" / "images",
    _DOCS / "api" / "images",
    _DOCS / "color_system" / "theory_figures",
)

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
    result = subprocess.run(
        ["git", "ls-files", "--", "*.py"],
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


def test_tracked_docs_svgs_have_no_embedded_date() -> None:
    svgs = sorted(p for d in _SVG_DIRS for p in d.glob("*.svg"))
    assert svgs, "no docs asset SVGs found"
    dated = [
        str(p.relative_to(_DOCS))
        for p in svgs
        if "<dc:date" in p.read_text(encoding="utf-8")
    ]
    assert not dated, f"non-deterministic (timestamped) docs SVGs: {dated}"


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
