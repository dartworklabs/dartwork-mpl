# Tutorials

End-to-end workflows for common use cases. Each tutorial takes you from raw data
to a finished, export-ready figure.

::::{grid} 1 1 2 2
:gutter: 2

:::{grid-item-card} Paper Figure
Create a publication-ready two-panel figure for an academic paper using the
`scientific` preset, GridSpec layout, and panel labels.

[Paper figure tutorial](#paper-figure)
:::

:::{grid-item-card} Korean Operations Report
Build a weekly operations chart with Korean labels using the `report-kr`
preset and bar+line combo.

[Korean operations report tutorial](#korean-operations-report)
:::

:::{grid-item-card} Dark Mode Notebook
Set up a Jupyter workflow with the `dark` preset, retina display, and
`save_and_show` for interactive exploration.

[Dark mode tutorial](#dark-mode-notebook)
:::

::::

---

(paper-figure)=
## Paper Figure (scientific preset)

A typical journal submission requires a multi-panel figure at specific dimensions
with consistent typography. Here's a complete workflow:

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm
import numpy as np

# 1. Apply style — scientific preset for journal figures
dm.style.use("scientific")

# 2. Create figure at single-column width (3.5 inches ~ 9 cm)
fig = plt.figure(figsize=(dm.cm2in(17), dm.cm2in(7)), dpi=300)
gs = fig.add_gridspec(1, 2, wspace=0.35)
ax1 = fig.add_subplot(gs[0])
ax2 = fig.add_subplot(gs[1])

# 3. Panel (a): Time series with error band
t = np.linspace(0, 5, 200)
signal = np.exp(-0.3 * t) * np.sin(2 * np.pi * t)
noise = 0.1 * np.random.randn(200)
ax1.plot(t, signal, color="oc.blue6", lw=dm.lw(1))
ax1.fill_between(t, signal - 0.15, signal + 0.15,
                 color="oc.blue2", alpha=0.4)
ax1.set_xlabel("Time [s]", fontsize=dm.fs(0))
ax1.set_ylabel("Amplitude [V]", fontsize=dm.fs(0))

# 4. Panel (b): Frequency spectrum
freq = np.fft.rfftfreq(200, d=0.025)
spectrum = np.abs(np.fft.rfft(signal + noise))
ax2.semilogy(freq[:50], spectrum[:50], color="oc.red5", lw=dm.lw(1))
ax2.set_xlabel("Frequency [Hz]", fontsize=dm.fs(0))
ax2.set_ylabel("Magnitude", fontsize=dm.fs(0))

# 5. Add panel labels and optimize layout
dm.label_axes([ax1, ax2])
dm.simple_layout(fig, gs=gs)

# 6. Export for submission
dm.save_formats(fig, "fig_signal_analysis",
                formats=("pdf", "svg", "png"), dpi=300, validate=True)
```

**Key points:**
- `dm.cm2in(17)` converts cm to inches for `figsize` -- journals often specify dimensions in cm
- `dm.fs(0)` uses the preset's base font size; `dm.lw(1)` uses relative line width
- `dm.label_axes()` adds (a), (b) labels aligned to y-axis labels
- `validate=True` catches clipped labels before you submit

---

(korean-operations-report)=
## Korean Operations Report (report-kr preset)

A weekly operations chart with Korean labels — bar series for a
primary count, line series for a secondary percentage on a twin axis:

```python
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import dartwork_mpl as dm
import numpy as np

# 1. Korean report style
dm.style.use("report-kr")

# 2. Create figure
fig, ax = plt.subplots(figsize=(dm.cm2in(15), dm.cm2in(9)), dpi=200)

# 3. Weekly data (synthetic)
weeks = ["1주차", "2주차", "3주차", "4주차", "5주차"]
throughput = [1234, 1456, 1389, 1567, 1650]   # primary: 처리량 (건)
utilization = [82.5, 84.2, 83.1, 85.8, 86.3]  # secondary: 가동률 (%)

# 4. Bar chart for the primary series
bars = ax.bar(weeks, throughput, color="oc.blue4", width=0.6, zorder=2)
ax.set_ylabel("처리량 (건)", fontsize=dm.fs(0))
ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))

# 5. Line chart for the secondary series on a twin axis
ax2 = ax.twinx()
ax2.plot(weeks, utilization, color="oc.red5", marker="o",
         markersize=4, lw=dm.lw(1.5), zorder=3)
ax2.set_ylabel("가동률 (%)", fontsize=dm.fs(0))
ax2.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=1))
ax2.spines["right"].set_visible(True)

# 6. Add value labels on bars
for bar, val in zip(bars, throughput):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 20,
            f"{val:,}", ha="center", va="bottom", fontsize=dm.fs(-1.5))

# 7. Layout and save
dm.auto_layout(fig)
dm.save_formats(fig, "korean_report",
                formats=("png", "pdf"), dpi=200)
```

**Key points:**
- `report-kr` preset loads Paperlogy/Pretendard for Korean text
- `ax2.spines["right"].set_visible(True)` -- show right spine for dual-axis charts
- `PercentFormatter(decimals=1)` -- clean percentage display
- `auto_layout` handles the dual y-axis label overflow automatically

---

(dark-mode-notebook)=
## Dark Mode Notebook

Set up a Jupyter workflow optimized for dark themes:

```python
# Cell 1: Setup
%config InlineBackend.figure_format = 'retina'

import matplotlib.pyplot as plt
import dartwork_mpl as dm
import numpy as np

dm.style.use("dark")
```

```python
# Cell 2: Create and preview
fig, ax = plt.subplots(figsize=(dm.cm2in(14), dm.cm2in(8)), dpi=150)

x = np.linspace(0, 4 * np.pi, 300)
for i, (amp, phase) in enumerate([(1.0, 0), (0.7, 0.5), (0.4, 1.0)]):
    y = amp * np.sin(x + phase)
    ax.plot(x, y, color=f"oc.blue{3 + i*2}", lw=dm.lw(1),
            label=f"A={amp}, phase={phase:.1f}")

ax.set_xlabel("Phase [rad]")
ax.set_ylabel("Amplitude")
ax.legend(fontsize=dm.fs(-1))

dm.simple_layout(fig)
dm.save_and_show(fig, size=720)  # Preview at 720px width
```

```python
# Cell 3: Export light version for paper
dm.style.use("scientific")  # Switch to light style
fig2, ax2 = plt.subplots(figsize=(dm.cm2in(9), dm.cm2in(6)), dpi=300)

# Replot with same data but paper-appropriate styling
for i, (amp, phase) in enumerate([(1.0, 0), (0.7, 0.5), (0.4, 1.0)]):
    y = amp * np.sin(x + phase)
    ax2.plot(x, y, color=f"oc.blue{3 + i*2}", lw=dm.lw(1),
             label=f"A={amp}, phase={phase:.1f}")

ax2.set_xlabel("Phase [rad]")
ax2.set_ylabel("Amplitude")
ax2.legend(fontsize=dm.fs(-1))

dm.simple_layout(fig2)
dm.save_formats(fig2, "waves", formats=("svg", "pdf"), dpi=300)
```

**Key points:**
- `retina` format makes inline plots crisp on HiDPI displays
- `save_and_show(fig, size=720)` previews at a specific pixel width
- Switch styles mid-notebook to export different versions from the same data
- Dark preset uses `#1e1e1e` background with subtle gray spines

---

## See also

- [Quick Start](quickstart.md) -- minimal 5-minute introduction
- [Styles and Presets](styles.md) -- full preset comparison
- [Colors and Colormaps](colors.md) -- palette reference
- [Layout and Typography](layout.md) -- margin optimization details
