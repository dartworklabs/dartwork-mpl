"""Annotation helpers name the keyword they cannot honour and the fix (#483).

``label_axes`` has its own file (``test_label_axes_diagnostics.py``); this one
covers the helpers that share its guard: ``annotate_value``,
``annotate_corner``, ``label_hline``, ``label_line_ends`` and ``add_note``.
Each gets the three checks of the policy: a property the helper sets itself
raises ``TypeError`` naming it and the right argument, a name the artist does
not take raises ``AttributeError``, and an ordinary ``Text`` property still
reaches the artist (the guard against over-blocking).
"""

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import pytest

import dartwork_mpl as dm


@pytest.fixture
def fig_ax():
    """Two labelled lines and a reference line on a throwaway figure."""
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1], label="rise")
    ax.plot([0, 1], [1, 0], label="fall")
    ax.axhline(0.5)
    yield fig, ax
    plt.close(fig)


# Each helper in a mode where it leaves ha= / va= to the caller.
_CALLS = {
    "annotate_value": lambda fig, ax, **kw: dm.annotate_value(
        ax, 0.5, 0.5, "v", side="above", **kw
    ),
    "annotate_corner": lambda fig, ax, **kw: dm.annotate_corner(
        ax, "c", avoid_overlap=False, **kw
    ),
    "label_hline": lambda fig, ax, **kw: dm.label_hline(
        ax, 0.5, "h", x="right", **kw
    ),
    "label_line_ends": lambda fig, ax, **kw: dm.label_line_ends(ax, **kw)[0],
    "add_note": lambda fig, ax, **kw: dm.add_note(fig, "n", **kw),
}

# (helper, owned kwarg, value, the right argument the message must name)
_OWNED = [
    ("annotate_value", "xy", (0.1, 0.1), "x= and y="),
    ("annotate_value", "xycoords", "axes fraction", "x= and y="),
    ("annotate_value", "xytext", (5, 5), "offset_pt="),
    ("annotate_value", "textcoords", "offset pixels", "offset_pt="),
    ("annotate_value", "transform", None, "offset_pt="),
    ("annotate_value", "size", 20, "fontsize="),
    ("annotate_value", "horizontalalignment", "right", "ha="),
    ("annotate_value", "verticalalignment", "top", "va="),
    ("annotate_corner", "xy", (0.1, 0.1), "loc="),
    ("annotate_corner", "xytext", (5, 5), "inset_pt="),
    ("annotate_corner", "textcoords", "offset pixels", "inset_pt="),
    ("annotate_corner", "transform", None, "loc="),
    ("annotate_corner", "x", 0.3, "loc="),
    ("annotate_corner", "size", 20, "fontsize="),
    ("annotate_corner", "horizontalalignment", "right", "ha="),
    ("label_hline", "xy", (0.1, 0.1), "y="),
    ("label_hline", "xytext", (5, 5), "gap_pt="),
    ("label_hline", "transform", None, "gap_pt="),
    ("label_hline", "size", 20, "fontsize="),
    ("label_hline", "verticalalignment", "top", "va="),
    ("label_line_ends", "xy", (0.1, 0.1), "gap_pt="),
    ("label_line_ends", "xytext", (5, 5), "gap_pt="),
    ("label_line_ends", "transform", None, "gap_pt="),
    ("label_line_ends", "y", 0.3, "gap_pt="),
    ("label_line_ends", "horizontalalignment", "right", "ha="),
    ("add_note", "x", 0.3, "position="),
    ("add_note", "y", 0.3, "position="),
    ("add_note", "size", 20, "fontsize="),
    ("add_note", "horizontalalignment", "right", "ha="),
]


@pytest.mark.parametrize(("helper", "name", "value", "fix"), _OWNED)
def test_owned_property_raises_typeerror_naming_it_and_the_fix(
    fig_ax, helper, name, value, fix
):
    """Each of these used to collide inside matplotlib or vanish silently."""
    fig, ax = fig_ax
    if name == "transform":
        value = ax.transAxes
    before = (len(ax.texts), len(fig.texts))
    with pytest.raises(TypeError) as caught:
        _CALLS[helper](fig, ax, **{name: value})
    message = str(caught.value)
    assert f"{helper}()" in message
    assert repr(name) in message
    assert fix in message
    assert (len(ax.texts), len(fig.texts)) == before


@pytest.mark.parametrize(
    ("helper", "call", "name"),
    [
        (
            "annotate_value",
            lambda ax: dm.annotate_value(ax, 0.5, 0.5, "v", ha="left"),
            "ha",
        ),
        (
            "annotate_value",
            lambda ax: dm.annotate_value(ax, 0.5, 0.5, "v", va="top"),
            "va",
        ),
        (
            "annotate_corner",
            lambda ax: dm.annotate_corner(ax, "c", ha="right"),
            "ha",
        ),
        (
            "label_hline",
            lambda ax: dm.label_hline(ax, 0.5, "h", x="auto", ha="left"),
            "ha",
        ),
    ],
)
def test_alignment_the_automatic_mode_picks_raises_typeerror(
    fig_ax, helper, call, name
):
    """side='auto', avoid_overlap=True and x='auto' overwrite the alignment."""
    _fig, ax = fig_ax
    with pytest.raises(TypeError) as caught:
        call(ax)
    assert f"{helper}()" in str(caught.value)
    assert repr(name) in str(caught.value)


