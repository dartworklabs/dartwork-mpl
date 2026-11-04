"""Effective margins reject before drawing or mutation, preserving old precedence."""

import hashlib
import random
import warnings

import matplotlib.pyplot as plt
import pytest
from matplotlib.gridspec import GridSpecBase

import dartwork_mpl as dm

_NO_GRID = (
    "simple_layout: no GridSpec found (figure uses fig.add_axes or "
    "manually placed axes); layout unchanged. Build axes via "
    "plt.subplots / fig.add_gridspec to use content-aware margins."
)


def _figure(kind="grid"):
    """Pre-draw orphan labels with unequal label and major/minor tick fonts."""
    dm.style.use("scientific")
    fig = plt.figure(figsize=dm.figsize("13cm", "standard"))
    axes = (
        fig.subplots(1, 2)
        if kind == "grid"
        else [fig.add_axes([0.15, 0.15, 0.7, 0.7])]
        if kind == "manual"
        else []
    )
    for ax in axes:
        ax.plot([1e6, 1e6 + 1], [2e6, 2e6 + 1])
        ax.minorticks_on()
        for axis in (ax.xaxis, ax.yaxis):
            axis.label.set_fontsize(dm.fs(3))
            axis.label.set_fontweight(dm.fw(1))
            for minor in (False, True):
                for label in axis.get_ticklabels(minor=minor):
                    label.set_fontsize(dm.fs(-1))
            axis.get_offset_text().set_fontsize(dm.fs(-1))
    fig.canvas.draw()
    return fig


def _state(fig):
    """Read bounds, raw/resolved edges and fonts of every existing tick/offset."""
    grids = list(dict.fromkeys(ax.get_gridspec() for ax in fig.axes))
    fonts = []
    for ax in fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            texts = [axis.get_offset_text()]
            for ticks in (axis.majorTicks, axis.minorTicks):
                texts.extend(
                    t for tick in ticks for t in (tick.label1, tick.label2)
                )
            for text in texts:
                font = text.get_fontproperties()
                fonts.append(
                    (
                        font.get_size_in_points(),
                        font.get_weight(),
                        font.get_family(),
                        font.get_style(),
                        font.get_variant(),
                        font.get_stretch(),
                    )
                )
    keys = ("left", "right", "bottom", "top", "wspace", "hspace")
    return {
        "bounds": [ax.get_position().bounds for ax in fig.axes],
        "edges": [
            [getattr(g, k) for k in keys]
            + [getattr(g.get_subplot_params(fig), k) for k in keys]
            for g in grids
            if g is not None
        ],
        "fonts": fonts,
        # simple_layout also installs tick formatters (#554); a refused
        # call must leave them as they were.
        "formatters": [
            type(axis.get_major_formatter()).__name__
            for ax in fig.axes
            for axis in (ax.xaxis, ax.yaxis)
        ],
    }


def _observe(fig, kwargs):
    """Observe real draws and capture errors without skipping state inspection."""
    draws = []
    draw = fig.canvas.draw

    def observed_draw(*args, **kw):
        """Count draws while retaining actual Agg rendering."""
        draws.append(1)
        return draw(*args, **kw)

    fig.canvas.draw = observed_draw
    error = None
    result = None
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            result = dm.simple_layout(
                fig, adopt_orphan_tick_font=True, **kwargs
            )
        except Exception as exc:
            error = exc
    return error, result, draws, [str(w.message) for w in caught]


_NONFINITE = [
    {"margin": value}
    for number in (float("nan"), float("inf"), float("-inf"))
    for value in (number, f"{number}%", dm.cm(1) * number)
] + [
    {"margin": 0.02, "ml": float("nan")},
    {"margin": 0.02, "mr": "inf%"},
    {"margin": 0.02, "mt": dm.cm(1) * -float("inf")},
    {"margin": 0.02, "mb": float("inf")},
    {"margin": float("nan"), "ml": 0.02},
]


@pytest.mark.parametrize("kwargs", _NONFINITE)
def test_nonfinite_effective_margin_rejects_without_effects(kwargs):
    """All nonfinite effective sides refuse before any layout or font effects."""
    fig = _figure()
    try:
        before = _state(fig)
        error, _, draws, _ = _observe(fig, kwargs)
        after = _state(fig)
        checks = {
            "error": (type(error), str(error))
            == (ValueError, "margin must resolve to finite figure fractions"),
            "draws": draws == [],
            "bounds": after["bounds"] == before["bounds"],
            "edges": after["edges"] == before["edges"],
            "fonts": after["fonts"] == before["fonts"],
            "formatters": after["formatters"] == before["formatters"],
        }
        assert checks == dict.fromkeys(checks, True), checks
    finally:
        plt.close(fig)


def _render(margin, sides):
    """Return full state and rendered RGBA digest after a real finite layout."""
    fig = _figure()
    try:
        dm.simple_layout(
            fig, margin=margin, adopt_orphan_tick_font=True, **sides
        )
        fig.canvas.draw()
        return _state(fig), hashlib.sha256(fig.canvas.buffer_rgba()).hexdigest()
    finally:
        plt.close(fig)


def test_full_finite_overrides_preserve_layout():
    """Complete finite overrides ignore nonfinite bases, including seeded cases."""
    rng = random.Random(20261029)
    cases = [{"ml": 0.02, "mr": "3%", "mt": dm.cm(0.1), "mb": -0.01}]
    for _ in range(8):
        left, right, top, bottom = [rng.uniform(-0.1, 0.8) for _ in range(4)]
        cases.append(
            {
                "ml": left,
                "mr": f"{right * 100}%",
                "mt": dm.cm(1) * top,
                "mb": bottom,
            }
        )
    for sides in cases:
        expected = _render(0, sides)
        for margin in (float("nan"), float("inf"), float("-inf")):
            assert _render(margin, sides) == expected, sides


@pytest.mark.parametrize(
    ("kind", "kwargs", "expected_error", "expected_warnings"),
    [
        ("empty", {"margin": float("nan"), "mb": "a%"}, None, []),
        ("manual", {"margin": float("nan"), "mb": "a%"}, None, [_NO_GRID]),
        (
            "grid",
            {"gs": GridSpecBase(1, 1), "margin": float("nan"), "mb": "a%"},
            None,
            [_NO_GRID],
        ),
        (
            "grid",
            {"margin": float("nan"), "ml": float("inf"), "mb": "a%"},
            (ValueError, "could not convert string to float: 'a'"),
            [],
        ),
    ],
)
def test_margin_preflight_preserves_parse_and_noop_precedence(
    kind, kwargs, expected_error, expected_warnings
):
    """Empty/manual/unsupported grids precede parsing; late parse errors win."""
    fig = _figure(kind)
    try:
        before = _state(fig)
        error, result, draws, caught = _observe(fig, kwargs)
        assert (
            None if error is None else (type(error), str(error))
        ) == expected_error
        assert result is None
        assert draws == []
        assert _state(fig) == before
        assert caught == expected_warnings
    finally:
        plt.close(fig)
