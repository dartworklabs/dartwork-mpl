"""#810, the check side: a text whose ink is partly under 3:1.

``TEXT_CONTRAST`` today compares a text with the one colour behind the
centre of its box. This reads every pixel of ink against what is drawn
behind it and judges half-em slices along the text, so a note that leaves
a pale bar for a dark one is seen. ``uv run python -m
spike.split_text.partial`` runs it over the corpus beside today's rule.
"""

from __future__ import annotations

import contextlib
import io
import os
import runpy
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import to_hex

import dartwork_mpl as dm

from . import cases, legible
from .columns import TABLES

if TYPE_CHECKING:
    from matplotlib.figure import Figure
    from matplotlib.text import Text

CORPUS = Path(__file__).resolve().parents[2] / "tests" / "corpus"


@dataclass(frozen=True)
class Faint:
    """A text with a slice the reader cannot make out."""

    text: Text
    panel: int
    low: float
    ratio: float
    paper: str

    @property
    def whole(self) -> bool:
        """Nearly all of it is faint: today's rule is meant to see these."""
        return self.low > 0.9


def faint_texts(fig: Figure) -> list[Faint]:
    """The texts placed in an Axes that have a faint slice."""
    pieces = {
        id(p)
        for table in TABLES.get(fig, [])
        for cell in table
        for p in cell.pieces
    }
    placed = [
        (i, t)
        for i, ax in enumerate(fig.axes)
        for t in ax.texts
        if t.get_visible() and t.get_text().strip() and id(t) not in pieces
    ]
    if not placed:
        return []
    found: list[Faint] = []
    read = legible.samples(fig, [t for _i, t in placed])
    for (panel, text), got in zip(placed, read, strict=True):
        if len(got.paper) < 8 or got.worst_slice < legible.FAINT_SLICE:
            continue
        ratios = got.ratios
        worst = int(np.argmin(ratios))
        found.append(
            Faint(
                text,
                panel,
                got.low,
                float(np.percentile(ratios, 2)),
                to_hex(got.paper[worst]),
            )
        )
    return found


def report(fig: Figure) -> str:
    """The finding as ``dm.check`` would print it, or an empty string."""
    found = faint_texts(fig)
    if not found:
        return ""
    w = max(found, key=lambda f: f.low)
    short = " ".join(w.text.get_text().split())[:30]
    part = "all" if w.whole else f"{w.low:.0%}"
    return (
        f"TEXT_CONTRAST: Axes[{w.panel}]: {len(found)} text(s) with ink under "
        f"3:1 on what is behind it, worst {short!r}: {part} of its ink, down "
        f"to {w.ratio:.2f}:1 on {w.paper}\n  try: move it onto one "
        "background; or dm.legible(text) picks the ink that reads on each "
        "(a halo over a point cloud)"
    )


def corpus() -> list[str]:
    """Today's rule and this one on every corpus figure."""
    lines: list[str] = []
    totals = {"figures": 0, "today": 0, "proposed": 0, "both": 0}
    original = dm.save_formats
    for script in sorted(
        [*CORPUS.glob("charts/*.py"), *CORPUS.glob("rough/*.py")]
    ):
        seen: list[tuple[bool, list[Faint]]] = []

        def capture(fig, *args, seen=seen, **kwargs):
            today = "TEXT_CONTRAST" in dm.check(fig).rules
            seen.append((today, faint_texts(fig)))

        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            dm.save_formats = capture
            try:
                with (
                    plt.rc_context(),
                    contextlib.redirect_stdout(io.StringIO()),
                ):
                    runpy.run_path(str(script), run_name="__main__")
            finally:
                dm.save_formats = original
                os.chdir(cwd)
                plt.close("all")
        for today, faint in seen:
            totals["figures"] += 1
            totals["today"] += today
            totals["proposed"] += bool(faint)
            totals["both"] += today and bool(faint)
            if today or faint:
                partly = sum(not f.whole for f in faint)
                lines.append(
                    f"  {script.parent.name}/{script.stem}: today "
                    f"{'TEXT_CONTRAST' if today else '-'}; proposed "
                    f"{len(faint)} text(s), {partly} only partly faint"
                )
    head = (
        f"corpus: {totals['figures']} figures; today's TEXT_CONTRAST on "
        f"{totals['today']}, the proposed rule on {totals['proposed']} "
        f"({totals['both']} on both)"
    )
    return [head, *lines]


def main() -> None:
    """The proposed finding on each #810 scene, then the corpus."""
    dm.quiet()
    lines = ["the proposed finding on each scene, as drawn:"]
    for name, scene in cases.SCENES.items():
        fig, _texts = scene()
        today = [f.rule for f in dm.check(fig) if f.rule == "TEXT_CONTRAST"]
        lines.append(f"- {name}: today {today or 'nothing'}")
        lines.append(
            "  " + (report(fig) or "proposed: nothing").replace("\n", "\n  ")
        )
        plt.close(fig)
    lines += ["", *corpus()]
    text = "\n".join(lines)
    print(text)
    cases.OUT.mkdir(parents=True, exist_ok=True)
    (cases.OUT / "partial.txt").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
