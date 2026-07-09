"""Execute the python fences of the primary usage docs (G3).

The discovery block in ``usage_guide/colors.md`` shipped three calls
that crash (wrong signature, phantom names) — a resolvability scan
can't catch a wrong *signature*, so the fences are executed under Agg
with a small standard preamble. Fences that are intentionally
non-self-contained opt out with an HTML comment directly above::

    <!-- snippet: no-run -->
"""

from __future__ import annotations

import re
import textwrap
from pathlib import Path

import matplotlib
import pytest

matplotlib.use("Agg")

_REPO = Path(__file__).resolve().parents[1]
_DOCS = [
    _REPO / "docs" / "usage_guide" / "colors.md",
    _REPO / "docs" / "usage_guide" / "quickstart.md",
    _REPO / "docs" / "usage_guide" / "save_export.md",
    _REPO / "docs" / "color_system" / "categorical-palettes.md",
    _REPO / "docs" / "usage_guide" / "config.md",
    _REPO / "docs" / "usage_guide" / "extras.md",
    _REPO / "docs" / "usage_guide" / "interactive.md",
    _REPO / "docs" / "usage_guide" / "layout.md",
    _REPO / "docs" / "usage_guide" / "recipes.md",
    _REPO / "docs" / "usage_guide" / "styles.md",
    _REPO / "docs" / "usage_guide" / "tutorials.md",
    _REPO / "docs" / "color_system" / "colormaps.md",
    _REPO / "docs" / "color_system" / "colors.md",
    _REPO / "docs" / "color_system" / "space.md",
]

_FENCE = re.compile(r"```python\n(.*?)```", re.S)
_NO_RUN = "snippet: no-run"


def _snippets() -> list[tuple[str, int, str]]:
    out = []
    for doc in _DOCS:
        text = doc.read_text(encoding="utf-8")
        for m in _FENCE.finditer(text):
            lineno = text.count("\n", 0, m.start()) + 1
            preceding = text[: m.start()].rsplit("\n", 3)[-3:]
            if any(_NO_RUN in line for line in preceding):
                continue
            out.append((doc.name, lineno, m.group(1)))
    return out


def _rst_snippets() -> list[tuple[str, int, str]]:
    out = []
    for doc in sorted((_REPO / "docs" / "api").glob("*.rst")):
        lines = doc.read_text(encoding="utf-8").splitlines()
        i = 0
        while i < len(lines):
            if lines[i].strip() != ".. code-block:: python":
                i += 1
                continue

            lineno = i + 1
            preceding = lines[max(0, i - 3) : i]
            skip = any(_NO_RUN in line for line in preceding)

            j = i + 1
            while j < len(lines):
                stripped = lines[j].lstrip(" ")
                indent = len(lines[j]) - len(stripped)
                if indent >= 3 and stripped.startswith(":"):
                    j += 1
                    continue
                break

            if j < len(lines) and lines[j].strip() == "":
                j += 1

            body = []
            while j < len(lines):
                line = lines[j]
                if line.strip() == "":
                    body.append(line)
                    j += 1
                    continue

                stripped = line.lstrip(" ")
                indent = len(line) - len(stripped)
                if indent >= 3:
                    body.append(line)
                    j += 1
                    continue
                break

            if not skip:
                out.append(
                    (
                        f"api/{doc.name}",
                        lineno,
                        textwrap.dedent("\n".join(body)),
                    )
                )
            i = j
    return out


def _preamble_namespace() -> dict:
    import matplotlib.pyplot as plt
    import numpy as np

    import dartwork_mpl as dm

    dm.style.use("scientific")
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    ax.plot([1, 2, 3], [1, 2, 1.5])
    x = np.linspace(0.0, 1.0, 8)
    return {
        "plt": plt,
        "np": np,
        "dm": dm,
        "fig": fig,
        "ax": ax,
        # Common illustrative-fragment names so short fences run as-is.
        "x": x,
        "y": x**2,
        "y1": x,
        "y2": x + 0.5,
        "categories": ["A", "B", "C"],
        "values": [3.0, 1.5, 2.2],
        "gains": [1.0, 1.8, 1.4, 2.2],
        "baseline": 1.5,
    }


@pytest.mark.parametrize(
    ("doc", "lineno", "code"),
    _snippets(),
    ids=[f"{d}:{n}" for d, n, _ in _snippets()],
)
def test_snippet_executes(
    doc: str,
    lineno: int,
    code: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import matplotlib.pyplot as plt

    monkeypatch.chdir(tmp_path)
    ns = _preamble_namespace()
    try:
        exec(compile(code, f"{doc}:{lineno}", "exec"), ns)
    finally:
        plt.close("all")


@pytest.mark.parametrize(
    ("doc", "lineno", "code"),
    _rst_snippets(),
    ids=[f"{d}:{n}" for d, n, _ in _rst_snippets()],
)
def test_rst_snippet_executes(
    doc: str,
    lineno: int,
    code: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import matplotlib.pyplot as plt

    monkeypatch.chdir(tmp_path)
    ns = _preamble_namespace()
    try:
        exec(compile(code, f"{doc}:{lineno}", "exec"), ns)
    finally:
        plt.close("all")


def test_discovery_block_output_comments_are_true() -> None:
    """The ``# → [...]`` output comments in the discovery snippets must
    match reality (they were once fabricated)."""
    import dartwork_mpl as dm

    assert dm.list_palettes()[:5] == [
        "ad.blue",
        "ad.cyan",
        "ad.geekblue",
        "ad.gold",
        "ad.green",
    ]
    assert dm.list_colormaps()[:5] == [
        "dc.afterglow",
        "dc.amber",
        "dc.aurora",
        "dc.blaze",
        "dc.blue",
    ]
    import matplotlib as mpl

    assert dm.classify_colormap(mpl.colormaps["dc.aurora"]) == "Multi-Hue"
