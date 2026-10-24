"""Mutation controls for the scorer: correct figures pass, corrupted ones fail.

Not collected by the default ``pytest`` run (``testpaths`` excludes evals/).
Run explicitly:  uv run pytest evals/agentic/test_scorer.py -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import metrics
import oracle
import probe
from oracle import num, table

COUNTRIES = ["Korea", "Japan", "United States", "Germany", "France"]
SERIES = {
    "type": "series",
    "file": "gdp_growth.csv",
    "x": {"col": "year", "kind": "num"},
    "identity": "named",
    "series": [{"y": c, "aliases": [c]} for c in COUNTRIES],
}
BARS = {
    "type": "bars",
    "file": "quarterly_sales.csv",
    "category": {"col": "quarter"},
    "series": {"col": "region"},
    "value": "revenue",
    "orientation": "v",
}
POINTS = {
    "type": "points",
    "file": "plants.csv",
    "x": "leaf_length_cm",
    "y": "leaf_width_cm",
    "by": {"col": "species"},
}
DIST = {
    "type": "dist",
    "file": "response_times.csv",
    "value": "response_ms",
    "by": {"col": "variant"},
    "accept": ["hist"],
}
STACK = {
    "type": "stack",
    "file": "energy_mix.csv",
    "x": {"col": "year", "kind": "num"},
    "layers": [
        {"y": k, "aliases": [k]}
        for k in ("coal", "gas", "nuclear", "hydro", "wind_solar")
    ],
}
MATRIX = {
    "type": "matrix",
    "file": "sensors.csv",
    "cell_text": False,
    "columns": [
        "temperature",
        "humidity",
        "pressure",
        "wind_speed",
        "pm25",
        "noise_db",
    ],
}


def run(fig, check: dict) -> bool:
    snap = probe.snapshot(fig, None)
    plt.close(fig)
    res = oracle.check_oracle(
        [check], {"snapshot": snap, "styles": [], "missing_glyphs": []}
    )
    return res[0]["ok"]


def col(file, name):
    return [num(r[name]) for r in table(file)]


def nan(v):
    return np.nan if v is None else v


# ------------------------------------------------------------ series
def gdp_fig(mutation=None):
    years = col("gdp_growth.csv", "year")
    fig, ax = plt.subplots()
    for c in COUNTRIES:
        x, y = list(years), [nan(v) for v in col("gdp_growth.csv", c)]
        label = c
        if mutation == "swap_labels" and c in ("Korea", "Japan"):
            label = "Japan" if c == "Korea" else "Korea"
        if mutation == "reorder" and c == "Korea":
            y = y[::-1]
        if mutation == "remove" and c == "Korea":
            x, y = x[1:], y[1:]
        if mutation == "drop_gap" and c == "Germany":
            keep = [i for i, v in enumerate(y) if not np.isnan(v)]
            x, y = [x[i] for i in keep], [y[i] for i in keep]
        if mutation == "duplicate" and c == "Korea":
            x, y = [*x, x[-1]], [*y, y[-1]]
        ax.plot(x, y, label=label)
    ax.legend()
    return fig


@pytest.mark.parametrize(
    "mutation, ok",
    [
        (None, True),
        ("swap_labels", False),
        ("reorder", False),
        ("remove", False),
        ("drop_gap", False),
        ("duplicate", False),
    ],
)
def test_series_contract(mutation, ok):
    assert run(gdp_fig(mutation), SERIES) is ok


# ------------------------------------------------------------ bars
def sales_fig(mutation=None):
    rows = table("quarterly_sales.csv")
    quarters = ["Q1", "Q2", "Q3", "Q4"]
    fig, ax = plt.subplots()
    for k, region in enumerate(["North", "South", "East", "West"]):
        vals = [
            num(r["revenue"])
            for q in quarters
            for r in rows
            if r["region"] == region and r["quarter"] == q
        ]
        x = np.arange(4) + (k - 1.5) * 0.2
        label = region
        if mutation == "swap_series" and region in ("North", "South"):
            label = "South" if region == "North" else "North"
        if mutation == "remove" and region == "West":
            x, vals = x[:3], vals[:3]
        if mutation == "duplicate" and region == "West":
            x, vals = np.append(x, x[-1] + 0.05), [*vals, vals[-1]]
        ax.bar(x, vals, width=0.2, label=label)
    labels = (
        ["Q2", "Q1", "Q3", "Q4"] if mutation == "swap_categories" else quarters
    )
    ax.set_xticks(range(4), labels)
    ax.legend()
    return fig


@pytest.mark.parametrize(
    "mutation, ok",
    [
        (None, True),
        ("swap_categories", False),
        ("swap_series", False),
        ("remove", False),
        ("duplicate", False),
    ],
)
def test_bars_contract(mutation, ok):
    assert run(sales_fig(mutation), BARS) is ok


# ------------------------------------------------------------ points
def plants_fig(mutation=None):
    rows = [
        r for r in table("plants.csv") if num(r["leaf_width_cm"]) is not None
    ]
    fig, ax = plt.subplots()
    for sp in ("Alpine", "Coastal", "Desert"):
        g = [r for r in rows if r["species"] == sp]
        x = [num(r["leaf_length_cm"]) for r in g]
        y = [num(r["leaf_width_cm"]) for r in g]
        label = sp
        if mutation == "swap_xy" and sp == "Alpine":
            x, y = y, x
        if mutation == "remove" and sp == "Alpine":
            x, y = x[1:], y[1:]
        if mutation == "duplicate" and sp == "Alpine":
            x, y = [*x, x[0]], [*y, y[0]]
        if mutation == "swap_labels" and sp in ("Alpine", "Desert"):
            label = "Desert" if sp == "Alpine" else "Alpine"
        ax.scatter(x, y, label=label)
    ax.legend()
    return fig


@pytest.mark.parametrize(
    "mutation, ok",
    [
        (None, True),
        ("swap_xy", False),
        ("remove", False),
        ("duplicate", False),
        ("swap_labels", False),
    ],
)
def test_points_contract(mutation, ok):
    assert run(plants_fig(mutation), POINTS) is ok


# ------------------------------------------------------------ histogram
def hist_fig(mutation=None):
    rows = table("response_times.csv")
    data = {
        v: [num(r["response_ms"]) for r in rows if r["variant"] == v]
        for v in ("A", "B")
    }
    if mutation == "remove":
        data["A"] = data["A"][1:]
    if mutation == "duplicate":
        data["A"] = [*data["A"], data["A"][0]]
    bins = np.linspace(50, 600, 31)
    fig, ax = plt.subplots()
    for v, vals in data.items():
        ax.hist(vals, bins=bins, label=f"Variant {v}", alpha=0.5)
    ax.legend()
    return fig


@pytest.mark.parametrize(
    "mutation, ok", [(None, True), ("remove", False), ("duplicate", False)]
)
def test_hist_contract(mutation, ok):
    assert run(hist_fig(mutation), DIST) is ok


# ------------------------------------------------------------ stack / matrix
def stack_fig(mutation=None):
    years = col("energy_mix.csv", "year")
    cols = ["coal", "gas", "nuclear", "hydro", "wind_solar"]
    labels = list(cols)
    if mutation == "swap_labels":
        labels[0], labels[1] = labels[1], labels[0]
    fig, ax = plt.subplots()
    ax.stackplot(
        years, *[col("energy_mix.csv", c) for c in cols], labels=labels
    )
    return fig


@pytest.mark.parametrize("mutation, ok", [(None, True), ("swap_labels", False)])
def test_stack_contract(mutation, ok):
    assert run(stack_fig(mutation), STACK) is ok


def matrix_fig(mutation=None):
    cols = MATRIX["columns"]
    data = np.asarray([[num(r[c]) for c in cols] for r in table("sensors.csv")])
    corr = np.corrcoef(data, rowvar=False)
    names = list(cols)
    if mutation == "swap_labels":
        names[0], names[1] = names[1], names[0]
    fig, ax = plt.subplots()
    ax.imshow(corr)
    ax.set_xticks(range(6), names)
    ax.set_yticks(range(6), names)
    return fig


@pytest.mark.parametrize("mutation, ok", [(None, True), ("swap_labels", False)])
def test_matrix_contract(mutation, ok):
    assert run(matrix_fig(mutation), MATRIX) is ok


# ------------------------------------------------------------ preservation
def test_explicit_preservation_flags_non_target_change():
    base = probe.snapshot(gdp_fig(), None)["props"]
    fig = gdp_fig()
    ax = fig.axes[0]
    ax.xaxis.label.set_fontsize(ax.xaxis.label.get_fontsize() + 1)  # target
    same = probe.snapshot(fig, None)["props"]
    ax.lines[0].set_linewidth(4)  # not a target
    changed = probe.snapshot(fig, None)["props"]
    plt.close("all")
    target = ["ax*.xlabel.fontsize"]
    assert metrics.preservation(base, same, "explicit", target)["ok"] is True
    res = metrics.preservation(base, changed, "explicit", target)
    # series properties are keyed by the data they draw; the one change is Korea's width
    (key,) = res["changed"]
    assert res["ok"] is False and key.endswith(".lw")
    assert base[key.removesuffix(".lw") + ".label"] == "Korea"
    assert metrics.preservation(base, changed, "broad", ["*"])["ok"] is None


# ------------------------------------------------------------ customization checks
def spec(fig, check: dict, save: dict | None = None) -> bool:
    """One spec check on a figure snapshot (``save`` stands in for the saved file)."""
    snap = probe.snapshot(fig, save)
    plt.close(fig)
    res = oracle.check_oracle(
        [check], {"snapshot": snap, "styles": [], "missing_glyphs": []}
    )
    return res[0]["ok"]


GRID_Y = {"type": "gridlines", "axis": "y"}


def grid_fig(mutation=None):
    fig = sales_fig()
    ax = fig.axes[0]
    fig.canvas.draw()
    ticks = [t for t in ax.get_yticks() if 0 < t < ax.get_ylim()[1]]
    if mutation == "grid_y":
        ax.grid(axis="y")
    if mutation == "grid_x":
        ax.grid(axis="x")
    if mutation == "grid_y_alpha0":
        ax.grid(axis="y", alpha=0)
    if mutation == "axhlines_at_ticks":
        for t in ticks:
            ax.axhline(t, color="0.85", linewidth=0.5, zorder=0)
    if mutation == "one_reference_line":
        ax.axhline(ticks[0], color="0.5", linewidth=0.5)
    if mutation == "hlines_at_ticks":
        ax.hlines(ticks, *ax.get_xlim(), color="0.85", linewidth=0.5)
    return fig


@pytest.mark.parametrize(
    "mutation, ok",
    [
        (None, False),
        ("grid_y", True),
        ("grid_x", False),
        ("grid_y_alpha0", False),
        ("axhlines_at_ticks", True),
        ("hlines_at_ticks", True),
        ("one_reference_line", False),
    ],
)
def test_gridlines_check(mutation, ok):
    assert spec(grid_fig(mutation), GRID_Y) is ok


def energy_fig(legend: str):
    fig, ax = plt.subplots()
    for c in STACK["layers"]:
        ax.plot(
            col("energy_mix.csv", "year"),
            col("energy_mix.csv", c["y"]),
            label=c["y"],
        )
    if legend == "top":
        ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), ncols=5)
    elif legend == "right":
        fig.subplots_adjust(right=0.7)  # room on the canvas, as a layout makes
        ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1))
    elif legend == "top_off_canvas":
        ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.3), ncols=5)
    else:
        ax.legend(loc="upper right")
    return fig


@pytest.mark.parametrize(
    "legend, side, ok",
    [
        ("top", "top", True),
        ("inside", "top", False),
        ("right", "top", False),
        ("top_off_canvas", "top", False),
        ("right", "right", True),  # e04's behaviour is unchanged
        ("top", "right", False),
        ("right", None, True),  # no side: right, as before
    ],
)
def test_legend_side(legend, side, ok):
    check = {"type": "legend", "outside": "right"}
    if side:
        check["side"] = side
    assert spec(energy_fig(legend), check) is ok


DARK = {"type": "dark_background", "max_luminance": 0.3}
WHITE_SAVE = {"facecolor": "#ffffff", "face_alpha": 1.0, "transparent": False}


@pytest.mark.parametrize(
    "fig_face, ax_face, save, ok",
    [
        ("#1e1e1e", "#1e1e1e", None, True),
        ("white", "white", None, False),
        ("#1e1e1e", "white", None, False),  # dark margins, white plot area
        ("white", "#1e1e1e", None, True),  # the plot area is dark
        ("#1e1e1e", "none", None, True),  # transparent axes over a dark canvas
        # a preset's savefig.facecolor (white) wins over fig.set_facecolor
        ("#1e1e1e", "none", WHITE_SAVE, False),
        ("#1e1e1e", "#1e1e1e", WHITE_SAVE, True),
        ("#1e1e1e", "#1e1e1e", {**WHITE_SAVE, "transparent": True}, False),
    ],
)
def test_dark_background_check(fig_face, ax_face, save, ok):
    fig = gdp_fig()
    fig.set_facecolor(fig_face)
    fig.axes[0].set_facecolor(ax_face)
    assert spec(fig, DARK, save) is ok


def test_dark_background_reads_the_saved_canvas(tmp_path):
    """End to end: the probe records savefig's facecolor, so a dark figure
    saved under a preset whose savefig.facecolor is white is not dark."""
    import score

    src = (
        "from pathlib import Path\n"
        "import matplotlib.pyplot as plt\n"
        "import dartwork_mpl as dm\n"
        "dm.style.use('report')\n"
        "fig, ax = plt.subplots(figsize=dm.figsize('10cm', 'golden'))\n"
        "ax.plot([1, 2, 3], [1, 3, 2])\n"
        "fig.set_facecolor('#111111')\n"
        "ax.set_facecolor('{ax}')\n"
        "Path('out').mkdir(exist_ok=True)\n"
        "dm.save_formats(fig, 'out/figure', formats=('png',))\n"
    )
    results = {}
    for ax_face in ("none", "#111111"):
        work = tmp_path / ax_face.strip("#")
        work.mkdir()
        (work / "plot.py").write_text(src.replace("{ax}", ax_face))
        pr = score.run_probe(score.REPO / ".venv" / "bin" / "python", work)
        assert pr["snapshot"]["save"]["facecolor"] == "#ffffff", pr.get("error")
        results[ax_face] = oracle.check_oracle([DARK], pr)[0]["ok"]
    assert results == {"none": False, "#111111": True}


TITLE = {"type": "title", "contains": "Real GDP growth by country"}


@pytest.mark.parametrize(
    "how, ok",
    [
        ("set_title", True),
        ("set_title_left", True),
        ("suptitle", True),
        ("figtext_above", True),
        ("text_inside_axes", False),
        ("other_title", False),
        ("none", False),
    ],
)
def test_title_check(how, ok):
    fig = gdp_fig()
    ax = fig.axes[0]
    t = TITLE["contains"]
    if how == "set_title":
        ax.set_title(t)
    if how == "set_title_left":
        ax.set_title(t, loc="left")
    if how == "suptitle":
        fig.suptitle(t)
    if how == "figtext_above":
        fig.text(0.02, 0.97, t, va="top")
    if how == "text_inside_axes":
        ax.text(0.5, 0.5, t, transform=ax.transAxes)
    if how == "other_title":
        ax.set_title("GDP growth")
    assert spec(fig, TITLE) is ok


NOTE = {"type": "text_below", "contains": "출처: 사내 웹 로그"}


@pytest.mark.filterwarnings("ignore:Glyph")  # Hangul in the default font
@pytest.mark.parametrize(
    "where, ok",
    [
        ("figtext_bottom", True),
        ("annotation_below", True),
        ("inside_axes", False),
        ("top", False),
        ("off_canvas", False),
        ("other_text", False),
    ],
)
def test_text_below_check(where, ok):
    fig = gdp_fig()
    fig.subplots_adjust(bottom=0.25)
    ax = fig.axes[0]
    note = NOTE["contains"]
    if where == "figtext_bottom":
        fig.text(0.01, 0.01, note)
    if where == "annotation_below":
        ax.annotate(note, (0, -0.25), xycoords="axes fraction", va="top")
    if where == "inside_axes":
        ax.text(0.05, 0.05, note, transform=ax.transAxes)
    if where == "top":
        fig.text(0.01, 0.95, note)
    if where == "off_canvas":
        fig.text(0.01, -0.1, note)
    if where == "other_text":
        fig.text(0.01, 0.01, "Source: internal web logs")
    assert spec(fig, NOTE) is ok


# ------------------------------------------------------------ customization props
def test_new_props_record_titles_grid_facecolor_and_legend():
    fig = gdp_fig()
    ax = fig.axes[0]
    ax.set_title("Left", loc="left", fontweight="bold")
    fig.suptitle("Figure title")
    ax.grid(axis="y", color="#cccccc", linewidth=0.4, linestyle="--")
    fig.text(0.01, 0.01, "note", color="#ff0000")
    p = probe.snapshot(fig, None)
    plt.close(fig)
    props, texts = p["props"], p["texts"]
    assert props["ax0.title.left.text"] == "Left"
    assert props["ax0.title.left.fontweight"] == "bold"
    assert "ax0.title.center.text" not in props  # empty slots are skipped
    assert props["figure.suptitle.text"] == "Figure title"
    assert props["ax0.grid.y.visible"] is True
    assert props["ax0.grid.y.linestyle"] == "--"
    assert props["ax0.grid.y.color"] == "#cccccc"
    assert props["ax0.grid.x.visible"] is False
    assert "ax0.grid.x.color" not in props
    assert props["ax0.facecolor"] == props["figure.facecolor"] == "#ffffff"
    assert props["ax0.legend.ncols"] == 1
    assert isinstance(props["ax0.legend.frameon"], bool)
    (note,) = [t for t in texts if t["s"] == "note"]
    assert note["role"] == "figtext" and note["color"] == "#ff0000"
    assert note["fontsize"] > 0


@pytest.mark.parametrize(
    "mutation", ["grid_y", "grid_x", "facecolor", "frameon", "ncols"]
)
def test_new_props_flag_collateral_changes_in_explicit_edits(mutation):
    base = probe.snapshot(gdp_fig(), None)["props"]
    fig = gdp_fig()
    ax = fig.axes[0]
    ax.xaxis.label.set_fontsize(ax.xaxis.label.get_fontsize() + 1)  # target
    if mutation == "grid_y":
        ax.grid(axis="y")
    if mutation == "grid_x":
        ax.grid(axis="x")
    if mutation == "facecolor":
        ax.set_facecolor("#f0f0f0")
    if mutation == "frameon":
        ax.legend(frameon=not ax.get_legend().get_frame_on())
    if mutation == "ncols":
        ax.legend(ncols=2)
    edit = probe.snapshot(fig, None)["props"]
    plt.close("all")
    target = ["ax*.xlabel.fontsize"]
    assert metrics.preservation(base, edit, "explicit", target)["ok"] is False
    # an explicit horizontal-grid edit (e17's target) admits only the y grid
    grid_target = [*target, "ax*.grid.y.*"]
    allowed = metrics.preservation(base, edit, "explicit", grid_target)["ok"]
    assert allowed is (mutation == "grid_y")
