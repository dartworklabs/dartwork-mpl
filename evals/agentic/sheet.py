"""Contact sheet per host (and arm): every unit's original figure with its case id.

    uv run python evals/agentic/sheet.py RUN_DIR

Edit cases show the base figure (left) next to the agent's result (right).
The caption's second line repeats the scores so a reader can check them
against the picture. Writes ``RUN_DIR/sheet-<host>-<arm>.png``.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from common import read_json
from matplotlib import image as mimage

COLS = 3


def _thumb(ax, path: Path, title: str | None = None) -> None:
    ax.set_axis_off()
    if path.exists():
        img = mimage.imread(path)
        step = max(1, img.shape[1] // 1100)
        ax.imshow(img[::step, ::step], interpolation="lanczos")
    else:
        ax.text(
            0.5,
            0.5,
            "no figure",
            ha="center",
            va="center",
            fontsize=11,
            color="0.4",
        )
    if title:
        ax.text(
            -0.01,
            0.5,
            title,
            transform=ax.transAxes,
            rotation=90,
            ha="right",
            va="center",
            fontsize=10,
            color="0.4",
        )


def _caption(score: dict | None) -> str:
    if not score:
        return "not scored"
    yn = {True: "yes", False: "no", None: "-"}
    d = (score.get("defects") or {}).get("total", "-")
    flag = " | CONTAMINATED" if score.get("contaminated") else ""
    return (
        f"exec {yn[score.get('execution_success')]} | task {yn[score.get('task_success')]} | "
        f"inspected {yn[score.get('inspection_observed')]} | defects {d}{flag}"
    )


def sheet(run_dir: Path, host: str, arm: str, units: list[Path]) -> Path:
    cols = min(COLS, len(units))
    rows = math.ceil(len(units) / cols)
    fig = plt.figure(figsize=(cols * 6.4, rows * 5.2))
    outer = fig.add_gridspec(rows, cols, hspace=0.3, wspace=0.08)
    for k, unit in enumerate(units):
        cell = outer[k // cols, k % cols]
        score = read_json(unit / "score.json")
        after = unit / "artifacts" / "figure.png"
        if (unit / "base_out" / "figure.png").exists():
            sub = cell.subgridspec(2, 1, hspace=0.15)
            _thumb(
                fig.add_subplot(sub[0, 0]),
                unit / "base_out" / "figure.png",
                "before",
            )
            ax = fig.add_subplot(sub[1, 0])
            _thumb(ax, after, "after")
            label_ax = fig.add_subplot(cell, frameon=False)
            label_ax.set_axis_off()
        else:
            label_ax = fig.add_subplot(cell)
            _thumb(label_ax, after)
        held = " (held-out)" if (score or {}).get("held_out") else ""
        label_ax.text(
            0.5,
            -0.04,
            f"{unit.parent.name}{held}  [{unit.name}]\n{_caption(score)}",
            transform=label_ax.transAxes,
            ha="center",
            va="top",
            fontsize=12,
        )
    fig.suptitle(f"{run_dir.name} — {host} / {arm}", fontsize=15)
    out = run_dir / f"sheet-{host}-{arm}.png"
    fig.savefig(out, dpi=100)
    plt.close(fig)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("run_dir", type=Path)
    a = ap.parse_args()
    groups: dict[tuple[str, str], list[Path]] = {}
    for run_json in sorted(a.run_dir.glob("*/*/*/run.json")):
        unit = run_json.parent
        groups.setdefault(
            (unit.parent.parent.name, unit.name.split("-r")[0]), []
        ).append(unit)
    for (host, arm), units in sorted(groups.items()):
        print(sheet(a.run_dir, host, arm, units))
    return 0


if __name__ == "__main__":
    sys.exit(main())
