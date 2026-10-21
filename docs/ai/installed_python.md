# Installed Python agent workflow

This route needs the core `dartwork-mpl` installation and Python file/image
access, without MCP, a repository checkout or a lint CLI. Use existing APIs;
matplotlib Figure/Axes and artist setters stay native. A human can request a
plot or revision in ordinary language; the agent performs this loop.

## Read the installed guidance and template source

```python
from importlib.resources import files
from pathlib import Path
import dartwork_mpl as dm

print(dm.get_agent_doc("AGENTS"))
print(dm.get_prompt("01-policy"))
print(dm.get_prompt("03-recipes"))
print(dm.get_prompt("02-anti-patterns"))

# Ranking metadata is available without MCP; source_path is repo-relative.
root = files("dartwork_mpl").joinpath("asset", "prompt", "05-templates")
Path("output").mkdir(exist_ok=True)
for tier in ("basic", "advanced"):
    match = dm.find_template("line time series", top_k=1, tier=tier)[0]
    folder = root if tier == "basic" else root.joinpath("advanced")
    source = folder.joinpath(f"{match['template_id']}.py").read_text(encoding="utf-8")
    print(tier, match["template_id"], match["source_path"])
    Path(f"output/template-{tier}.py").write_text(source, encoding="utf-8")
    print(source)  # inspect/adapt; retrieving a template does not execute it
```

`find_template(...)[0]["source_path"]` identifies the repository gallery source;
it is not an installed filesystem path. `importlib.resources` above reads the
bundled executable basic/advanced source. Keep the selected preset and existing
scoped overrides when adapting it. Templates are starting points, not chart or
property limits. For equal, ratio, spanning, nested and whole-canvas container
layouts, read `dm.get_prompt("03-recipes")` or [Layout](../usage_guide/layout.md#native-multi-panel-layouts).

## Check data without silently closing gaps

`dm.validate_data(x, y)` returns cleaned NumPy arrays, not a report or boolean.
Its default `allow_nan=False` removes NaN/Inf observations and aligned rows,
which can connect a line across a missing observation. Decide the blank/missing
policy first. Preserve meaningful gaps with `allow_nan=True` and separate shape,
alignment, infinity and finite-observation checks as below. That option also
allows infinities; it is not a complete shape/domain validator. Do not coerce
arbitrary categorical blanks to zero or drop rows without the user's intent.
The MCP `validate_plot_data(plot_type, data_json, ...)` is a distinct tool with
chart-specific input checks; it is not `dm.validate_data` or a Python alias.

## Native Figure → full report → files → actual image review

Save the following as `plot.py` and run `python plot.py`. In a notebook, replace
`Path(__file__)` with the path where you saved the exact executed source.

```python
from dataclasses import asdict
from pathlib import Path
import json
import matplotlib.pyplot as plt
import numpy as np
import dartwork_mpl as dm

# Blank observations represent missing readings, so retain a visible line gap.
x_input = [0, 1, 2, 3, 4, 5]
y_input = [1.0, 1.8, None, 2.1, 1.7, 2.5]
x = np.asarray(x_input, dtype=float)
y = np.asarray([np.nan if v is None else v for v in y_input], dtype=float)
if x.ndim != 1 or y.ndim != 1 or x.shape != y.shape:
    raise ValueError("Expected aligned one-dimensional x/y observations")
if not np.isfinite(x).all() or np.isinf(y).any() or np.isfinite(y).sum() < 2:
    raise ValueError("Expected finite x and at least two finite y observations")
x, y = dm.validate_data(x, y, allow_nan=True)

dm.style.use("report")
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
line, = ax.plot(x, y, color="oc.blue9", label="Observed")
ax.set(xlabel="Time (s)", ylabel="Response", title="Missing reading retained")
ax.legend(loc="upper left")
dm.simple_layout(fig, margin="2mm")

# Save this complete script as plot.py before running it.
source_path = Path(__file__)
code = source_path.read_text(encoding="utf-8")
report = {"lint": [asdict(item) for item in dm.lint_code(code)],
          "visual": [asdict(item) for item in dm.validate_figure(fig)]}
Path("output").mkdir(exist_ok=True)
Path("output/figure-v1.py").write_text(code, encoding="utf-8")
Path("output/figure-v1-report.json").write_text(json.dumps(report, indent=2))
dm.save_formats(fig, "output/figure-v1", formats=("png", "pdf"),
                bbox_inches=None)
```

Read every lint and visual finding, including its severity, message and detail.
`CHECK_FAILED` means validation is incomplete. An empty heuristic warning list
cannot prove visual or scientific correctness. `save_formats` returns `None`;
its return value is not clean-validation evidence. It saves despite warnings.
Preserve advisory findings and explain intentional choices rather than hiding
warnings or changing requested colors, dimensions or local overrides.

**Open and inspect the actual `output/figure-v1.png` with the agent's image
viewer**, then review the PDF at its target physical size (or rasterize the PDF
and inspect that page). Check the gap, labels, fonts, legend, clipping and data.
Reading filenames, file sizes or the JSON report is not image review. If the
agent has no image reader, disclose that missing step; do not claim completion.

## Revise to a separate stem and hand off

After reviewing v1, copy `plot.py` to `plot-v2.py`. In the copy, replace all
`figure-v1` output stems with `figure-v2` and insert this requested label-only
revision immediately before `source_path = Path(__file__)`. Run
`python plot-v2.py`, then inspect v2 PNG/PDF and its full report. This retains
v1 source/files and saves the exact revised script under the new stem.
Repeated “one more step” acts on retained current label values, not the preset
base; retain previous local edits when preparing another revision.
Keep the current layout when the enlarged labels fit. If image/content inspection
shows clipping or overlap, refit using the original `simple_layout` kwargs
(`margin="2mm"` here, and the original `gs` if used), then inspect again and
report any necessary movement of axes or anchored legends.

```python
# Insert before the source/report/export block in plot-v2.py.
for label in (ax.xaxis.label, ax.yaxis.label):
    label.set_fontsize(label.get_fontsize() + 1)
# Draw and inspect changed labels before deciding whether a refit is needed.
fig.canvas.draw()
# Keep existing axes/legend positions when labels still fit. Only if needed:
# dm.simple_layout(fig, margin="2mm")  # reuse the original margin/grid kwargs
```

Hand off the exact source, PNG, PDF and full report for each revision, the
chosen preset and physical canvas, data/gap policy, requested changes, retained
warnings and what images were actually reviewed. Preserve original artifacts;
use another stem for the next revision. These deterministic examples demonstrate
the APIs, not evidence that an autonomous agent successfully followed the loop.
