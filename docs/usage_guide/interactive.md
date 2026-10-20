# Interactive UI

dartwork-mpl ships an optional in-browser viewer (FastAPI + Pydantic)
for tweaking plot parameters with sliders, downloading the result,
and — most importantly — exporting the **exact Python script** that
reproduces what you see. It's the fastest way to figure out the
parameters you actually want before locking them into code.

## See it in action

The slider below is the **real viewer**, captured at two moments:
on the left, the default state right after `python viewer.py` boots;
on the right, the same UI after a handful of slider/dropdown/color-picker
tweaks. Drag the handle to wipe between them and watch the chart
respond — every control on the left panel is auto-generated from a
Pydantic `ParamModel` and re-renders the matplotlib figure on the
right in ≈80 ms.

```{raw} html
:file: ../_static/interactive_slider.html
```

```{admonition} What the UI gives you
:class: tip

A split-pane web app served on a local port (default `8501`):

- **Left panel** — auto-generated controls (sliders, text inputs,
  toggles, dropdowns) derived from your `ParamModel` fields.
- **Right panel** — live matplotlib figure that re-renders on every
  change, in any dartwork-mpl style preset.
- **Bottom bar** — Download (PNG / SVG / PDF), Save-to-Server (with
  optional mirror copies), and **Download Script** for one-click
  reproducible export.
```

```{admonition} Install the optional extra
:class: note

The interactive UI is gated behind the `ui` extra:

    pip install "dartwork-mpl[ui]"
    uv add "dartwork-mpl[ui]"
```

## 30-second tour

```bash
# 1. scaffold a starter viewer
dartwork-mpl-ui init ./my-viewer --example simple

# 2. run it
cd my-viewer
python viewer.py
# → opens the viewer in your default browser (local server, default port 8501)
```

Adjust the sliders. When the figure looks right, click
**Download Script** at the bottom — you get a standalone `.py` file
that reproduces the figure with no UI dependency.

## Building your own viewer

A viewer is two things: a Pydantic `ParamModel` describing what the
user can tweak, and a function that turns those parameters into a
matplotlib `Figure`.

<!-- snippet: no-run -->
```python
import matplotlib.pyplot as plt
import numpy as np
import dartwork_mpl as dm
from dartwork_mpl.ui import ParamModel, run
from pydantic import Field


class ScatterParams(ParamModel):
    n: int = Field(default=100, ge=10, le=1000, description="Number of points")
    alpha: float = Field(default=0.5, ge=0.0, le=1.0, description="Transparency")
    color: str = Field(default="dc.teal2", description="Point color")


def plot_scatter(params: ScatterParams):
    dm.style.use("scientific")
    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))

    x = np.random.randn(params.n)
    y = np.random.randn(params.n)
    ax.scatter(x, y, alpha=params.alpha, color=params.color)

    dm.simple_layout(fig)
    return fig


if __name__ == "__main__":
    # Starts a local web server (default port 8501) and opens it
    run(plot_scatter)
```

That's it. The UI introspects `ScatterParams`, generates the right
control for each field, and starts re-rendering on every change.

## What field type maps to which control?

| Pydantic field                                  | Auto-generated control      | Tip                                          |
| ----------------------------------------------- | --------------------------- | -------------------------------------------- |
| `int = Field(ge=…, le=…)`                       | Integer slider              | Always set both bounds for sliders           |
| `float = Field(ge=…, le=…)`                     | Float slider                | Add `multiple_of=` for snap-to steps         |
| `int` / `float` (no bounds)                     | Number text input           | Free-form numeric entry                      |
| `bool`                                          | Toggle switch               | —                                            |
| `Literal["a", "b", "c"]`                        | Dropdown                    | Cleanest way to expose presets / colors      |
| `str`                                           | Text input                  | Use `Literal[…]` instead when values are fixed |
| `list[float]` with `min_length` / `max_length`  | Repeated number inputs      | Good for piecewise breakpoints               |

<!-- snippet: no-run -->
```python
from typing import Literal
from pydantic import Field

class FontParams(ParamModel):
    preset: Literal[
        "scientific", "report", "presentation", "poster",
    ] = Field(default="scientific")
    fs_offset: int = Field(default=0, ge=-3, le=4, description="dm.fs offset")
    bold_title: bool = Field(default=False)
```

Wire that to a render function and you've built a one-page font /
preset comparator.

## Common patterns

### Browse a parameter sweep

Set wide bounds and step through them with the keyboard arrow keys
once focus is on a slider:

<!-- snippet: no-run -->
```python
class SweepParams(ParamModel):
    sigma: float = Field(default=1.0, ge=0.1, le=5.0)
    samples: int = Field(default=500, ge=50, le=5000)
```

### Compare style presets live

<!-- snippet: no-run -->
```python
from typing import Literal

class PresetParams(ParamModel):
    preset: Literal[
        "scientific", "report", "presentation", "poster", "web", "minimal", "dark",
    ] = Field(default="scientific")

def plot_preset(params: PresetParams):
    dm.style.use(params.preset)
    fig, ax = plt.subplots(figsize=dm.figsize("15cm", "wide"))
    ...
    return fig
```

### Mirror exports to your paper / report directory

<!-- snippet: no-run -->
```python
run(
    plot_scatter,
    copy_to=["~/Papers/2026-acl/figures/", "../report/figures/"],
)
```

