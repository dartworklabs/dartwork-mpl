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
    """Run renderer assertions outside Matplotlib's callback exception handler."""
    failures = []
    called = False

    def capture(event):
        """Keep a failing measurement for pytest to report."""
        nonlocal called
        called = True
        try:
            read(event)
        except Exception as error:
            failures.append(error)

    signal = fig.canvas.mpl_connect("draw_event", capture)
    try:
        fig.savefig(BytesIO(), format=fmt, dpi=dpi)
    finally:
        fig.canvas.mpl_disconnect(signal)
    assert called
    if failures:
        raise failures[0]


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
                    for p in row.get_children()
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


def inter_joints():
    """Four proportional-digit rows with three stops outside a log axis."""
    dm.style.use("scientific")
    fig, ax = plt.subplots(figsize=dm.figsize("15cm", "5cm"))
    ax.set(xscale="log", xlim=(1, 10), ylim=(-0.55, 3.55))
    texts = [
        ax.text(
            1.04,
            y,
            s,
            transform=ax.get_yaxis_transform(),
            va="center",
            fontproperties=FontProperties(family="Inter", size=10),
        )
        for y, s in enumerate(ROWS)
    ]
    dm.align_texts(texts, "decimal")
    dm.simple_layout(fig)
    return fig


@pytest.mark.parametrize(
    "build", [forest_alignment, inter_joints, korean_alignment]
)
@pytest.mark.parametrize("fmt", ["pdf", "svg", "png"])
def test_numeric_joints_keep_original_spacing(build, fmt, record_property):
    """No rendered joint loses its authored whitespace at any tab stop."""
    from matplotlib.text import Text

    figure = build()

    def read(event):
        renderer = event.renderer
        tight = {}
        for artist in figure.axes[0].texts:
            pieces = [
                child
                for child in artist.get_children()
                if isinstance(child, Text)
            ]
            if not pieces:
                continue
            text = artist.get_text()
            group = (len(pieces), text.endswith("%"))
            font = artist.get_fontproperties()

            def width(value, font=font):
                """Read a native renderer advance, in display pixels."""
                return float(
                    renderer.get_text_width_height_descent(value, font, False)[
                        0
                    ]
                )

            cursor = 0
            previous = None
            for i, piece in enumerate(pieces):
                value = piece.get_text()
                start = text.index(value, cursor)
                current = piece.get_window_extent(renderer)
                if previous is not None:
                    gap = (current.x0 - previous.x1) * 72 / figure.dpi
                    # This advance in the intact string includes the
                    # renderer's kerning at both sides of the joint.
                    expected = (
                        (
                            width(text[:start] + value[0])
                            - width(value[0])
                            - width(text[:cursor])
                        )
                        * 72
                        / figure.dpi
                    )
                    if fmt == "png" and start > cursor:
                        separation = text[cursor:start]
                        advance, _, _ = (
                            text_to_path.get_text_width_height_descent(
                                separation, font, False
                            )
                        )
                        assert gap >= advance - 0.05, (text, i, gap, advance)
                    delta = float(gap - expected)
                    assert delta >= -0.05, (text, fmt, i, gap, expected)
                    key = (group, i)
                    tight[key] = min(tight.get(key, float("inf")), abs(delta))
                previous = current
                cursor = start + len(value)
        assert tight
        record_property("max_tight_joint_error_pt", max(tight.values()))
        if fmt != "png":
            assert max(tight.values()) <= 0.05

    during_save(figure, fmt, 200, read)
    plt.close(figure)


@pytest.mark.parametrize("literal", ["", " ", "   ", "\xa0"])
def test_authored_separator_advance_survives_a_vector_render(literal):
    """The real SVG advances preserve missing, repeated and nonbreaking spaces."""
    with dm.style.context("scientific"):
        fig, ax = plt.subplots(figsize=dm.figsize("10cm", "4cm"))
        value = f"1.1,{literal}[2.2%]"
        labels = [
            ax.text(1.03, y, value, transform=ax.transAxes) for y in (0.3, 0.7)
        ]
        row, _ = dm.align_texts(labels, "decimal")
        dm.simple_layout(fig)

        def read(event):
            renderer = event.renderer
            pieces = {t.get_text(): t for t in row.get_children()}
            a = pieces[".1,"].get_window_extent(renderer)
            b = pieces["[2"].get_window_extent(renderer)
            width = renderer.get_text_width_height_descent(
                literal, row.get_fontproperties(), False
            )[0]
            assert b.x0 - a.x1 == pytest.approx(width, abs=0.05)

        during_save(fig, "svg", 72, read)
        plt.close(fig)
