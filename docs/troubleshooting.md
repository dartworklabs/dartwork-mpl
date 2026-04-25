# Troubleshooting & FAQ

Common issues and their solutions when working with dartwork-mpl.

## Installation

### `ModuleNotFoundError: No module named 'dartwork_mpl'`

Make sure dartwork-mpl is installed in your **active** Python environment:

```bash
# Check which Python is active
which python

# Install in the correct environment
pip install git+https://github.com/dartworklabs/dartwork-mpl
```

If using virtual environments or conda, activate the environment first.

### `git` not found during installation

dartwork-mpl is installed from GitHub, so Git must be available:

```bash
# macOS
brew install git

# Ubuntu/Debian
sudo apt install git

# Windows
# Download from https://git-scm.com/downloads
```

---

## Fonts

### Korean text shows as empty boxes (tofu) or fallback font

The Korean font variants (`-kr`) require bundled fonts to be available. dartwork-mpl registers fonts automatically on import, but some environments need extra steps:

```python
import dartwork_mpl as dm

# Verify Korean fonts are registered
dm.style.use("report-kr")
print(dm.font.list_registered())  # Check for 'Paperlogy', 'Pretendard'
```

**Common fixes:**

1. **Restart your kernel** — matplotlib caches fonts at startup
2. **Clear matplotlib font cache:**
   ```python
   import matplotlib
   import shutil
   cache_dir = matplotlib.get_cachedir()
   shutil.rmtree(cache_dir)
   # Restart Python after this
   ```
3. **Verify font files exist:**
   ```python
   import dartwork_mpl as dm
   print(dm.font.get_font_dir())  # Should contain .ttf/.otf files
   ```

### Font sizes look different across presets

This is expected behavior. Each preset defines its own font size scale optimized for its target medium:

| Preset | Base font size | Target |
|--------|---------------|--------|
| `scientific` | 7.5 pt | Journal figures at 3.5" width |
| `report` | 8.0 pt | PDF reports |
| `presentation` | 10.5 pt | Projected slides |
| `poster` | 12.0 pt | Conference posters (1-2m viewing) |

Use `dm.fs(n)` for relative sizing that scales correctly with any preset.

---

## Layout

### `simple_layout` doesn't seem to change anything

`simple_layout` optimizes **outer margins** (left, right, top, bottom). If your issue is **inner spacing** between subplots, use GridSpec parameters:

```python
fig = plt.figure()
gs = fig.add_gridspec(2, 2, hspace=0.35, wspace=0.25)  # inner spacing
axes = [fig.add_subplot(gs[i, j]) for i in range(2) for j in range(2)]

dm.simple_layout(fig, gs=gs)  # pass gs for correct margin calculation
```

### Labels or titles are clipped at figure edges

Switch from `simple_layout` to `auto_layout`, which detects and fixes overflow:

```python
# Instead of:
dm.simple_layout(fig)

# Use:
dm.auto_layout(fig, verbose=True)  # verbose shows what it fixed
```

### `tight_layout()` warning when using `simple_layout`

If you see warnings about `tight_layout`, make sure you're **not** calling both:

```python
# Don't mix layout managers
fig.tight_layout()
dm.simple_layout(fig)

# Use only one
dm.simple_layout(fig)
```

---

## Colors

### Named color not recognized: `'oc.blue5' is not a valid color`

Named colors are registered when dartwork-mpl is imported. Make sure you import before using colors:

```python
import dartwork_mpl as dm  # This registers all named colors
import matplotlib.pyplot as plt

# Now named colors work
ax.plot(x, y, color="oc.blue5")
```

### Colors look different in saved files vs notebook

This is usually a DPI or colorspace issue:

```python
# Ensure consistent rendering
dm.save_formats(fig, "output", formats=("png",), dpi=300)

# For print: use PDF or SVG (vector, no DPI issues)
dm.save_formats(fig, "output", formats=("pdf", "svg"))
```

---

## Saving & Export

### SVG file is empty or very small

This usually happens when `plt.show()` is called before saving, which clears the figure:

```python
# Wrong order
plt.show()
dm.save_formats(fig, "output")  # Figure is already cleared!

# Correct order
dm.save_formats(fig, "output")  # Save first
plt.show()                       # Then display

# Or use the combined function
dm.save_and_show(fig)  # Handles ordering correctly
```

### Saved image has extra whitespace

Use `simple_layout` or `auto_layout` before saving:

```python
dm.simple_layout(fig)  # Optimize margins
dm.save_formats(fig, "output", formats=("png", "svg"), dpi=300)
```

Avoid passing `bbox_inches="tight"` with `simple_layout` — they can conflict. `simple_layout` already calculates optimal margins.

---

## Jupyter Notebooks

### Figures are too small / too large in notebook output

Control notebook display size with `save_and_show`:

```python
dm.save_and_show(fig, size=720)  # Display at 720px width
dm.save_and_show(fig, size=480)  # Smaller preview
```

### Inline plots look blurry

Set retina display support:

```python
%config InlineBackend.figure_format = 'retina'
# Or for SVG (always crisp):
%config InlineBackend.figure_format = 'svg'
```

### Style changes don't take effect

matplotlib caches style parameters. If you switch presets mid-notebook:

```python
# This may not fully reset
dm.style.use("dark")

# Force a clean slate by creating a new figure after style change
dm.style.use("dark")
fig, ax = plt.subplots()  # New figure picks up new style
```

---

## Interactive UI

### `ImportError` when using `dartwork_mpl.ui`

The interactive UI requires extra dependencies:

```bash
pip install "dartwork-mpl[ui]"
# or
uv add "dartwork-mpl[ui]"
```

### UI server doesn't start

Check that the port is not already in use:

```bash
# Default port is 8501
lsof -i :8501
```

If something else is bound to 8501, pass a different port directly to
`run(...)` inside your viewer script:

```python
from dartwork_mpl.ui import run

if __name__ == "__main__":
    run(plot_my_chart, port=8502)
```

---

## Still stuck?

1. Check the [Examples Gallery](examples_gallery/index) for working code patterns
2. Open an issue on [GitHub](https://github.com/dartworklabs/dartwork-mpl/issues)
3. Include your dartwork-mpl version: `python -c "import dartwork_mpl; print(dartwork_mpl.__version__)"`