Each image **Save to Server** creates a new file in the script directory
and each `copy_to` directory. Choose a new filename on every save, such as
`scatter-v2.png`: copies use the same create-only rule, so a collision at
any destination returns **409 — file exists; choose a new name**. This
does not repeatedly overwrite a manuscript figure. Script saves stay in
the script directory.

`copy_to` accepts a single string or `os.PathLike`, a list of either, or
`None`. `~` expands, relative roots use the working directory at startup,
and paths referring to the same directory are deduplicated. Output names
may include safe relative subdirectories. Absolute paths, traversal,
symlinks and non-directory parents are refused. No overwrite control is
provided; automatic names also use exclusive creation.

## Local access and recovery

The viewer accepts loopback IP binds (`127.0.0.0/8`, `::1`) and maps
`localhost` directly to `127.0.0.1`. The default stays `127.0.0.1:8501`.
Other hostnames, wildcard and non-loopback binds are rejected before
startup or writes. Host is checked on every route; each supplied Origin
and Referer must match it for effects, including rendering and reload.
Forwarded headers grant no access. Hosted use and reverse proxies are
outside this local development contract. Loopback establishes network
locality, not a person's identity; local processes and callbacks are trusted.

The viewer saves configuration and presets in `.dartwork_ui_config.json`
and `.dartwork_ui_presets.json` beside the script. Invalid or oversized
existing files return **409** with code `invalid_stored_state`; their bytes
are preserved and updates/deletes are refused. The UI reports the error
and keeps default controls and **Reset** available. Reset restores active
parameter defaults; it does not repair or delete a stored file. Repeated
auto-save failures with the same 409/501 code are notified once per page.
A rejected preset save never reports success, and a failed preset read
reports its error instead of an empty collection.

After a model changes, reads omit removed field names and report them as
`dropped_fields` in config and each preset. Reading does not rewrite the
file. Other preset entries retain their JSON values when one is added or
deleted. A retained field with an obsolete type or range can still return
**422** when used; **Reset** restores current defaults.

Safe filesystem operations require no-follow opens and directory-handle
primitives. If they are unavailable, affected state/save operations return
**501** while rendering and downloads remain usable. The package's general
OS-independent support does not imply these capabilities on every OS.

Image copies use best-effort rollback across destinations. This is not a
cross-root transaction: readers may see provisional files, and a crash or
failed cleanup may leave new files. A partial-save **503** reports affected
relative paths; retry with a new name. Directory handles prevent path
redirection, but do not promise protection against a malicious same-owner
process moving authorized directories or racing cleanup. State updates use
atomic replacement and serialize within one process; separate viewer
processes sharing a directory can lose updates (last replacement wins).

Callbacks run serially as trusted arbitrary Python. There is no hard CPU,
memory or execution deadline guarantee and no hostile-code sandbox.

### Input limits and API errors

JSON-bearing requests require `application/json`, an absent or UTF-8
charset, and no Content-Encoding. Active parameters accept only declared
field names, including nested model fields; explicitly open dictionaries
remain open within the limits. Limits include UTF-8 bytes:

| Input | Limit |
| --- | --- |
| Request body / config file | 1 MiB each |
| Preset file | 8 MiB |
| JSON depth / total values / entries per container | 16 / 65,536 / 4,096 |
| String / integer token | 64 KiB / 640 digits |
| Tabs / presets | 64 / 1,000 |
| Preset or tab label | 256 bytes |
| Relative output path | 1,024 bytes plus platform component limits |
| Active figure width | Integer 30..100; invalid stored widths use the UI default |

Errors include human-readable `detail` and a stable `code`:

| Status | Meaning |
| --- | --- |
| 400 | Malformed, duplicate-key or non-finite JSON; unsafe path |
| 403 | Local access policy or unclassified effect refusal |
| 404 | Missing preset or route |
| 409 | Existing output, changed root/target, or invalid stored state |
| 413 | Request or next serialized state exceeds a limit |
| 415 | Unsupported media type, charset or content encoding |
| 422 | Invalid schema, unknown field or invalid active value |
| 500 | Trusted callback failed (`callback_failed`); no traceback details |
| 501 | Safe filesystem primitives unavailable (`unsupported_filesystem_capability`) |
| 503 | Filesystem I/O or partial-save failure |

## Reproducible code export

When you click **Download Script**, the viewer generates a
self-contained `.py` file capturing:

1. Your exact `ParamModel` and render function.
2. The current parameter values from the UI.
3. The minimal boilerplate to recreate the figure with no UI
   dependency.

<!-- snippet: no-run -->
```python
# Auto-generated by dartwork-mpl Interactive UI
# Parameters captured at 2026-04-25 14:30:22

from scatter_viewer import ScatterParams, plot_scatter
import dartwork_mpl as dm

params = ScatterParams(n=250, alpha=0.35, color="dc.green2")
fig = plot_scatter(params)
dm.save_formats(fig, "scatter_final", formats=("png", "svg"), dpi=300)
```

This is the whole reason the UI exists: tune by feel, lock the
result into version control, and never ship "I forgot which
parameters made this plot" again.

```{tip}
The viewer respects whatever `dm.style.use(...)` you call inside the
render function — including `dark`, `report-kr`, and stacked styles
like `["scientific", "font-libertine"]`.
```

## See also

- [API › Interactive Viewer](../api/ui.rst) for all `run()`,
  `ParamModel`, and CLI arguments.
- [Save and Validation](save_export.md) for batch export without the
  interactive UI.
- [Design Philosophy](../philosophy/index) for the "Utilities, Not
  Wrappers" approach behind the UI.
