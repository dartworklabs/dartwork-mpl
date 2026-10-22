# Layout robustness — #523 stage 2 (style-invariant bug fixes)

Measured on main c332c7ab, ported onto the ADR 0005 structure at 2fa337c4. Unchanged: rcParams, presets,
fonts, spines, colours, `simple_layout`'s default `margin=0`, public names, MCP.

## Changes

1. **Side titles.** `_figure_geometry.axes_titles` is the one reader of `ax._left_title`/`_right_title` (kept while
   the text equals `ax.get_title(loc)`); `simple_layout` and OVERFLOW, CLIPPED_TEXT, OVERLAP and
   CROSS_AXES_OVERLAP use it. The layout drops overhang it cannot fix: text anchored at or past one axes
   edge (left title, `transAxes` x=0 subtitle) beyond the opposite edge, and text wider than the canvas.
   Chasing those shrank the axes every iteration (advanced bar/heatmap under presentation: width ≤0.001).
2. **Figure text.** Roles first (suptitle → top, supxlabel → bottom, supylabel → left, each on its half);
   other text in the outer 15 % band (inclusive, 1e-9 tolerance) reserves along its reading direction;
   the rest keeps the nearest edge as on main. `set_in_layout(False)` text reserves nothing.
3. **Twins.** CROSS_AXES_OVERLAP skips a hidden axis's labels (twins hide the shared one); titles still count.
4. **Axes3D.** Window, each axis's full tight bbox and the legend replace the per-tick walk; titles and
   2-D texts go through the same no-chase rule as item 1.
5. **Template text (separate commit, a proposal).** Line breaks in the advanced bar and waterfall
   headlines. Without it the two presentation headlines stay oversized, are reported, cost no width.

## Evidence (main → branch)

- New tests (`_figure_geometry/tests/test_axes_text.py`, `layout/tests/test_layout_robustness.py`,
  `validate/tests/…twins.py`, `tests/test_template_title_layout.py`): main 73 failed / 29 passed, 3 cannot
  import (14 failures need the new `_reservation_edge`); branch 105 passed, also on matplotlib 3.10.1.
- Advanced templates with a title outside the canvas: scientific 10/18, report 10/18, presentation 11/18
  → 0, 0, 2 (fixes only) → 0, 0, 0 (with the template commit). No xfail: an outside title must be wider
  than its anchor's room, be reported, and re-running the layout without it must not widen the axes.
- Repros: left title y 1170–1203 on a 1151 px canvas, unreported → inside. KR left suptitle: axes x0
  0.382 → 0.071. `plot_3d.py` axes 0.158² → 0.931². twinx: 1 CROSS_AXES_OVERLAP → 0. Pixel baselines
  14/14 unchanged (also on 3.10.1); shipped-colour hash 6/6.
- Checks over 36 templates × 3 presets: −6 CROSS_AXES_OVERLAP (twins), −413 OVERLAP (collapsed heatmap);
  new OVERLAP in small_multiples (`label_axes` letters sit on the left titles: real) and OVERFLOW for
  the oversized texts; `plot_3d` CLIPPED_TEXT 3 → 8 (stale 3-D ticks, below).

## Left out, with findings

- **Bug 5, glyph ink at `margin=0`.** Ink reaches 1.4–2.4 px at 300 dpi past `get_window_extent`
  (report-kr ylabel 2.4 px left, title 1.8 px up; Roboto 1.4 px): anti-aliasing and bitmap snapping sit
  outside the metric box. A ~0.6 pt ink guard on measured text would fix it but moves almost every
  figure ~2 px (13 of 14 baselines have ink in an outermost row or column): its own approved change.
- Bar's subtitle still overflows under report (3 px) and presentation, reported; needs shorter text.
- Checks read mplot3d tick labels at stale positions (false OVERFLOW/CLIPPED_TEXT): stage 3.
  The `measure_overflow` oracle in `layout/tests/test_layout.py` still reads `ax.title` only.

## Port onto the ADR 0005 structure

