"""A/B sheet: per host and case, the noskill and skill figures side by side.

    uv run python evals/agentic/ab_sheet.py RUN_DIR [--rep 1]

Both arms (and, for edit cases, the base figure) are drawn at one common
scale (the same pixels per figure inch), so a size difference between arms
is visible. Each figure is captioned with inspection, lint findings
(critical + warning, then rule ids), defects, preset overrides, tokens and
task success. Writes ``RUN_DIR/ab-sheet.png``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from common import read_json
from matplotlib import font_manager
from PIL import Image, ImageDraw, ImageFont

CELL_W, CELL_H, PAD, CAP_H, HEAD_W = 1000, 640, 16, 92, 400


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = font_manager.findfont(
        font_manager.FontProperties(
            family="DejaVu Sans", weight="bold" if bold else "normal"
        )
    )
    return ImageFont.truetype(path, size)


def _caption(arm: str, s: dict | None) -> list[str]:
    if not s:
        return [f"{arm}: not scored"]
    yn = {True: "yes", False: "no", None: "-"}
    lint = s.get("lint") or {}
    rules = ", ".join(sorted(lint.get("rules") or {}))
    tok = (s.get("tokens") or {}).get("total")
    return [
        f"{arm}  |  task {yn[s.get('task_success')]}  |  inspected "
        f"{yn[s.get('inspection_observed')]}  |  lint {s.get('lint_findings', '-')}"
        f"  |  defects {(s.get('defects') or {}).get('total', '-')}  |  overrides "
        f"{s.get('preset_overrides_total', '-')}  |  tokens "
        f"{'-' if tok is None else f'{tok / 1000:,.0f}k'}",
        f"lint rules: {rules or 'none'}"
        + (
            "  |  skill invoked"
            if (s.get("skill_usage") or {}).get("invoked")
            else ""
        ),
    ]


def _img(path: Path) -> Image.Image | None:
    return Image.open(path).convert("RGB") if path.exists() else None


def row(run_dir: Path, host: str, case: str, rep: int) -> Image.Image:
    units = {
        arm: run_dir / host / case / f"{arm}-r{rep}"
        for arm in ("noskill", "skill")
    }
    imgs = {
        arm: _img(u / "artifacts" / "figure.png") for arm, u in units.items()
    }
    base = _img(units["noskill"] / "base_out" / "figure.png")
    panels = ([("base", base)] if base else []) + [
        (arm, imgs[arm]) for arm in ("noskill", "skill")
    ]
    # one scale for every panel in the row: px per source px (same dpi ->
    # same px per figure inch), fitted so the largest figure fills its cell
    present = [im for _, im in panels if im is not None]
    k = (
        min(
            min(CELL_W / im.width, (CELL_H - CAP_H) / im.height)
            for im in present
        )
        if present
        else 1.0
    )
    width = HEAD_W + len(panels) * (CELL_W + PAD) + PAD
    out = Image.new("RGB", (width, CELL_H + 2 * PAD), "white")
    d = ImageDraw.Draw(out)
    d.text((PAD, PAD), host, font=_font(30, True), fill="#111")
    d.text((PAD, PAD + 44), case, font=_font(22), fill="#333")
    x = HEAD_W
    for arm, im in panels:
        d.rectangle(
            [x, PAD, x + CELL_W, PAD + CELL_H - 1], outline="#cccccc", width=2
        )
        if im is None:
            d.text(
                (x + 20, PAD + 20),
                f"{arm}: no figure",
                font=_font(22),
                fill="#888",
            )
        else:
            t = im.resize(
                (max(1, round(im.width * k)), max(1, round(im.height * k))),
                Image.LANCZOS,
            )
            out.paste(t, (x + (CELL_W - t.width) // 2, PAD + 4))
        lines = (
            ["base (edit input)"]
            if arm == "base"
            else _caption(arm, read_json(units[arm] / "score.json"))
        )
        for j, line in enumerate(lines):
            d.text(
                (x + 12, PAD + CELL_H - CAP_H + 10 + j * 30),
                line,
                font=_font(20, j == 0),
                fill="#111" if j == 0 else "#555",
            )
        x += CELL_W + PAD
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--rep", type=int, default=1)
    a = ap.parse_args()
    keys = sorted(
        {
            (u.parent.parent.parent.name, u.parent.parent.name)
            for u in a.run_dir.glob("*/*/*/run.json")
        }
    )
    rows = [row(a.run_dir, h, c, a.rep) for h, c in keys]
    width = max(r.width for r in rows)
    head = 90
    sheet = Image.new(
        "RGB", (width, head + sum(r.height for r in rows)), "white"
    )
    manifest = read_json(a.run_dir / "manifest.json") or {}
    ImageDraw.Draw(sheet).text(
        (PAD, 24),
        f"{a.run_dir.name}: noskill vs skill (same wheel {manifest.get('wheel', {}).get('sha256', '')[:12]}, "
        f"--hide-grading); every figure in a row at one scale",
        font=_font(34, True),
        fill="#111",
    )
    y = head
    for r in rows:
        sheet.paste(r, (0, y))
        y += r.height
    out = a.run_dir / "ab-sheet.png"
    sheet.save(out, optimize=True)
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
