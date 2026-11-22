"""User-visible alignment and its limits on chart geometry."""

import matplotlib.pyplot as plt
import pytest

import dartwork_mpl as dm


@pytest.mark.parametrize(
    "kind", ["dartwork", "native-decimal", "native-right", "annotation"]
)
def test_mark_labels_keep_their_positions(kind, caplog):
    """Choosing alignment leaves labels tied to their own bar or point."""
    with dm.style.context("report"):
        fig, ax = plt.subplots(figsize=dm.figsize("14cm", "6cm"))
        values = [38.6, 182.7, 6.2, 1025.3]
        bars = ax.barh(range(4), values)
        ax.set(xlabel="Value", yticks=[])
        if kind == "dartwork":
            texts = dm.label_bars(ax)
        elif kind == "annotation":
            texts = [
                ax.annotate(
                    f"{n:.1f}",
                    (n, y),
                    xytext=(5, 0),
                    textcoords="offset points",
                )
                for y, n in enumerate(values)
            ]
        else:
            texts = ax.bar_label(bars, fmt="%.1f", padding=5)
        dm.simple_layout(fig)
        renderer = fig.canvas.get_renderer()
        before = [tuple(t.get_window_extent(renderer).extents) for t in texts]
        with caplog.at_level("INFO", logger="dartwork_mpl.labels"):
            caplog.clear()
            assert (
                dm.align_texts(
                    texts, "right" if kind == "native-right" else "decimal"
                )
                == texts
            )
        assert [
            tuple(t.get_window_extent(renderer).extents) for t in texts
        ] == before
        assert all(t.get_visible() for t in texts)
        assert len(caplog.records) == 1
        plt.close(fig)


@pytest.mark.parametrize(
    ("how", "right"), [("left", False), ("center", False), ("right", True)]
)
def test_tick_alignment_reserves_the_outside_margin(how, right):
    """The width of the longest name stays outside either side of the plot."""
    with dm.style.context("report"):
        fig, ax = plt.subplots(figsize=dm.figsize("14cm", "5cm"))
        ax.barh(range(3), [2, 5, 3])
        ax.set(xscale="log", xlabel="Score")
        axis = ax.twinx() if right else ax
        if right:
            ax.set_yticks([])
            axis.invert_yaxis()
        axis.set_yticks(
            range(3), ["Japan", "Democratic Republic of the Congo", "Chile"]
        )
        labels = axis.get_yticklabels()
        assert dm.align_texts(labels, how) == labels
        dm.simple_layout(fig)
        renderer = fig.canvas.get_renderer()
        boxes = [t.get_window_extent(renderer) for t in labels]
        assert all(0 <= b.x0 < b.x1 <= fig.bbox.x1 for b in boxes)
        if right:
            assert min(b.x0 for b in boxes) >= axis.bbox.x1
        else:
            assert max(b.x1 for b in boxes) <= axis.bbox.x0
        plt.close(fig)


@pytest.mark.parametrize(
    "labels",
    [
        ["2026-1-2", "1999-12-31", "2025-02-01"],
        ["5\u201310", "1\u2013100", "100\u20132000"],
        ["12/34", "1/9", "11/13"],
        ["v1.2.3", "v0.9.1", "v10.0.1"],
        ["AB-193", "ID-4", "NO-97"],
        ["2026년 1월 2일", "1999년 12월 31일", "2025년 2월 1일"],
    ],
)
def test_decimal_does_not_rewrite_non_numeric_formats(labels, caplog):
    """Dates, ranges, fractions, versions and identifiers stay literal."""
    fig, ax = plt.subplots()
    originals = [
        ax.text(1.02, i / 4, value, transform=ax.transAxes)
        for i, value in enumerate(labels, 1)
    ]
    with caplog.at_level("INFO", logger="dartwork_mpl.labels"):
        assert dm.align_texts(originals, "decimal") == originals
    assert len(caplog.records) == 1
    assert [t.get_text() for t in originals] == labels
    assert all(t.get_visible() for t in originals)
    plt.close(fig)


@pytest.mark.parametrize(
    "labels",
    [["1.2e-3", "12.5e+10", "3e5"], ["1,284만 원", "12.5억 원", "100.25억 원"]],
)
def test_decimal_keeps_the_exponent_and_attached_unit(labels):
    """Exponent and unit are part of the number and keep their source text."""
    dm.style.use("report-kr")
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "5cm"))
    originals = [
        ax.text(1.02, i / 4, value, transform=ax.transAxes)
        for i, value in enumerate(labels, 1)
    ]
    rows = dm.align_texts(originals, "decimal")
    assert rows != originals
    assert [t.get_text() for t in rows] == labels
    plt.close(fig)