The title adapter lives in the `_figure_geometry` platform unit (no new unit); the edge rule returns a
typed `_Edge` and feeds `_Sides`. Tests sit next to the slice they pin; the template matrix is cross-cutting.

## PoC — `uv run python poc.py OUT_DIR` on main, on the fixes, and with the template commit

```python
import os, re, sys, tempfile, warnings  # noqa: E401
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import dartwork_mpl as dm
warnings.simplefilter("ignore")
OUT, TPL = Path(sys.argv[1]).resolve(), Path(dm.__file__).parent / "asset/prompt/05-templates"
OUT.mkdir(parents=True, exist_ok=True)
def save(fig, name, pdf=False):
    ids = {w.check_id for w in dm.validate_figure(fig, quiet=True)}
    found = sorted(ids & {"OVERFLOW", "CLIPPED_TEXT", "CROSS_AXES_OVERLAP"})
    box = [round(float(v), 3) for v in fig.axes[0].get_position().bounds]
    print(f"{name}: axes[0] x0,y0,w,h={box} warnings={found}")
    for ext in ("png", "pdf") if pdf else ("png",):
        fig.savefig(OUT / f"{name}.{ext}", dpi=150)
    plt.close(fig)
def new(preset, aspect="standard"):
    dm.style.use(preset)
    return plt.subplots(figsize=dm.figsize("13cm", aspect))
fig, ax = new("scientific")
ax.plot([1, 3, 2])
ax.set_title("Revenue has doubled", loc="left")
dm.simple_layout(fig)
save(fig, "1_left_title")
fig, ax = new("report-kr")
ax.plot(np.arange(12), np.linspace(10, 21, 12) + np.sin(np.arange(12)))
ax.set(xlabel="월", ylabel="매출 (억 원)")
fig.suptitle("매출이 1년 사이 두 배로 늘었다", x=0.01, ha="left", fontweight=dm.fw(1))
fig.text(0.01, 0.92, "2024년 월별 매출, 단위 억 원", va="top")
fig.text(0.01, 0.01, "Source: 내부 집계", va="bottom")
dm.simple_layout(fig)
save(fig, "2_kr_suptitle")
fig, ax = new("report-kr", "wide")
ax.bar(np.arange(12), np.linspace(120, 210, 12), alpha=0.4)
ax.set(ylabel="매출 (억 원)", title="월별 매출과 이익률")
ax2 = ax.twinx()
ax2.plot(np.arange(12), np.linspace(18, 31, 12), color="C1", marker="o")
ax2.set_ylabel("이익률 (%)")
dm.simple_layout(fig)
save(fig, "3_twinx")
dm.style.use("report")
fig = plt.figure(figsize=dm.figsize("13cm", "square"))
ax = fig.add_subplot(projection="3d")
x, y = np.meshgrid(np.linspace(-2, 2, 30), np.linspace(-2, 2, 30))
ax.plot_surface(x, y, np.exp(-(x**2 + y**2)), cmap="dc.blue")
ax.set(xlabel="x (m)", ylabel="y (m)", zlabel="z (energy)")
ax.view_init(elev=35, azim=-120)
dm.simple_layout(fig)
save(fig, "4_3d_camera", pdf=True)
for rel, preset in [("plot_3d.py", None), ("advanced/bar.py", None), ("advanced/bar.py", "presentation"),
                    ("advanced/heatmap.py", "presentation"), ("advanced/stacked_bar.py", None),
                    ("advanced/waterfall.py", "presentation")]:
    src = (TPL / rel).read_text()
    if preset:
        src = re.sub(r'dm\.style\.use\("[^"]+"\)', f'dm.style.use("{preset}")', src)
    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as td:  # templates save relative to cwd
        os.chdir(td)
        try:
            exec(compile(src, rel, "exec"), {"__name__": "__main__"})
        finally:
            os.chdir(cwd)
    save(plt.gcf(), f"5_{Path(rel).stem}_{preset or 'own'}")
```
