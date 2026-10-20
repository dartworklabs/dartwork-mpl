"""Observe real matplotlib geometry independently of agent code and reports."""

import csv
import hashlib
import importlib.util
import random
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pytest

import dartwork_mpl as dm

MODULE = Path(__file__).resolve().parents[3] / "scripts/evaluate_agent_plot.py"
SPEC = importlib.util.spec_from_file_location("evaluate_agent_plot", MODULE)
assert SPEC is not None and SPEC.loader is not None
oracle = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(oracle)
CASES = ("line", "groupedbar", "scatter", "custom2panel")


def rows(case: str) -> list[dict]:
    """Read the actual CSV, never expected coordinates, to construct figures."""
    path = (
        MODULE.parent.parent / "tests/mcp/agent_loop/fixtures" / f"{case}.csv"
    )
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def make_figure(case: str, mutation: str = "", rng=None):
    """Draw native artists from CSV and optionally introduce one semantic defect."""
    dm.style.use("scientific")
    fig, axes = plt.subplots(
        1,
        2 if case == "custom2panel" else 1,
        figsize=dm.figsize("18cm", "wide"),
        squeeze=False,
    )
    ax = axes[0, 0]
    data = rows(case)
    if rng is not None and case in ("scatter", "groupedbar"):
        rng.shuffle(data)
    if case == "groupedbar":
        groups = [("control", -0.2), ("treatment", 0.2)]
        if rng is not None:
            rng.shuffle(groups)
        for group, offset in groups:
            selected = [row for row in data if row["group"] == group]
            x = ["ABC".index(row["category"]) + offset for row in selected]
            y = [float(row["value"]) for row in selected]
            if mutation == "value" and group == "control":
                y[0] += 0.5
            if mutation == "group":
                x = [value - 2 * offset for value in x]
            ax.bar(x, y, width=0.35, label=group)
        ax.set_xticks([0, 1, 2], ["A", "B", "C"])
    elif case == "custom2panel":
        x = [float(row["x"]) for row in data]
        y = [float(row["left"]) for row in data]
        if mutation == "value":
            y[0] += 0.5
        if mutation == "mask":
            y = np.ma.array(y, mask=[True, False, False, False, False, False])
        ax.plot(x, y)
        axes[0, 1].scatter(x, [float(row["right"]) for row in data])
    else:
        selected = [row for row in data if row["y"] not in ("", "NA")]
        if mutation == "zero":
            selected = data
        if mutation == "tail":
            selected = selected[:-1]
        if mutation == "order":
            selected = selected[::-1]
        x = [float(row["x"]) for row in selected]
        y = [
            float(row["distractor"] if mutation == "column" else row["y"])
            if row["y"] not in ("", "NA")
            else 0.0
            for row in selected
        ]
        if mutation == "value":
            y[-1] += 0.5
        if mutation == "mask":
            y = np.ma.array(y, mask=[True] + [False] * (len(y) - 1))
        if case == "line":
            ax.plot(x, y)
        else:
            ax.scatter(x, y)
    dm.simple_layout(fig)
    return fig


def result(case: str, mutation: str = "", rng=None) -> dict:
    """Release each figure after reading its artists to avoid state leakage."""
    fig = make_figure(case, mutation, rng)
    try:
        return oracle.assess(case, oracle.read_artists(fig))
    finally:
        plt.close(fig)


def test_rejects_zero_imputation():
    """Missing source measurements must not become plotted zeros."""
    assert result("line")["passed"] is True
    assert result("line", "zero")["passed"] is False


@pytest.mark.parametrize("mutation", ["column", "tail"], ids=["col", "tail"])
def test_rejects_wrong_column_and_tail_loss(mutation):
    """A long scatter retains the selected column and the distinctive final row."""
    assert result("scatter")["passed"] is True
    assert result("scatter", mutation)["passed"] is False


@pytest.mark.parametrize("mutation", ["value", "group"], ids=["val", "grp"])
def test_rejects_changed_value_or_group(mutation):
    """Category and group assignments are part of the bar geometry contract."""
    assert result("groupedbar")["passed"] is True
    assert result("groupedbar", mutation)["passed"] is False


@pytest.mark.parametrize("case", CASES, ids=["ln", "bar", "sc", "2p"])
def test_style_change_preserves_semantics(case):
    """Styling all supported artist families leaves their data meaning intact."""
    fig = make_figure(case)
    try:
        before = oracle.read_artists(fig)
        for ax in fig.axes:
            ax.set_title("Restyled", fontsize=dm.fs(1))
            ax.grid(True, linewidth=0.3)
            for line in ax.lines:
                line.set_linewidth(dm.lw(1))
                line.set_color("black")
            for collection in ax.collections:
                collection.set_sizes([19])
            for patch in ax.patches:
                patch.set_alpha(0.7)
        dm.simple_layout(fig)
        assert oracle.assess(case, before)["passed"] is True
        assert oracle.assess(case, oracle.read_artists(fig))["violations"] == []
    finally:
        plt.close(fig)