def test_dates_do_not_get_a_decimal_hint():
    """An already aligned column of dates has no decimal-alignment finding."""
    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "5cm"))
    ax.plot([0, 1], [0, 1])
    for i, value in enumerate(
        ("2026-11-22", "2026-1-2", "1999-12-31", "2026-3-02"), 1
    ):
        ax.text(1.04, i / 5, value, transform=ax.transAxes)
    dm.simple_layout(fig)
    assert "TEXT_MISALIGNMENT" not in dm.check(fig).rules
    plt.close(fig)


@pytest.mark.parametrize("table", ["outside", "axis-off"])
def test_column_hint_can_be_followed_without_changing_values(table):
    """The same numeric eligibility applies to hints and explicit alignment."""
    with dm.style.context("scientific"):
        fig, ax = plt.subplots(figsize=dm.figsize("13cm", "5cm"))
        ax.set(xlabel="Estimate", xlim=(0, 1), ylim=(0, 4))
        if table == "axis-off":
            ax.set_axis_off()
            x = 0.1
        else:
            x = 1.04
        source = ["1.1 [2.4, 16.4]", "88.8 [-3.6, 5.2]", "-111.1 [-5.8, 1.6]"]
        for y, label in enumerate(source, 1):
            ax.text(x, y, label, transform=ax.get_yaxis_transform())
        dm.simple_layout(fig)
        (finding,) = [f for f in dm.check(fig) if f.rule == "TEXT_MISALIGNMENT"]
        assert '"decimal"' in finding.fix
        aligned = dm.align_texts(finding.artists, "decimal")
        dm.simple_layout(fig)
        assert "TEXT_MISALIGNMENT" not in dm.check(fig).rules
        assert [t.get_text().replace("\u2212", "-") for t in aligned] == source
        plt.close(fig)


def test_edge_hint_aligns_nearly_coincident_names():
    """A slightly ragged text edge gets a usable hint even without numbers."""
    with dm.style.context("scientific"):
        fig, ax = plt.subplots(figsize=dm.figsize("14cm", "5cm"))
        ax.set(xlabel="Score", ylim=(0, 4))
        source = ["Japan", "DR Congo", "Chile"]
        texts = [
            ax.annotate(
                label,
                (1, i),
                (9 + offset, 0),
                xycoords=ax.get_yaxis_transform(),
                textcoords="offset points",
            )
            for i, (label, offset) in enumerate(
                zip(source, (0, 1.5, 0), strict=True), 1
            )
        ]
        dm.simple_layout(fig)
        (finding,) = [f for f in dm.check(fig) if f.rule == "TEXT_MISALIGNMENT"]
        assert '"left"' in finding.fix
        assert dm.align_texts(finding.artists, "left") == texts
        dm.simple_layout(fig)
        assert "TEXT_MISALIGNMENT" not in dm.check(fig).rules
        assert [text.get_text() for text in texts] == source
        plt.close(fig)


def test_alignment_mode_names_the_valid_choices():
    """Invalid public input raises an actionable ValueError."""
    with pytest.raises(ValueError, match="left, right, center, decimal"):
        dm.align_texts([], "diagonal")


def test_edited_sources_and_removed_overlays_can_be_realigned():
    """Source edits stay visible and removing an overlay restores the original."""
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "5cm"))
    ax.set(ylim=(0, 3))
    originals = [
        ax.text(1.02, y, n, transform=ax.get_yaxis_transform())
        for y, n in enumerate(("12.3", "4.5"), 1)
    ]
    first, second = dm.align_texts(originals, "decimal")
    originals[0].set_text("99.9")
    assert first.get_text() == "99.9"
    rows = dm.align_texts(originals, "decimal")
    assert rows != [first, second]
    rows[0].remove()
    assert originals[0].get_visible()
    assert dm.align_texts(originals, "decimal") != originals
    ax.clear()
    assert dm.align_texts(originals, "decimal") == originals
    plt.close(fig)


def test_annotation_alignment_keeps_a_live_vertical_anchor():
    """Changing a snapped annotation's data y continues to move its text."""
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "5cm"))
    ax.set(ylim=(0, 5))
    text = ax.annotate(
        "Name",
        (1.02, 1),
        (4, 0),
        xycoords=ax.get_yaxis_transform(),
        textcoords="offset points",
    )
    other = ax.text(1.06, 2, "Another", transform=ax.get_yaxis_transform())
    dm.align_texts([text, other], "left")
    dm.simple_layout(fig)
    renderer = fig.canvas.get_renderer()
    before = text.get_window_extent(renderer)
    text.xy = (1.02, 3)
    after = text.get_window_extent(renderer)
    assert after.x0 == pytest.approx(before.x0)
    assert after.y0 > before.y1
    plt.close(fig)


