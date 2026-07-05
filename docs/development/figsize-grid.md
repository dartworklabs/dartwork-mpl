---
orphan: true
---

# Per-panel sizing with `figsize_grid`

`dm.figsize(width, aspect)` sizes the whole matplotlib figure.
`dm.figsize_grid(panel_width, aspect, ncols=..., nrows=...)` sizes a
multi-panel figure from the desired physical size of each panel.

```python
import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("scientific")
fig, axes = plt.subplots(
    nrows=2,
    ncols=3,
    figsize=dm.figsize_grid(
        "6cm",
        "standard",
        ncols=3,
        nrows=2,
        gap="0.6cm",
    ),
)

# ... draw on axes ...
dm.simple_layout(fig)
```

The calculation is:

- figure width = `ncols * panel_width + (ncols - 1) * gap`
- figure height = `nrows * panel_height + (nrows - 1) * gap`
- panel height = `panel_width * aspect`

`gap` is a physical distance, unlike matplotlib's relative `wspace` and
`hspace` settings. Matplotlib can still adjust subplot positions after
the figure size is chosen, so the final rendered panel spacing is an
approximation. Pair `figsize_grid` with `dm.simple_layout(fig)` for the
deterministic content-aware layout path used by dartwork-mpl.
