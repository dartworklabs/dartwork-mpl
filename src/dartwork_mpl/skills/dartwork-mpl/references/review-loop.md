# Render, inspect, revise

Run this loop for every figure and again for every revision. A figure is
done when you have looked at the saved PNG, not when the script ran.

```python
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import dartwork_mpl as dm

dm.style.use("report")
x = np.linspace(0, 10, 101)
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
ax.plot(x, np.sin(x), label="Measured")
ax.plot(x, np.cos(x), label="Model")
ax.set(xlabel="Time (s)", ylabel="Signal")
ax.legend()
dm.simple_layout(fig)

for finding in dm.validate_figure(fig, quiet=True):
    print(finding.severity.value, finding.check_id, finding.message)
Path("output").mkdir(exist_ok=True)
dm.save_formats(fig, "output/figure-v1", formats=("png", "pdf"), validate=False)
plt.close(fig)
```

## Look at the image

Open `output/figure-v1.png` with the image tool you have (Claude Code: Read
the file; Codex: view_image). Check that:

- every title, label, tick label and legend entry is inside the canvas and
  readable at the printed size;
- nothing overlaps: text on text, legend on data, labels between panels;
- the plotted data matches the input (count, gaps, order, units);
- panel sizes and empty space look intended.

If you cannot view images, say so in your answer instead of claiming the
figure was reviewed.

## Read the findings

WARNING findings are defects to fix or explain; INFO findings are hints.

| check_id | Means | Usual fix |
|---|---|---|
| `OVERFLOW`, `CLIPPED_TEXT` | text outside the canvas or axes | `dm.simple_layout(fig)` after the last artist; `margin=` |
| `OVERLAP`, `CROSS_AXES_OVERLAP` | text collides | more `hspace`/`wspace`, fewer or rotated ticks |
| `LEGEND_OVERFLOW` | legend too large or off the canvas | fewer columns, outside legend, direct labels |
| `TICK_CROWD`, `TICK_ROTATION` | crowded or rotated tick labels | `MaxNLocator(nbins=5)`, `dm.avoid_tick_overlap(ax)` |
| `TICK_DECIMAL`, `UNIT_DUP` | odd precision, unit repeated | `dm.set_decimal(ax, yn=1)`, unit in the axis label only |
| `MIN_FONT_SIZE`, `TEXT_CONTRAST` | text too small or faint | `dm.fs(0)` or larger, darker colour |
| `MARGIN_ASYMMETRY`, `EMPTY_AXES` | lopsided margins, empty panel | rerun `simple_layout`, remove the panel |
| `GRAYSCALE_SAFETY` (INFO) | similar grey values | mention it; change colours only when asked |
| `CHECK_FAILED` | a check could not run | the check is incomplete; say so |

A twin-axes pair can report `CROSS_AXES_OVERLAP` for its shared x ticks;
that one is a false positive.

## Revise

1. Change only what the image, a WARNING or the user asked for.
2. Save under the next stem (`output/figure-v2`) and keep v1.
3. Look at the new PNG again.
4. Report what changed, which warnings remain and why.

Lint a script before running it: `dm.lint_code(Path("plot.py").read_text())`
returns issues with `rule_id`, `severity` and `fix_suggestion`; fix every
`critical` one. Explicit user values flagged as `fontsize-literal` or
`linewidth-literal` stay as the user set them.