def test_realigning_ticks_after_edit_measures_the_new_width():
    """Tick alignment uses the current strings when explicitly called again."""
    with dm.style.context("report"):
        fig, ax = plt.subplots(figsize=dm.figsize("14cm", "5cm"))
        ax.set_yticks([0, 1, 2], ["A", "B", "C"])
        dm.align_texts(ax.get_yticklabels(), "left")
        ax.set_yticks([0, 1, 2], ["A", "A much longer category name", "C"])
        labels = dm.align_texts(ax.get_yticklabels(), "left")
        dm.simple_layout(fig)
        renderer = fig.canvas.get_renderer()
        boxes = [label.get_window_extent(renderer) for label in labels]
        assert max(box.x1 for box in boxes) < ax.bbox.x0
        assert max(box.x0 for box in boxes) == pytest.approx(
            min(box.x0 for box in boxes)
        )
        plt.close(fig)


def test_decimal_overlay_honours_position_offsets():
    """Moving a returned row changes the visible text's rendered position."""
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "5cm"))
    ax.set_ylim(0, 3)
    labels = [
        ax.text(1.02, y, value, transform=ax.get_yaxis_transform())
        for y, value in enumerate(("1.2", "4.5"), 1)
    ]
    row, _ = dm.align_texts(labels, "decimal")
    dm.simple_layout(fig)
    renderer = fig.canvas.get_renderer()
    before = row.get_window_extent(renderer)
    row.set_position((2, 3))
    after = row.get_window_extent(renderer)
    assert (after.x0 - before.x0, after.y0 - before.y0) == pytest.approx(
        (2 * fig.dpi / 72, 3 * fig.dpi / 72)
    )
    plt.close(fig)


@pytest.mark.parametrize(
    "kind",
    [
        "tick",
        "x-ticks",
        "separate",
        "rotation",
        "multiline",
        "math",
        "arrow",
        "mixed",
        "already",
    ],
)
def test_declined_alignment_emits_one_notice(kind, caplog):
    """An unsupported group is preserved and reports one reason."""
    with dm.style.context("scientific"):
        fig, axes = plt.subplots(1, 2, figsize=dm.figsize("14cm", "5cm"))
        ax, second = axes
        ax.set_yticks([0, 1], ["1.2", "4.5"])
        texts = [
            ax.text(1.02, y, v, transform=ax.transAxes)
            for y, v in enumerate(("1.2", "4.5"))
        ]
        how = "decimal"
        if kind == "tick":
            texts = ax.get_yticklabels()
        elif kind == "x-ticks":
            texts = ax.get_xticklabels()
            how = "left"
        elif kind == "separate":
            texts[1] = second.text(1.02, 1, "4.5", transform=second.transAxes)
        elif kind == "rotation":
            texts[0].set_rotation(20)
        elif kind == "multiline":
            texts[0].set_text("1.2\n4.5")
        elif kind == "math":
            texts[0].set_text("$x^2$")
        elif kind == "arrow":
            texts[0] = ax.annotate(
                "1.2",
                (0.2, 0.3),
                (1.02, 0.3),
                xycoords=ax.transAxes,
                arrowprops={"arrowstyle": "->"},
            )
        elif kind == "mixed":
            texts[0].set_text("1.2 [0.1, 9.9]")
        elif kind == "already":
            texts = dm.align_texts(texts, "decimal")
            how = "left"
        with caplog.at_level("INFO", logger="dartwork_mpl.labels"):
            caplog.clear()
            assert dm.align_texts(texts, how) == texts
        assert len(caplog.records) == 1
        plt.close(fig)


def test_bold_summary_does_not_turn_an_aligned_body_into_a_finding():
    """An intentionally bold summary can have wider glyphs than the rows."""
    with dm.style.context("scientific"):
        fig, ax = plt.subplots(figsize=dm.figsize("13cm", "5cm"))
        ax.set(xlabel="Effect", ylim=(0, 5))
        for y, value in enumerate(
            (
                "0.84 [0.77, 0.92]",
                "0.82 [0.61, 1.10]",
                "0.79 [0.57, 1.09]",
                "0.88 [0.80, 0.97]",
            ),
            1,
        ):
            ax.text(
                1.04,
                y,
                value,
                transform=ax.get_yaxis_transform(),
                fontweight="bold" if y == 4 else "normal",
            )
        dm.simple_layout(fig)
        assert "TEXT_MISALIGNMENT" not in dm.check(fig).rules
        plt.close(fig)
