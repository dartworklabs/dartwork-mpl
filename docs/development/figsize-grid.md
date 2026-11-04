---
orphan: true
---

# Per-panel sizing with `figsize_grid`

`dm.figsize(width, aspect)` sizes the whole matplotlib figure.
`dm.figsize_grid(panel_width, aspect, ncols=..., nrows=...)` sizes a
whole multi-panel figure from nominal panel-size and gap inputs. It does
not create Axes or set GridSpec spacing.

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

`gap` is a physical-distance input to this size calculation, unlike
matplotlib's relative `wspace` and `hspace` settings. It is not applied to
those settings. Labels, outer margins and native subplot spacing reduce or
redistribute the available area: neither exact panel Axes dimensions nor
exact cm gaps are guaranteed. Measure rendered Axes and content bounds
separately from the whole figure. Pair `figsize_grid` with `dm.simple_layout(fig)` for the
deterministic content-aware layout path used by dartwork-mpl.
