"""Re-run a figure script and write what its figure shows: ``python -m evals.probe SRC OUT [ARGS]``.

Runs in a throwaway copy of the agent's project. The backend is left as the
script finds it, as it was for the agent: on macOS the default ``macosx``
backend lays a figure out a fraction of a pixel differently from Agg, and
the re-render is compared with the agent's image. ``plt.show`` and
``plt.close`` do nothing, so no window opens and the figure survives the script.
The figure measured is the script's ``fig`` if it has one, else the last one
opened. Writes ``{"error", "figures": n, "figure": {...} | null}``.
"""

from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
from matplotlib.collections import PathCollection, QuadMesh
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
from matplotlib.text import Text

import dartwork_mpl as dm


def marks(fig: Figure) -> list[str]:
    """Which kinds of data marks the figure's axes hold."""
    found: set[str] = set()
    for ax in fig.axes:
        bars = [p for p in ax.patches if isinstance(p, Rectangle)]
        if len(bars) >= 2:
            found.add("bar")
        if any(len(line.get_xydata()) >= 2 for line in ax.lines):  # pyright: ignore[reportArgumentType]
            found.add("line")
        for coll in ax.collections:
            if isinstance(coll, QuadMesh):
                found.add("image")
            elif (
                isinstance(coll, PathCollection)
                and len(coll.get_offsets()) >= 2
            ):
                found.add("scatter")
        if ax.images:
            found.add("image")
    return sorted(found)


def describe(fig: Figure) -> dict[str, Any]:
    """Panels, marks, every visible text, legend, size and ``dm.check``."""
    found = dm.check(fig)  # draws the figure, so tick labels exist
    # An inset (ax.inset_axes) is a child of its axes, not one of fig.axes.
    insets = [child for ax in fig.axes for child in ax.child_axes]
    data_axes = [
        ax
        for ax in [*fig.axes, *insets]
        if ax.get_visible() and not hasattr(ax, "_colorbar")
    ]
    positions = {
        tuple(round(v, 3) for v in ax.get_position().bounds) for ax in data_axes
    }
    texts = [
        t.get_text()
        for t in fig.findobj(Text)
        if isinstance(t, Text) and t.get_visible() and t.get_text().strip()
    ]
    width, height = fig.get_size_inches()
    return {
        "panels": len(positions),
        "marks": marks(fig),
        "texts": texts,
        "legend": bool(fig.legends)
        or any(ax.get_legend() is not None for ax in fig.axes),
        "size_cm": [round(width * 2.54, 2), round(height * 2.54, 2)],
        "check": [
            {
                "rule": f.rule,
                "severity": str(f.severity),
                "message": f.message,
                "fix": f.fix,
            }
            for f in found
        ],
        "check_skipped": list(found.skipped),
    }


def main(argv: list[str]) -> int:
    """Run the script, measure its figure, write the JSON."""
    source, out, args = Path(argv[0]), Path(argv[1]), argv[2:]
    plt.show = lambda *a, **k: None  # pyright: ignore[reportAttributeAccessIssue, reportUnknownLambdaType]
    plt.close = lambda *a, **k: None  # pyright: ignore[reportAttributeAccessIssue, reportUnknownLambdaType]
    report: dict[str, Any] = {"error": None, "figures": 0, "figure": None}
    scope: dict[str, Any] = {}
    sys.argv = [str(source), *args]
    try:
        scope = runpy.run_path(str(source), run_name="__main__")
    except SystemExit:
        pass
    except BaseException as exc:  # noqa: BLE001 - recorded, the figure may stand
        report["error"] = f"{type(exc).__name__}: {exc}"
    numbers = plt.get_fignums()
    report["figures"] = len(numbers)
    fig = scope.get("fig")
    if not isinstance(fig, Figure) and numbers:
        fig = plt.figure(numbers[-1])
    if isinstance(fig, Figure):
        try:
            report["figure"] = describe(fig)
        except Exception as exc:  # noqa: BLE001
            report["error"] = f"measuring failed: {type(exc).__name__}: {exc}"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
