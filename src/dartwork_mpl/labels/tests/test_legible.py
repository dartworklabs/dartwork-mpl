"""``dm.legible`` on real charts: the text reads afterwards, and only what
had to change was changed."""

from __future__ import annotations

import io

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib import patheffects
from matplotlib.colors import ListedColormap, to_hex

import dartwork_mpl as dm
from dartwork_mpl.colorspace import LEGIBLE
from dartwork_mpl.geometry import backdrops
from tests.text_on_backgrounds import (
    FAINT,
    contour_labels,
    korean_note,
    point_cloud,
)


@pytest.fixture(autouse=True)
def _own_rc():
    with matplotlib.rc_context():
        yield
    plt.close("all")


def _readings(fig, texts):
    return [behind.read(LEGIBLE) for behind in backdrops(fig, texts)]


def _outlined(text) -> bool:
    return any(
        isinstance(e, patheffects.Stroke) for e in text.get_path_effects()
    )


def _look(fig, texts) -> tuple[object, ...]:
    """Everything ``dm.legible`` may change, and the figure as it saves."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    return (
        [(t.get_color(), t.get_alpha(), t.get_position()) for t in texts],
        [list(t.get_path_effects()) for t in texts],
        buf.getvalue(),
    )


def _said(capsys: pytest.CaptureFixture[str]) -> list[str]:
    """The lines ``dm.legible`` printed since the last call."""
    return [
        line
        for line in capsys.readouterr().err.splitlines()
        if line.startswith("dartwork-mpl: labels:")
    ]


def _crossing(**text):
    """A dark word from white paper onto a dark half."""
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "6cm"), dpi=120)
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.set_axis_off()
    ax.imshow(
        [[0, 1]], cmap=ListedColormap(["white", "#151515"]),
        extent=(0, 1, 0, 1), aspect="auto", interpolation="nearest",
    )  # fmt: skip
    word = ax.text(
        0.5, 0.5, "LEFT RIGHT", ha="center", va="center",
        fontsize=dm.fs(8), color="#151515", **text,
    )  # fmt: skip
    return fig, ax, word


@pytest.mark.parametrize("name", sorted(FAINT))
def test_every_text_reads_after_legible(name: str):
    """The spec's bar: under 2 % of the ink under 3:1 and no half-em window
    half lost, and ``dm.check`` no longer points at the text."""
    fig, texts = FAINT[name]()
    assert any(not r.reads for r in _readings(fig, texts))
    dm.legible(texts)
    for reading in _readings(fig, texts):
        assert reading.low <= 0.02 and reading.worst < 0.5
    assert "TEXT_CONTRAST" not in dm.check(fig).rules


def test_contour_numbers_that_are_lost_take_a_colour_and_the_rest_are_left():
    """On the dark bands the grey numbers are lost and take the colour that
    reads there. The two on the pale bands read (6.3:1 and 4.3:1) and stay
    the grey they were given, though three handed over with them changed."""
    fig, labels = contour_labels()
    by_text = dict(zip([t.get_text() for t in labels], labels, strict=True))
    grey = to_hex(by_text["3.0"].get_color())
    reads = {t.get_text(): r.reads for t, r in zip(labels, _readings(fig, labels), strict=True)}  # fmt: skip
    assert reads == {"3.0": True, "4.0": True, "5.0": False, "6.0": False, "7.0": False}  # fmt: skip
    dm.legible(labels)
    assert not any(_outlined(t) for t in labels)
    assert {n: to_hex(t.get_color()) for n, t in by_text.items()} == {
        "3.0": grey,
        "4.0": grey,
        "5.0": to_hex(matplotlib.rcParams["text.color"]),
        "6.0": "#ffffff",
        "7.0": "#ffffff",
    }
    assert all(r.reads for r in _readings(fig, labels))


def test_numbers_in_points_change_only_where_they_do_not_read():
    """White rank numbers in dark and in orange points: the ones in the
    orange points (2.4:1) change, the ones that read are not touched."""
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "5cm"))
    colours = ["dc.blue8", "dc.orange6", "dc.blue8", "dc.orange6"]
    ax.scatter(range(4), [0] * 4, s=900, color=colours, lw=0, zorder=3)
    numbers = [
        ax.text(x, 0, str(x + 1), ha="center", va="center", color="white", zorder=4)
        for x in range(4)
    ]  # fmt: skip
    ax.set(xlim=(-0.6, 3.6), ylim=(-1, 1))
    ax.axis("off")
    dm.simple_layout(fig)
    dm.legible(numbers)
    assert [to_hex(t.get_color()) == "#ffffff" for t in numbers] == [
        True,
        False,
        True,
        False,
    ]
    assert all(r.reads for r in _readings(fig, numbers))
    assert "TEXT_CONTRAST" not in dm.check(fig).rules


@pytest.mark.parametrize("name", ["korean_note", "vertical_note", "wind_rose"])
def test_a_note_across_backgrounds_keeps_its_colour_and_gets_an_outline(
    name: str,
):
    """No one colour reads on canvas and navy, up a stack of pale and dark
    segments, or across a wind rose: the note stays black and is outlined."""
    fig, (note,) = FAINT[name]()
    dm.legible(note)
    (stroke, *_rest) = note.get_path_effects()
    assert isinstance(stroke, patheffects.Stroke)
    assert to_hex(note.get_color()) == "#000000" and _outlined(note)


def _bars(**style):
    """A pale and a dark bar and a black note across both and the canvas."""
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    ax.bar(["A", "B"], [3, 9], color=["dc.gray2", "#0b2a5b"], **style)
    note = ax.text(0.5, 2.0, "B leads A by six points here", ha="center")
    dm.simple_layout(fig)
    return fig, ax, note


@pytest.mark.parametrize("kind", ["hatch", "image"])
def test_a_note_over_hatching_or_an_image_is_outlined_too(kind: str):
    """Over hatching or an image, as over flat bars, the note is outlined
    and then reads."""
    if kind == "hatch":
        fig, ax, note = _bars(hatch="////", edgecolor="white")
    else:
        fig, ax, note = _bars(alpha=0.0)
        ramp = np.tile(np.linspace(1.0, 0.0, 256), (2, 1))
        ax.imshow(ramp, cmap="gray", aspect="auto", extent=(-0.5, 1.5, 0, 9))
    (before,) = _readings(fig, [note])
    assert not before.reads
    dm.legible(note)
    assert _outlined(note)
    (after,) = _readings(fig, [note])
    assert after.low <= 0.02 and after.reads


def test_translucent_fills_are_judged_by_the_colour_they_show():
    """A translucent bar with a darker one over it: what is behind the ink
    is read from the canvas, so each visible part is the flat colour it
    shows, and whichever fix is taken the note reads cleanly."""
    fig, ax, note = _bars(alpha=0.75)
    ax.bar(["A", "B"], [1, 6], color="#000000", alpha=0.5, width=0.5)
    (before,) = _readings(fig, [note])
    assert not before.reads
    dm.legible(note)
    (after,) = _readings(fig, [note])
    assert after.low <= 0.02 and after.reads


def test_a_text_that_reads_is_left():
    """The note over the point cloud reads at 6:1: nothing is done to it."""
    fig, (note,) = point_cloud()
    before = _look(fig, [note])
    dm.legible(note)
    assert _look(fig, [note]) == before


@pytest.mark.parametrize("name", sorted(FAINT))
def test_calling_it_again_changes_nothing(name: str):
    """Twice is the same as once: the same colours, the same path effects
    (one outline, never two) and the same saved figure."""
    fig, texts = FAINT[name]()
    dm.legible(texts)
    once = _look(fig, texts)
    dm.legible(texts)
    dm.legible(texts)
    assert _look(fig, texts) == once


def test_a_translucent_text_no_colour_can_mend_is_left_as_it_was(
    capsys: pytest.CaptureFixture[str],
):
    """At alpha 0.27 what is behind the word shows through any colour and
    any outline: nothing is changed, however often it is asked, the check
    still points at it, and one line says the word was left."""
    fig, _ax, word = _crossing(alpha=0.27)
    before = _look(fig, [word])
    for _ in range(3):
        capsys.readouterr()
        dm.legible(word)
        lines = _said(capsys)
        assert len(lines) == 1 and "LEFT RIGHT" in lines[0]
        assert _look(fig, [word]) == before
    assert "TEXT_CONTRAST" in dm.check(fig).rules


@pytest.mark.parametrize("cover", [1.0, 0.7])
def test_a_text_under_something_drawn_over_it_is_left_as_it_was(
    cover: float, capsys: pytest.CaptureFixture[str]
):
    """A band drawn over the word (a higher zorder) hides it whatever is
    done to the word: no outline is added, none piles up over three calls,
    and one line says so each time."""
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "6cm"), dpi=120)
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.set_axis_off()
    word = ax.text(
        0.5, 0.5, "LEFT RIGHT", ha="center", va="center",
        fontsize=dm.fs(8), color="#151515",
    )  # fmt: skip
    ax.axvspan(0.5, 1, color="#151515", alpha=cover, zorder=5)
    before = _look(fig, [word])
    for _ in range(3):
        capsys.readouterr()
        dm.legible(word)
        lines = _said(capsys)
        assert len(lines) == 1 and "LEFT RIGHT" in lines[0]
        assert _look(fig, [word]) == before
    assert "TEXT_CONTRAST" in dm.check(fig).rules


def test_an_outline_replaces_the_outline_of_an_earlier_call():
    """The word is outlined for the dark half. Made four times as large,
    its old outline is a hairline that no longer carries it; asked again,
    it gets one outline of its new size, not a second one over the first."""
    fig, _ax, word = _crossing()
    dm.legible(word)
    (first, *_fill) = word.get_path_effects()
    word.set_fontsize(4 * word.get_fontsize())
    (lost,) = _readings(fig, [word])
    assert not lost.reads
    dm.legible(word)
    strokes = [
        e for e in word.get_path_effects() if isinstance(e, patheffects.Stroke)
    ]
    assert len(strokes) == 1 and strokes[0] is not first
    (reading,) = _readings(fig, [word])
    assert reading.reads


def test_only_texts_placed_in_an_axes_are_mended_and_the_rest_are_named(
    capsys: pytest.CaptureFixture[str],
):
    """``dm.legible`` mends what ``TEXT_CONTRAST`` reports. On a dark
    canvas around a light plot the dark title, legend entry, tick label
    and figure note are lost too, but their colour is the preset's: handed
    over, they are left exactly as they were and one line says so, while
    the note placed in the plot with them is mended."""
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    fig.set_facecolor("#10151c")
    ax.bar(["A", "B"], [3, 9], color="#0b2a5b")
    ax.plot([0, 1], [5, 5], label="Target")
    ax.set_title("Weekly output")
    legend = dm.place_legend(ax, loc="below")
    noted = fig.text(0.99, 0.99, "Draft", ha="right", va="top")
    placed = ax.text(0.5, 2.0, "B leads A by six points here", ha="center")
    dm.simple_layout(fig)
    others = [ax.title, legend.get_texts()[0], ax.get_yticklabels()[2], noted]
    assert not any(r.reads for r in _readings(fig, [*others, placed]))
    before = _look(fig, others)[:2]
    capsys.readouterr()
    dm.legible([*others, placed])
    assert _look(fig, others)[:2] == before
    (reading,) = _readings(fig, [placed])
    assert reading.reads
    lines = _said(capsys)
    assert len(lines) == 2  # one for the four left alone, one for the note


@pytest.mark.parametrize("dpi", [100, 300])
@pytest.mark.parametrize("name", ["vertical_note", "korean_note", "wind_rose"])
def test_a_mended_note_holds_at_another_dpi_and_after_a_resize(
    name: str, dpi: int
):
    """The fix is made once; an outline goes where its text goes, so the
    note still reads when the figure is saved at another resolution, or
    resized and laid out again."""
    fig, (note,) = FAINT[name]()
    dm.legible(note)
    fig.set_dpi(dpi)
    (reading,) = _readings(fig, [note])
    assert reading.low <= 0.02 and reading.reads
    fig.set_size_inches(*dm.figsize("13cm", "9cm"))
    dm.simple_layout(fig)
    (again,) = _readings(fig, [note])
    assert again.low <= 0.02 and again.reads


def test_light_text_on_a_dark_preset_is_outlined_in_the_dark_paper():
    """The dark preset turns the poles round: pale text over a pale bar is
    outlined in the dark paper colour it reads best on."""
    dm.style.use("dark")
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    ax.bar(
        ["A", "B", "C"], [3, 9, 5], color=["dc.gray6", "dc.gray1", "dc.gray6"]
    )
    note = ax.text(0.45, 7.5, "B is the outlier here", ha="center")
    dm.simple_layout(fig)
    (before,) = _readings(fig, [note])
    assert not before.reads
    dm.legible(note)
    assert _outlined(note)
    (after,) = _readings(fig, [note])
    assert after.low <= 0.02 and after.reads
    assert to_hex(note.get_color()) == to_hex(matplotlib.rcParams["text.color"])


def test_each_change_is_said_in_one_line_and_quiet_silences_it(
    capsys: pytest.CaptureFixture[str],
):
    """One line for each text changed, naming it; one line for those
    left; none after ``dm.quiet()``."""
    fig, labels = contour_labels()
    capsys.readouterr()
    dm.legible(labels)
    lines = _said(capsys)
    assert len(lines) == 4  # three changed, one line for the two left
    for changed in ("5.0", "6.0", "7.0"):
        assert sum(f'"{changed}"' in line for line in lines) == 1
    assert not any('"3.0"' in line or '"4.0"' in line for line in lines)
    dm.legible(labels)
    assert len(_said(capsys)) == 1
    fig2, (note,) = korean_note()
    dm.quiet()
    try:
        dm.legible(note)
        assert capsys.readouterr().err == ""
    finally:
        dm.verbose()


def test_what_is_not_a_text_in_a_figure_is_refused():
    """A wrong argument is said, not skipped."""
    fig, ax = plt.subplots()
    with pytest.raises(TypeError, match="takes a Text"):
        dm.legible([ax])  # type: ignore[list-item]
    loose = matplotlib.text.Text(0, 0, "loose")
    with pytest.raises(ValueError, match="not drawn in a figure"):
        dm.legible(loose)
