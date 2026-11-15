"""``check_figure_quality`` figure diagnostics."""

import random

import matplotlib as mpl
from matplotlib.figure import Figure

import dartwork_mpl as dm
from dartwork_mpl import validate


def test_threshold_and_ordered_global_style_diagnostics():
    """DPI endpoints and global style advice precede per-axis findings."""
    with mpl.rc_context({"font.size": 10.0}):
        for dpi in (199, 200, 201):
            fig = Figure(figsize=dm.figsize("13cm", "standard"), dpi=dpi)
            ax = fig.subplots()
            ax.set_xticks(range(21))
            ax.set_yticks(range(20))
            expected = (
                ["Low DPI (199), should be at least 200"] if dpi == 199 else []
            ) + [
                "Style may not be applied (using default font size)",
                "Axes 0: Missing x-axis label",
                "Axes 0: Missing y-axis label",
                "Axes 0: Too many x-ticks (21)",
                "Axes 0: No data plotted",
            ]
            assert dm.check_figure_quality(fig) == expected


def test_artist_families_and_hidden_visibility():
    """Every supported artist family counts only while visible; hidden axes are skipped."""
    with mpl.rc_context({"font.size": 11.0}):
        for kind in ("line", "patch", "collection", "image", "table"):
            fig = Figure(figsize=dm.figsize("13cm", "standard"), dpi=200)
            ax = fig.subplots()
            ax.xaxis.set_visible(False)
            ax.yaxis.set_visible(False)
            if kind == "line":
                artist = ax.plot([0, 1], [1, 2])[0]
            elif kind == "patch":
                artist = ax.bar([0], [1])[0]
            elif kind == "collection":
                artist = ax.scatter([0], [1])
            elif kind == "image":
                artist = ax.imshow([[1]])
            else:
                artist = ax.table(cellText=[["a"]])
            assert dm.check_figure_quality(fig) == [], kind
            artist.set_visible(False)
            assert dm.check_figure_quality(fig) == [
                "Axes 0: No data plotted"
            ], kind
            ax.set_visible(False)
            assert dm.check_figure_quality(fig) == [], kind
        assert (
            dm.check_figure_quality(
                Figure(figsize=dm.figsize("13cm", "standard"), dpi=200)
            )
            == []
        )


def test_seeded_diagnostics_leave_figures_unchanged_and_return_fresh_lists():
    """Seed 20261030 varies six real figures without mutating artists or rcParams."""
    rng = random.Random(20261030)
    with mpl.rc_context({"font.size": 11.0}):
        for _ in range(6):
            fig = Figure(
                figsize=dm.figsize("13cm", "standard"),
                dpi=rng.choice((199, 200, 201)),
            )
            ax = fig.subplots()
            line = ax.plot([0, 1], [rng.random(), rng.random()])[0]
            ax.set_xticks(range(rng.choice((20, 21))))
            line.set_visible(rng.choice((True, False)))
            ax.set_visible(rng.choice((True, False)))
            before = (
                fig.dpi,
                fig.stale,
                tuple(ax.get_children()),
                tuple(ax.get_xlim()),
                tuple(ax.get_ylim()),
                tuple(ax.get_xticks()),
                line.get_visible(),
                line.get_ydata().copy(),
                dict(mpl.rcParams),
            )
            results = [
                f(fig)
                for f in (
                    dm.check_figure_quality,
                    validate.check_figure_quality,
                )
            ]
            assert all(result == results[0] for result in results)
            assert len({id(result) for result in results}) == 2
            after = (
                fig.dpi,
                fig.stale,
                tuple(ax.get_children()),
                tuple(ax.get_xlim()),
                tuple(ax.get_ylim()),
                tuple(ax.get_xticks()),
                line.get_visible(),
            )
            assert before[:7] == after
            assert (before[7] == line.get_ydata()).all()
            assert before[8] == dict(mpl.rcParams)
