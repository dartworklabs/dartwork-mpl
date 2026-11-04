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
