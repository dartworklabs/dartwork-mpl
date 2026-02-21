# Dartwork UI Viewer

Interactive matplotlib figure viewer powered by [dartwork-mpl](https://github.com/dartworklabs/dartwork-mpl).

---

## Prerequisites

You need **Python 3.10+** and **uv** (or pip) installed.

Install the `dartwork-mpl` package with the `ui` extra:

```bash
uv pip install "dartwork-mpl[ui]"
```

Or if you're working inside the dartwork-mpl repository:

```bash
uv sync --extra ui
```

---

## Quick Start

### 1. Run the viewer

```bash
uv run --extra ui python app.py
```

You should see output like:

```
  Dartwork Viewer running at:
  http://127.0.0.1:8501
```

### 2. Open in your browser

Go to **http://127.0.0.1:8501** in any web browser.

If port 8501 is busy, the server will automatically try the next available port
(8502, 8503, ...).

---

## How It Works

### The `app.py` file has 3 parts:

#### 1. `Params` — Define your parameters

```python
class Params(ParamModel):
    frequency: float = Field(default=2.0, ge=0.1, le=20.0)
    show_grid: bool = Field(default=True)
    ...
```

Each field becomes a **UI control** in the sidebar:

| Python Type | UI Widget | Example |
|---|---|---|
| `int` with `ge`/`le` | Slider | `n_points: int = Field(ge=50, le=3000)` |
| `int` without bounds | Number input | `seed: int = Field(default=42)` |
| `float` with `ge`/`le` | Slider | `freq: float = Field(ge=0.1, le=20.0)` |
| `float` without bounds | Number input | `phase: float = Field(default=0.0)` |
| `str` | Text input | `title: str = Field(default="My Plot")` |
| `str` with `"color"` in name | Color picker | `bg_color: str = Field(default="#fff")` |
| `str` with widget hint | Color picker | `Field(json_schema_extra={"widget": "color"})` |
| `bool` | Checkbox | `show_grid: bool = Field(default=True)` |
| `Literal["a", "b"]` | Dropdown | `style: Literal["solid", "dashed"]` |
| `list[float]` | Text (comma-sep) | `ticks: list[float] = Field(default=[])` |
| `list[int]` | Text (comma-sep) | `indices: list[int] = Field(default=[])` |
| `list[str]` | Text (comma-sep) | `labels: list[str] = Field(default=[])` |
| `tuple[float, ...]` | Text (comma-sep) | `range: tuple[float, ...] = Field(default=())` |

#### 2. `my_figure(p: Params) -> Figure` — Draw your figure

This function receives a `Params` instance with the current parameter values.
It must return a `matplotlib.figure.Figure`.

```python
def my_figure(p: Params) -> Figure:
    fig, ax = plt.subplots()
    ax.plot(x, y, color=p.line_color)
    return fig
```

#### 3. `run(my_figure)` — Start the viewer

```python
if __name__ == "__main__":
    run(my_figure, title="My Viewer")
```

---

## UI Features

### Toolbar (top bar, left to right)

| Button | What it does |
|---|---|
| **Auto** checkbox | When checked, figure re-renders automatically as you change parameters |
| **Redraw** | Manually re-render the figure (also: `Cmd+Enter` / `Ctrl+Enter`) |
| **Save** | Save current parameter values as a named preset |
| **Load** | Load a previously saved preset |
| **Width slider** | Adjust figure display width (30% — 100%) |
| **BG** color picker | Change the figure container background color |
| **Format dropdown** | Choose export format (PNG, SVG, PDF) |
| **Download** (arrow down) | Download image to your browser |
| **Save to server** (hard drive) | Save image file next to your `app.py` |
| **Script** | Download a standalone Python script with current parameters |
| **Save script** (hard drive) | Save the script next to your `app.py` |
| **Reload** (rotate) | Restart the server to pick up code changes |

### Tabs

Click **+** to add a new tab. Each tab keeps its own set of parameter values,
so you can compare different configurations side by side.

### Presets

- Click **Save** to name and store the current parameter values.
- Click **Load** to restore a previously saved preset.
- Presets are stored in `.dartwork_ui_history.jsonl` next to your script.

---

## Modifying Your Figure

1. Edit `app.py` — change the `Params` class or `my_figure` function.
2. Click the **Reload** button in the toolbar (or restart the server).
3. Your changes are live immediately.

---

## Generated Files

When you save/export from the UI, files appear next to `app.py`:

| File | Description |
|---|---|
| `my_figure_YYYYMMDD_HHMMSS.png` | Exported image |
| `my_figure_YYYYMMDD_HHMMSS.py` | Standalone reproduction script |
| `.dartwork_ui_config.json` | Last-used parameter values (auto-saved) |
| `.dartwork_ui_history.jsonl` | History of all parameter sets & presets |

The `.gitignore` in this folder excludes all generated files by default.

---

## Tips

- **Slider step size**: Use `json_schema_extra={"step": 0.1}` to control the
  slider increment.
- **Field labels**: Use `description="..."` in `Field()` to set the label shown
  in the sidebar. Without it, the field name is converted from `snake_case` to
  `Title Case`.
- **Color auto-detection**: Any `str` field with `"color"` in its name
  automatically gets a color picker widget.
- **Remote usage**: If running on a remote server, use the "Save to server"
  buttons to save files directly on the server instead of downloading to your
  browser.
