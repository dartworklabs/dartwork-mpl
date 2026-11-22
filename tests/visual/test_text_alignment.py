"""Measure text alignment on the renderer drawing the chart."""

from io import BytesIO

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.font_manager import FontProperties
from matplotlib.textpath import text_to_path

import dartwork_mpl as dm
from dartwork_mpl.check.measure import measure

from .alignment_scenes import forest_alignment, korean_alignment

BACKENDS = [("png", 100), ("png", 200), ("png", 300), ("pdf", 72), ("svg", 72)]

ROWS = [
    "1.1 [88.8%, 1,151.0]",
    "88.8 [-111.1%, 8.0]",
    "-111.1 {8.0%, 1.1}",
    "1,151.0 (1.1%, 88.8)",
]


def during_save(fig, fmt, dpi, read):
    signal = fig.canvas.mpl_connect("draw_event", read)
    try:
        fig.savefig(BytesIO(), format=fmt, dpi=dpi)
    finally:
        fig.canvas.mpl_disconnect(signal)


@pytest.mark.parametrize(("fmt", "dpi"), BACKENDS)
@pytest.mark.parametrize(
    "font", ["Inter", "Pretendard", "DejaVu Sans", "DejaVu Serif"]
)
def test_proportional_decimal_stops(font, fmt, dpi, record_property):
    with dm.style.context("scientific"):
        fig, ax = plt.subplots(figsize=dm.figsize("14cm", "6cm"))
        ax.set(xscale="log", xlim=(1, 10), ylim=(0, 5))
        prop = FontProperties(family=font, size=10)
        if font in {"Inter", "Pretendard"}:
            advances = [
                text_to_path.get_text_width_height_descent(n, prop, False)[0]
                for n in ("1", "8")
            ]
            assert advances[0] != advances[1]
        labels = [
            ax.text(
                1.03,
                y,
                s,
                transform=ax.get_yaxis_transform(),
                va="center",
                fontproperties=prop,
            )
            for y, s in enumerate(ROWS, 1)
        ]
        aligned = dm.align_texts(labels, "decimal")
        dm.simple_layout(fig)

        def read(event):
            k = 72 / fig.dpi
            offsets = [
                [
                    p.get_window_extent(event.renderer).x0 * k
                    for p in row.pieces
                    if p.get_text().startswith(".")
                ]
                for row in aligned
            ]
            assert all(len(row) == 3 for row in offsets)
            maximum = max(np.ptp(stop) for stop in zip(*offsets, strict=True))
            record_property("decimal_spread_pt", float(maximum))
            assert maximum <= 0.01

        during_save(fig, fmt, dpi, read)
        plt.close(fig)


@pytest.mark.parametrize("fmt", ["pdf", "svg"])
def test_one_row_and_whole_text_extents(fmt, record_property):
    with dm.style.context("scientific"):
        fig, ax = plt.subplots(figsize=dm.figsize("9cm", "4cm"))
        strings = ["-13.9 [-13.9, 2.5]"] * 2
        texts = [
            ax.text(1.02, y, s, transform=ax.get_yaxis_transform(), va="center")
            for y, s in enumerate(strings)
        ]
        whole = ax.text(
            1.02,
            0,
            "\u221213.9 [\u221213.9, 2.5]",
            transform=ax.get_yaxis_transform(),
            va="center",
        )
        row = dm.align_texts(texts, "decimal")[0]

        def read(event):
            renderer = event.renderer
            error = (
                max(
                    abs(
                        row.get_window_extent(renderer).extents
                        - whole.get_window_extent(renderer).extents
                    )
                )
                * 72
                / fig.dpi
            )
            record_property("union_error_pt", float(error))
            assert error <= 0.1

        during_save(fig, fmt, 72, read)
        plt.close(fig)


def test_forest_counts_rows_and_keeps_the_frame_after_resize(record_property):
    fig = forest_alignment()
    ax = fig.axes[0]
    expected_ticks = [t.get_text() for t in ax.get_yticklabels()]
    assert len(expected_ticks) == 10
    assert expected_ticks[0] == "Study A (2014)"
    assert len(ax.lines) == 2
    assert ax.get_ylim() == (-0.7, 9.7)
    for width in (14, 16):
        fig.set_size_inches(*dm.figsize(f"{width}cm", "6.5cm"))
        dm.simple_layout(fig)
        facts = measure(fig)
        assert len([t for t in facts.texts if t.role.free]) == 10
        report = dm.check(fig)
        assert not report, str(report)
        extents = [t.box for t in facts.texts if t.role.free]
        clearance = (
            min(
                facts.canvas.x1 - max(t.x1 for t in extents),
                min(t.y0 for t in extents),
                facts.canvas.y1 - max(t.y1 for t in extents),
            )
            / facts.px_per_pt
        )
        record_property(f"clearance_{width}cm_pt", float(clearance))
        assert clearance >= 72 / 25.4 - 0.01
        assert [t.get_text() for t in ax.get_yticklabels()] == expected_ticks
    plt.close(fig)


def test_korean_alignment_passes_check():
    fig = korean_alignment()
    report = dm.check(fig)
    assert not report, str(report)
    plt.close(fig)
