"""``label_axes`` names itself and the fix when a keyword cannot be honoured."""

import matplotlib.pyplot as plt
import pytest

import dartwork_mpl as dm


@pytest.fixture
def axes():
    """Two panels on a throwaway figure."""
    fig, created = plt.subplots(1, 2)
    yield created
    plt.close(fig)


@pytest.fixture
def titled_axes():
    """Two panels whose left titles push the labels onto the title line."""
    fig, created = plt.subplots(1, 2)
    for ax in created:
        ax.set_title("Left title", loc="left")
    yield created
    plt.close(fig)


@pytest.mark.parametrize("name", ["fmt", "loc", "xy"])
def test_unsupported_keyword_keeps_attributeerror(axes, name):
    """The exception kind callers already catch does not change."""
    with pytest.raises(AttributeError):
        dm.label_axes(axes, **{name: "whatever"})


@pytest.mark.parametrize("name", ["fmt", "loc", "xy", "bogus_kwarg"])
def test_unsupported_keyword_names_the_helper_and_the_argument(axes, name):
    """A bare matplotlib property error never mentioned which call failed."""
    with pytest.raises(AttributeError) as caught:
        dm.label_axes(axes, **{name: "whatever"})
    message = str(caught.value)
    assert "label_axes" in message
    assert name in message


@pytest.mark.parametrize("name", ["fmt", "loc", "xy"])
def test_unsupported_keyword_lists_the_supported_arguments(axes, name):
    """The message carries the dedicated parameters and the native escape."""
    with pytest.raises(AttributeError) as caught:
        dm.label_axes(axes, **{name: "whatever"})
    message = str(caught.value)
    assert "labels" in message
    assert "ax.text" in message


def test_fmt_points_at_labels(axes):
    """``fmt`` wanted pre-formatted strings, which ``labels`` already takes."""
    with pytest.raises(AttributeError, match="labels="):
        dm.label_axes(axes, fmt="({})")


@pytest.mark.parametrize("name", ["loc", "xy"])
def test_placement_keywords_point_at_x_and_y(axes, name):
    """Both placement spellings route to the Axes-relative parameters."""
    with pytest.raises(AttributeError) as caught:
        dm.label_axes(axes, **{name: "upper left"})
    message = str(caught.value)
    assert "x=" in message and "y=" in message


@pytest.mark.parametrize(
    "name",
    ["ha", "va", "transform", "horizontalalignment", "verticalalignment"],
)
def test_keyword_the_helper_sets_is_a_typeerror(axes, name):
    """Collisions blamed ``Axes.text``; the full alignment names said nothing."""
    with pytest.raises(TypeError) as caught:
        dm.label_axes(axes, **{name: "left"})
    message = str(caught.value)
    assert "label_axes" in message
    assert name in message
    assert "ax.text" in message


@pytest.mark.parametrize(
    ("name", "reader"),
    [
        ("horizontalalignment", "get_horizontalalignment"),
        ("verticalalignment", "get_verticalalignment"),
    ],
)
def test_alignment_full_names_are_not_silently_dropped(axes, name, reader):
    """These were accepted and then overridden, so the request vanished."""
    with pytest.raises(TypeError):
        dm.label_axes(axes, **{name: "right"})
    assert all(not ax.texts for ax in axes)
    plain = dm.label_axes(axes)
    assert getattr(plain[0], reader)() in {"left", "bottom"}


@pytest.mark.parametrize("name", ["size", "weight"])
def test_dedicated_parameter_aliases_keep_the_matplotlib_message(axes, name):
    """matplotlib already names both aliases; that message is left alone."""
    with pytest.raises(TypeError, match="aliases of one another"):
        dm.label_axes(axes, **{name: "bold"})


def test_transform_points_at_x_and_y(axes):
    """Positions are Axes-relative, so ``transform`` has a dedicated route."""
    with pytest.raises(TypeError) as caught:
        dm.label_axes(axes, transform=None)
    message = str(caught.value)
    assert "x=" in message and "y=" in message


def test_rejection_leaves_no_partial_labels(axes):
    """A rejected call must not label the panels it already reached."""
    before = [len(ax.texts) for ax in axes]
    with pytest.raises(AttributeError):
        dm.label_axes(axes, fmt="({})")
    assert [len(ax.texts) for ax in axes] == before


@pytest.mark.parametrize(
    ("kwargs", "reader", "expected"),
    [
        ({"color": "red"}, "get_color", "red"),
        ({"c": "red"}, "get_color", "red"),
        ({"rotation": 90}, "get_rotation", 90),
        ({"fontstyle": "italic"}, "get_fontstyle", "italic"),
    ],
)
def test_accepted_text_properties_still_take_effect(
    axes, kwargs, reader, expected
):
    """Every keyword that reached the Text before keeps reaching it."""
    texts = dm.label_axes(axes, **kwargs)
    assert len(texts) == len(axes)
    assert getattr(texts[0], reader)() == expected


def test_fontdict_still_reaches_the_label(axes):
    """``fontdict`` is an ``Axes.text`` argument, not a ``Text`` setter."""
    texts = dm.label_axes(axes, fontdict={"color": "red"})
    assert [t.get_color() for t in texts] == ["red"] * len(axes)


def test_fontdict_with_a_title_keeps_its_native_error(titled_axes):
    """The title path uses ``ax.annotate``, which never took ``fontdict``."""
    with pytest.raises(AttributeError, match="Annotation"):
        dm.label_axes(titled_axes, fontdict={"color": "red"})


@pytest.mark.parametrize(
    ("kwargs", "reader", "expected"),
    [
        ({"fontsize": 20}, "get_fontsize", 20),
        ({"fontweight": "bold"}, "get_fontweight", "bold"),
    ],
)
def test_dedicated_parameters_still_take_effect(axes, kwargs, reader, expected):
    """The named parameters are not caught by the collision check."""
    texts = dm.label_axes(axes, **kwargs)
    assert getattr(texts[0], reader)() == expected


def test_plain_call_is_untouched(axes):
    """The default path still produces one label per panel."""
    texts = dm.label_axes(axes)
    assert [t.get_text() for t in texts] == ["a", "b"]
