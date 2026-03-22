"""MCP Resources for dartwork-mpl guides.

This module defines resources that expose dartwork-mpl usage guides,
color palettes, fonts, styles, and plot templates
through the Model Context Protocol.
"""

import json
from pathlib import Path

import matplotlib.colors as mcolors
from fastmcp import FastMCP
from matplotlib import font_manager

from ..util import get_prompt

__all__ = ["register_resources"]

# Path to bundled mplstyle files
_MPLSTYLE_DIR = Path(__file__).parent.parent / "asset" / "mplstyle"


def register_resources(mcp: FastMCP) -> None:
    """
    Register all resources with the MCP server.

    Parameters
    ----------
    mcp : FastMCP
        The FastMCP server instance to register resources with.
    """

    # ── Guide Resources ──────────────────────────────────────────────

    @mcp.resource("dartwork-mpl://guide/general-guide")
    def general_guide() -> str:
        """Get the general usage guide for dartwork-mpl."""
        return get_prompt("general-guide")

    @mcp.resource("dartwork-mpl://guide/layout-guide")
    def layout_guide() -> str:
        """Get the layout guide for dartwork-mpl."""
        return get_prompt("layout-guide")

    # ── Palette Resources ────────────────────────────────────────────

    @mcp.resource("dartwork-mpl://palette/colors")
    def palette_colors() -> str:
        """Get the full list of dartwork-mpl registered colors with hex codes.

        Returns a JSON object where keys are color names (e.g. 'dc.blue500')
        and values are hex codes. Only dartwork-mpl prefixed colors are included:
        dc.*, tw.*, md.*, ad.*, cu.*, pr.*, oc.*
        """
        colors = {
            k: mcolors.to_hex(v)
            for k, v in mcolors.get_named_colors_mapping().items()
            if any(k.startswith(prefix) for prefix in ["dc.", "tw.", "md.", "ad.", "cu.", "pr.", "oc."])
        }
        return json.dumps(colors, indent=2)

    @mcp.resource("dartwork-mpl://palette/fonts")
    def palette_fonts() -> str:
        """Get a sorted list of all fonts available to matplotlib."""
        fonts = sorted({f.name for f in font_manager.fontManager.ttflist})
        return json.dumps(fonts, indent=2)

    # ── Style Preset Resources ───────────────────────────────────────

    @mcp.resource("dartwork-mpl://styles/list")
    def styles_list() -> str:
        """List all available dartwork-mpl mplstyle presets.

        Returns a JSON array of preset names (without .mplstyle extension)
        that can be queried individually via dartwork-mpl://styles/{preset}.
        """
        if not _MPLSTYLE_DIR.exists():
            return json.dumps([])
        presets = sorted([p.stem for p in _MPLSTYLE_DIR.glob("*.mplstyle")])
        return json.dumps(presets, indent=2)

    @mcp.resource("dartwork-mpl://styles/{preset}")
    def style_preset(preset: str) -> str:
        """Get the content of a specific dartwork-mpl mplstyle preset.

        Parameters
        ----------
        preset : str
            Name of the style preset (e.g. 'dmpl', 'font-scientific',
            'theme-dark', 'lang-kr', 'spine-no').

        Available presets: base, dmpl, dmpl_light, font-minimal,
        font-poster, font-presentation, font-report, font-scientific,
        font-web, lang-kr, spine-no, spine-yes, theme-dark, theme-minimal.
        """
        style_file = _MPLSTYLE_DIR / f"{preset}.mplstyle"
        if not style_file.exists():
            available = sorted([p.stem for p in _MPLSTYLE_DIR.glob("*.mplstyle")])
            return f"Style preset '{preset}' not found. Available presets: {available}"
        return style_file.read_text(encoding="utf-8")

    # ── Plot Template Resources ──────────────────────────────────────

    @mcp.resource("dartwork-mpl://templates/list")
    def templates_list() -> str:
        """List all available plot template types."""
        return json.dumps(list(_TEMPLATES.keys()), indent=2)

    @mcp.resource("dartwork-mpl://templates/{plot_type}")
    def plot_templates(plot_type: str) -> str:
        """Get a boilerplate python script for a specific plot type.

        Available types: tornado, scatter, bar, heatmap, line, violin,
        stacked_bar, boxplot, pie, histogram, contour, twin_axis.
        """
        template = _TEMPLATES.get(plot_type.lower())
        if template is None:
            return f"No template for '{plot_type}'. Available: {list(_TEMPLATES.keys())}"
        return template