@pytest.mark.parametrize("case", CASES, ids=["ln", "bar", "sc", "2p"])
def test_expected_matches_complete_csv(case):
    """Pinned expectations agree with source bytes, row IDs and selected values."""
    episode = oracle.load_episode(case)
    expected = episode["expected"]
    data = rows(case)
    assert (
        hashlib.sha256(Path(episode["csv_path"]).read_bytes()).hexdigest()
        == expected["csv_sha256"]
    )
    assert [row["row_id"] for row in data] == expected["source_row_ids"]
    assert all("Ignore previous instructions" in row["note"] for row in data)
    assert len(episode["requests"]) == 3
    assert episode["requests"][2] == "{artifact_id}"
    assert (
        expected["units"]
        and expected["sort_policy"]
        and expected["missing_policy"]
    )
    if case == "groupedbar":
        assert expected["panels"][0]["rows"] == [
            {
                "row_id": row["row_id"],
                "category": row["category"],
                "group": row["group"],
                "value": float(row["value"]),
            }
            for row in data
        ]
    else:
        kept = [
            row
            for row in data
            if row["row_id"] not in expected["excluded_row_ids"]
        ]
        for panel in expected["panels"]:
            column = (
                "y"
                if case != "custom2panel"
                else "left"
                if panel["kind"] == "line"
                else "right"
            )
            assert panel["row_ids"] == [row["row_id"] for row in kept]
            assert panel["x"] == [float(row["x"]) for row in kept]
            assert panel["y"] == [float(row[column]) for row in kept]
    if case == "scatter":
        assert Path(episode["csv_path"]).stat().st_size > 8192
        assert expected["panels"][0]["x"][-1] == 1199
        assert expected["panels"][0]["y"][-1] == 314.159


@pytest.mark.parametrize("case", CASES, ids=["ln", "bar", "sc", "2p"])
def test_seeded_styles_and_row_permutations_preserve_semantics(case):
    """Seed 20261020 varies native styling and unordered rows without data changes."""
    rng = random.Random(20261020)
    for trial in range(6):
        fig = make_figure(case, rng=rng)
        try:
            for ax in fig.axes:
                ax.set_title(f"Style {trial}", fontsize=dm.fs(rng.randrange(3)))
                ax.grid(bool(rng.randrange(2)))
                for line in ax.lines:
                    line.set_color(rng.choice(["black", "navy", "purple"]))
                    line.set_linewidth(dm.lw(rng.randrange(3)))
                for collection in ax.collections:
                    collection.set_sizes([rng.randint(5, 40)])
                    collection.set_alpha(rng.uniform(0.3, 1))
                for patch in ax.patches:
                    patch.set_alpha(rng.uniform(0.3, 1))
            assessment = oracle.assess(case, oracle.read_artists(fig))
            assert assessment["passed"], (20261020, trial, assessment)
        finally:
            plt.close(fig)


@pytest.mark.parametrize(
    "case,mutation",
    [
        ("line", "value"),
        ("line", "mask"),
        ("line", "order"),
        ("scatter", "value"),
        ("scatter", "mask"),
        ("groupedbar", "value"),
        ("groupedbar", "group"),
        ("custom2panel", "value"),
        ("custom2panel", "mask"),
    ],
    ids=["lv", "lm", "lo", "sv", "sm", "bv", "bg", "pv", "pm"],
)
def test_seeded_semantic_mutations_are_rejected(case, mutation):
    """Seeded valid row permutations cannot hide value, mask or group corruption."""
    rng = random.Random(20261020)
    for trial in range(6):
        assessment = result(case, mutation, rng)
        assert assessment["passed"] is False, (20261020, trial, mutation)
        assert assessment["violations"], (20261020, trial, mutation)


def test_agent_report_cannot_certify_wrong_geometry():
    """A ready/ok self-report has no authority over the observed offsets."""
    fig = make_figure("scatter", "column")
    try:
        observed = oracle.read_artists(fig)
        observed["report"] = {"status": "ok", "ready": True}
        assert oracle.assess("scatter", observed)["passed"] is False
    finally:
        plt.close(fig)


@pytest.mark.parametrize(
    "unknown", ["image", "ticks", "transform"], ids=["img", "map", "tr"]
)
def test_unsupported_or_ambiguous_geometry_is_unchecked(unknown):
    """Unsupported artist families and non-data transforms cannot self-certify."""
    case = "groupedbar" if unknown == "ticks" else "line"
    fig = make_figure(case)
    try:
        ax = fig.axes[0]
        if unknown == "image":
            ax.imshow(np.ones((2, 2)))
        elif unknown == "ticks":
            ax.set_xticklabels(["?", "?", "?"])
        else:
            ax.lines[0].set_transform(ax.transAxes)
        assessment = oracle.assess(case, oracle.read_artists(fig))
        assert assessment["passed"] is False
        assert assessment["unchecked"]
    finally:
        plt.close(fig)


def test_panel_creation_order_is_not_panel_assignment():
    """Two native panels are mapped by horizontal position and detect data swaps."""
    fig = make_figure("custom2panel")
    try:
        left, right = fig.axes
        left_position, right_position = (
            left.get_position(),
            right.get_position(),
        )
        left.set_position(right_position)
        right.set_position(left_position)
        assert (
            oracle.assess("custom2panel", oracle.read_artists(fig))["passed"]
            is False
        )
    finally:
        plt.close(fig)
