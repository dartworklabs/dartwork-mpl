"""Committed docs asset SVGs/HTML must be deterministic (no embedded date).

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