def test_alignment_survives_where_the_helper_does_not_pick_it(fig_ax):
    """With an explicit side / corner / end, ha= and va= are the caller's."""
    _fig, ax = fig_ax
    value = dm.annotate_value(
        ax, 0.5, 0.5, "v", side="above", ha="left", va="top"
    )
    corner = dm.annotate_corner(
        ax, "c", avoid_overlap=False, ha="right", va="bottom"
    )
    hline = dm.label_hline(ax, 0.5, "h", x="auto", va="top")
    assert (value.get_ha(), value.get_va()) == ("left", "top")
    assert (corner.get_ha(), corner.get_va()) == ("right", "bottom")
    assert hline.get_va() == "top"


@pytest.mark.parametrize("helper", sorted(_CALLS))
@pytest.mark.parametrize("name", ["fmt", "bogus_kwarg"])
def test_unknown_name_raises_attributeerror_naming_the_helper(
    fig_ax, helper, name
):
    """The exception kind matplotlib already raised, now saying which call."""
    fig, ax = fig_ax
    with pytest.raises(AttributeError) as caught:
        _CALLS[helper](fig, ax, **{name: "whatever"})
    message = str(caught.value)
    assert f"{helper}()" in message
    assert repr(name) in message


@pytest.mark.parametrize(
    ("helper", "fix"),
    [
        ("annotate_value", "finished text"),
        ("annotate_corner", "finished text"),
        ("label_hline", "finished text"),
        ("label_line_ends", "label="),
        ("add_note", "finished text"),
    ],
)
def test_fmt_points_at_the_real_route(fig_ax, helper, fix):
    """``fmt`` is what agents reach for; the message names what works."""
    fig, ax = fig_ax
    with pytest.raises(AttributeError, match=fix):
        _CALLS[helper](fig, ax, fmt="{:.1f}")


def test_loc_is_a_parameter_of_annotate_corner_not_a_rejected_kwarg(fig_ax):
    """``loc`` is annotate_corner's own argument and keeps working."""
    _fig, ax = fig_ax
    label = dm.annotate_corner(ax, "c", loc="lower right", avoid_overlap=False)
    assert (label.get_ha(), label.get_va()) == ("right", "bottom")


@pytest.mark.parametrize("helper", sorted(_CALLS))
def test_text_properties_still_reach_the_artist(fig_ax, helper):
    """The over-blocking guard: ordinary Text properties pass and apply."""
    fig, ax = fig_ax
    label = _CALLS[helper](
        fig, ax, color="#123456", rotation=15, fontstyle="italic", alpha=0.5
    )
    assert mcolors.to_hex(label.get_color()) == "#123456"
    assert label.get_rotation() == pytest.approx(15)
    assert label.get_fontstyle() == "italic"
    assert label.get_alpha() == 0.5


@pytest.mark.parametrize(
    "helper",
    ["annotate_value", "annotate_corner", "label_hline", "label_line_ends"],
)
def test_annotate_arguments_still_reach_the_annotation(fig_ax, helper):
    """``arrowprops`` / ``annotation_clip`` are ``ax.annotate`` arguments."""
    fig, ax = fig_ax
    label = _CALLS[helper](
        fig, ax, arrowprops={"arrowstyle": "->"}, annotation_clip=True
    )
    assert label.arrow_patch is not None
    assert label.get_annotation_clip() is True


def test_add_note_keeps_fontdict_transform_and_position(fig_ax):
    """``fig.text`` arguments and the note's own placement stay usable."""
    fig, ax = fig_ax
    note = dm.add_note(
        fig,
        "n",
        fontdict={"color": "#654321"},
        transform=ax.transAxes,
        position=(0.3, 0.2),
    )
    assert mcolors.to_hex(note.get_color()) == "#654321"
    assert note.get_transform() is ax.transAxes
    assert note.get_position() == (0.3, 0.2)


def test_short_alignment_and_size_alias_where_the_helper_allows_them(fig_ax):
    """label_line_ends sets no font size, so ``size`` is the caller's."""
    fig, ax = fig_ax
    label = dm.label_line_ends(ax, size=13, ha="right", va="top")[0]
    note = dm.add_note(fig, "n", ha="right", va="top")
    assert label.get_fontsize() == 13
    assert (label.get_ha(), label.get_va()) == ("right", "top")
    assert (note.get_ha(), note.get_va()) == ("right", "top")