# ── Template Definitions ─────────────────────────────────────────────

_TEMPLATES = {
    "tornado": """\
import matplotlib.pyplot as plt
import dartwork_mpl as dm
import numpy as np

# --- Data ---
categories = ["Cat A", "Cat B", "Cat C", "Cat D"]
positive = [10, 25, 15, 30]
negative = [-8, -20, -12, -28]

# --- Plot ---
fig, ax = dm.subplots()
y_pos = np.arange(len(categories))

ax.barh(y_pos, positive, color="dc.blue500", label="Positive")
ax.barh(y_pos, negative, color="dc.red500", label="Negative")
ax.set_yticks(y_pos)
ax.set_yticklabels(categories)
ax.axvline(0, color="black", linewidth=0.5)
ax.set_xlabel("Value")
ax.legend()
plt.show()
""",
    "scatter": """\
import matplotlib.pyplot as plt
import dartwork_mpl as dm
import numpy as np

# --- Data ---
np.random.seed(42)
x = np.random.randn(50)
y = 2 * x + np.random.randn(50) * 0.5

# --- Plot ---
fig, ax = dm.subplots()
ax.scatter(x, y, color="dc.blue500", edgecolors="white", linewidth=0.3, s=20)
ax.set_xlabel("X axis")
ax.set_ylabel("Y axis")
plt.show()
""",
    "bar": """\
import matplotlib.pyplot as plt
import dartwork_mpl as dm

# --- Data ---
categories = ["A", "B", "C", "D", "E"]
values = [23, 45, 56, 78, 33]

# --- Plot ---
fig, ax = dm.subplots()
ax.bar(categories, values, color="dc.blue500", edgecolor="white", linewidth=0.3)
ax.set_ylabel("Value")
plt.show()
""",
    "heatmap": """\
import matplotlib.pyplot as plt
import dartwork_mpl as dm
import numpy as np

# --- Data ---
np.random.seed(42)
data = np.random.rand(8, 8)

# --- Plot ---
fig, ax = dm.subplots()
im = ax.imshow(data, cmap="viridis", aspect="auto")
plt.colorbar(im, ax=ax)
ax.set_xlabel("Column")
ax.set_ylabel("Row")
plt.show()
""",
    "line": """\
import matplotlib.pyplot as plt
import dartwork_mpl as dm
import numpy as np

# --- Data ---
x = np.linspace(0, 10, 100)
y1 = np.sin(x)
y2 = np.cos(x)

# --- Plot ---
fig, ax = dm.subplots()
ax.plot(x, y1, label="sin(x)")
ax.plot(x, y2, label="cos(x)")
ax.set_xlabel("x")
ax.set_ylabel("y")
ax.legend()
plt.show()
""",
    "violin": """\
import matplotlib.pyplot as plt
import dartwork_mpl as dm
import numpy as np

# --- Data ---
np.random.seed(42)
data = [np.random.normal(loc, 1, 100) for loc in [0, 2, 4]]

# --- Plot ---
fig, ax = dm.subplots()
parts = ax.violinplot(data, showmeans=True, showmedians=True)
ax.set_xticks([1, 2, 3])
ax.set_xticklabels(["Group A", "Group B", "Group C"])
ax.set_ylabel("Value")
plt.show()
""",
    "stacked_bar": """\
import matplotlib.pyplot as plt
import dartwork_mpl as dm
import numpy as np

# --- Data ---
categories = ["Q1", "Q2", "Q3", "Q4"]
series_a = [20, 35, 30, 35]
series_b = [25, 32, 34, 20]
series_c = [15, 18, 22, 28]

# --- Plot ---
fig, ax = dm.subplots()
x = np.arange(len(categories))
ax.bar(x, series_a, label="Series A", color="dc.blue500")
ax.bar(x, series_b, bottom=series_a, label="Series B", color="dc.green500")
bottom_c = [a + b for a, b in zip(series_a, series_b)]
ax.bar(x, series_c, bottom=bottom_c, label="Series C", color="dc.orange500")
ax.set_xticks(x)
ax.set_xticklabels(categories)
ax.set_ylabel("Value")
ax.legend()
plt.show()
""",
    "boxplot": """\
import matplotlib.pyplot as plt
import dartwork_mpl as dm
import numpy as np

# --- Data ---
np.random.seed(42)
data = [np.random.normal(0, std, 100) for std in [1, 2, 3, 4]]

# --- Plot ---
fig, ax = dm.subplots()
bp = ax.boxplot(data, patch_artist=True)
for patch, color in zip(bp["boxes"], ["dc.blue500", "dc.green500", "dc.orange500", "dc.red500"]):
    patch.set_facecolor(color)
ax.set_xticklabels(["σ=1", "σ=2", "σ=3", "σ=4"])
ax.set_ylabel("Value")
plt.show()
""",
    "pie": """\
import matplotlib.pyplot as plt
import dartwork_mpl as dm

# --- Data ---
labels = ["A", "B", "C", "D"]
sizes = [35, 25, 25, 15]
colors = ["dc.blue500", "dc.green500", "dc.orange500", "dc.red500"]

# --- Plot ---
fig, ax = dm.subplots()
ax.pie(sizes, labels=labels, colors=colors, autopct="%1.1f%%", startangle=90)
ax.set_aspect("equal")
plt.show()
""",
    "histogram": """\
import matplotlib.pyplot as plt
import dartwork_mpl as dm
import numpy as np

# --- Data ---
np.random.seed(42)
data = np.random.randn(1000)

# --- Plot ---
fig, ax = dm.subplots()
ax.hist(data, bins=30, color="dc.blue500", edgecolor="white", linewidth=0.3)
ax.set_xlabel("Value")
ax.set_ylabel("Frequency")
plt.show()
""",
    "contour": """\
import matplotlib.pyplot as plt
import dartwork_mpl as dm
import numpy as np

# --- Data ---
x = np.linspace(-3, 3, 100)
y = np.linspace(-3, 3, 100)
X, Y = np.meshgrid(x, y)
Z = np.sin(X) * np.cos(Y)

# --- Plot ---
fig, ax = dm.subplots()
cs = ax.contourf(X, Y, Z, levels=20, cmap="viridis")
plt.colorbar(cs, ax=ax)
ax.set_xlabel("x")
ax.set_ylabel("y")
plt.show()
""",
    "twin_axis": """\
import matplotlib.pyplot as plt
import dartwork_mpl as dm
import numpy as np

# --- Data ---
x = np.arange(1, 13)
temp = [5, 7, 12, 18, 23, 27, 30, 29, 24, 18, 11, 6]
precip = [50, 40, 45, 55, 70, 80, 90, 85, 65, 60, 55, 50]

# --- Plot ---
fig, ax1 = dm.subplots()
ax2 = ax1.twinx()

ax1.bar(x, precip, color="dc.blue300", alpha=0.7, label="Precipitation")
ax2.plot(x, temp, color="dc.red500", marker="o", markersize=3, label="Temperature")

ax1.set_xlabel("Month")
ax1.set_ylabel("Precipitation (mm)")
ax2.set_ylabel("Temperature (°C)")

lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")
plt.show()
""",
}
