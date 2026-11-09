"""``dm.figsize_for(..., labels=names)``: a canvas the category names fit flat.

Without the names the canvas follows the counts only, so on a slide five
country names (``advanced/bar``) stood 0.38 em apart and the layout turned
them 30 degrees, costing the plot a quarter of its height. Given the names,
``figsize_for`` measures them at the preset's tick label font and takes the
smallest width of the preset's own table (report 9 / 12 / 14.5 / 17 cm,
slides 11.4 / 15.4 / 23.4 cm) at which neighbours stand half an em apart
flat; past the widest it keeps the widest and the layout's wrap and turn
take over. A call without names gets the canvas it got before.
"""

from __future__ import annotations

import inspect
from itertools import pairwise
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pytest

matplotlib.use("Agg")

import dartwork_mpl as dm
from dartwork_mpl._figure_geometry import drawn_tick_labels, get_renderer

CM = 2.54
COUNTRIES = ["Norway", "Iceland", "Sweden", "China", "Germany"]


@pytest.fixture(autouse=True)
def _own_rc():
    with matplotlib.rc_context():
        yield
    plt.close("all")


def _cm(size) -> tuple[float, float]:
    return (round(size[0] * CM, 2), round(size[1] * CM, 2))


def _template(name: str, preset: str):
    """A shipped template as written, in ``preset``, laid out by itself."""
    source = (
        Path(dm.__file__).parent / "asset/prompt/05-templates" / name
    ).read_text(encoding="utf-8")
    ends = ("dm.validate_with_fixes(fig)", "dm.save_formats(")
    cut = [i for e in ends if (i := source.find(e)) >= 0]
    source = source[: min(cut)] if cut else source
    source = source.replace(
        'dm.style.use("scientific")', f'dm.style.use("{preset}")'
    )
    namespace: dict = {}
    exec(compile(source, name, "exec"), namespace)
    fig = namespace["fig"]
    dm.simple_layout(fig)
    fig.canvas.draw()
    return fig


def _row(fig) -> tuple[set[float], bool, float]:
    """Turns, whether any label wrapped, and the smallest flat gap (em)
    between neighbouring bottom labels of the first Axes."""
    ax = fig.axes[0]
    renderer = get_renderer(fig)
    labels = [t for t in drawn_tick_labels(ax, "x") if t.get_text().strip()]
    boxes = sorted(
        (t.get_window_extent(renderer) for t in labels), key=lambda b: b.x0
    )
    em = labels[0].get_fontsize() * fig.dpi / 72
    gap = min(b.x0 - a.x1 for a, b in pairwise(boxes)) / em
    turns = {round(float(t.get_rotation()), 1) for t in labels}
    return turns, any("\n" in t.get_text() for t in labels), gap


def test_figsize_for_takes_the_names() -> None:
    assert "labels" in inspect.signature(dm.figsize_for).parameters


@pytest.mark.parametrize(
    "name",
    [
        "advanced/bar.py",
        "waterfall.py",
        "advanced/boxplot.py",
        "advanced/violin.py",
    ],
)
def test_templates_pass_their_names_and_draw_them_flat(name: str) -> None:
    """On a slide their names were turned or wrapped (0.38, 0.25, -0.78 and,
    turned by hand, -0.88 em apart flat); given the names, the canvas holds
    them flat, half an em apart."""
    turns, wrapped, gap = _row(_template(name, "presentation"))
    assert turns == {0.0}
    assert not wrapped
    assert gap >= 0.5


# The widest single-panel canvas each preset's names may take: a journal
# column stays a column.
WIDEST_CM = {"scientific": 9.0, "report": 17.0, "presentation": 23.4}
NAMED = [
    "advanced/bar.py",
    "waterfall.py",
    "advanced/boxplot.py",
    "advanced/violin.py",
    "advanced/waterfall.py",
]


@pytest.mark.parametrize("preset", ["scientific", "report", "presentation"])
@pytest.mark.parametrize("name", NAMED)
def test_named_templates_stand_flat_or_take_the_widest(
    name: str, preset: str
) -> None:
    """Every template that passes its names: flat half an em apart, or the
    widest canvas with the layout's own wrap or turn."""
    fig = _template(name, preset)
    turns, wrapped, gap = _row(fig)
    if turns == {0.0} and not wrapped:
        assert gap >= 0.5
    else:
        assert _cm(fig.get_size_inches())[0] == WIDEST_CM[preset]


def test_no_template_turns_its_names_by_hand() -> None:
    """The layout turns or wraps tick labels that would not clear; a
    template that turns them itself overrides it on every canvas
    (``advanced/violin`` 20 and ``advanced/waterfall`` 30 degrees did)."""
    import re

    root = Path(dm.__file__).parent / "asset/prompt/05-templates"
    by_hand = re.compile(
        r"set_[xy]tick(?:label)?s\([^)]*rotation|labelrotation|"
        r"xticks\([^)]*rotation|rotate_tick_labels\("
    )
    turned = [
        str(path.relative_to(root))
        for path in sorted(root.rglob("*.py"))
        if by_hand.search(path.read_text(encoding="utf-8"))
    ]
    assert turned == []
    for name in NAMED:
        assert "labels=" in (root / name).read_text(encoding="utf-8"), name


@pytest.mark.parametrize("preset", ["scientific", "report", "presentation"])
@pytest.mark.parametrize(
    ("kind", "n_points", "n_series", "expected"),
    [
        (
            "default",
            5,
            1,
            {"scientific": 9.0, "report": 9.0, "presentation": 15.4},
        ),
        (
            "default",
            3,
            1,
            {"scientific": 9.0, "report": 9.0, "presentation": 11.4},
        ),
        (
            "default",
            8,
            2,
            {"scientific": 9.0, "report": 12.0, "presentation": 23.4},
        ),
        (
            "grouped",
            4,
            3,
            {"scientific": 9.0, "report": 12.0, "presentation": 15.4},
        ),
        (
            "barh",
            5,
            1,
            {"scientific": 9.0, "report": 9.0, "presentation": 23.4},
        ),
    ],
)
def test_without_names_the_canvas_is_as_before(
    preset: str, kind: str, n_points: int, n_series: int, expected: dict
) -> None:
    dm.style.use(preset)
    size = dm.figsize_for(kind, n_points=n_points, n_series=n_series)
    assert _cm(size)[0] == expected[preset]


def _width(preset: str, names, kind: str = "default", **counts) -> float:
    dm.style.use(preset)
    counts.setdefault("n_points", len(names))
    counts.setdefault("n_series", 1)
    return _cm(dm.figsize_for(kind, labels=names, **counts))[0]


def test_names_that_fit_change_nothing() -> None:
    """Five short codes fit every preset's own width: the same canvas."""
    names = ["A", "B", "C", "D", "E"]
    for preset in ("scientific", "report", "presentation"):
        dm.style.use(preset)
        plain = dm.figsize_for(n_points=5, n_series=1)
        assert dm.figsize_for(n_points=5, n_series=1, labels=names) == plain


def test_long_names_take_the_next_width_of_the_table() -> None:
    assert _width("presentation", COUNTRIES) == 23.4
    assert _width("report", [f"{c} region" for c in COUNTRIES * 2]) in (
        14.5,
        17.0,
    )


def test_past_the_widest_width_the_widest_stays() -> None:
    names = [f"Very long category name number {i}" for i in range(12)]
    assert _width("presentation", names) == 23.4
    assert _width("report", names) == 17.0


def test_a_journal_column_stays_a_column() -> None:
    """``scientific`` sets one panel in one column, names or not."""
    names = [f"Very long category name number {i}" for i in range(12)]
    assert _width("scientific", names) == 9.0


@pytest.mark.parametrize("kind", ["barh", "compact", "matrix", "dense"])
def test_kinds_whose_width_is_not_the_x_positions_ignore_names(
    kind: str,
) -> None:
    names = [f"Very long category name number {i}" for i in range(12)]
    for preset in ("report", "presentation"):
        dm.style.use(preset)
        plain = dm.figsize_for(kind, n_points=12, n_series=1)
        assert (
            dm.figsize_for(kind, n_points=12, n_series=1, labels=names) == plain
        )


def test_the_same_names_give_the_same_canvas() -> None:
    first = _width("presentation", COUNTRIES)
    _width("report", COUNTRIES)  # another preset in between
    assert _width("presentation", COUNTRIES) == first


@pytest.mark.parametrize("preset", ["report", "presentation"])
def test_longer_or_more_names_never_narrow_the_canvas(preset: str) -> None:
    """No back and forth between widths as names grow, one letter at a
    time, or as names are added: the width only climbs."""
    widths = [
        _width(preset, [f"Name {'x' * k}{i}" for i in range(5)])
        for k in range(24)
    ]
    assert widths == sorted(widths)
    counts = [
        _width(preset, [f"Region {i}" for i in range(n)]) for n in range(2, 16)
    ]
    assert counts == sorted(counts)


def test_names_are_strings_or_turn_into_them() -> None:
    dm.style.use("presentation")
    numbers = dm.figsize_for(
        n_points=5, n_series=1, labels=[2019, 2020, 2021, 2022, 2023]
    )
    words = dm.figsize_for(
        n_points=5, n_series=1, labels=["2019", "2020", "2021", "2022", "2023"]
    )
    assert numbers == words
    with pytest.raises(TypeError, match="labels"):
        dm.figsize_for(n_points=5, labels="Norway")  # one string is not names


# ------------------------------------------------ what the names are given as
@pytest.mark.parametrize(
    "labels",
    [{"A", "B"}, {"A": 1, "B": 2}, {"A": 1, "B": 2}.keys(), 3, None.__class__],
    ids=["set", "dict", "dict-keys", "int", "type"],
)
def test_names_without_an_axis_order_are_refused_by_name(labels) -> None:
    """A set or a mapping has no axis order, so its neighbours are no
    neighbours; a number is no names at all. Each says ``labels``."""
    dm.style.use("report")
    with pytest.raises(TypeError, match="labels"):
        dm.figsize_for(n_points=2, n_series=1, labels=labels)


def test_ordered_names_are_taken_in_any_sequence() -> None:
    import numpy as np

    dm.style.use("presentation")
    names = ["Norway", "Iceland", "Sweden", "China", "Germany"]
    expected = dm.figsize_for(n_points=5, n_series=1, labels=names)
    given = [tuple(names), np.array(names), iter(names)]
    pandas = pytest.importorskip("pandas")
    given.append(pandas.Index(names))
    for labels in given:
        assert dm.figsize_for(n_points=5, n_series=1, labels=labels) == expected


# ------------------------------------- the names measure as the drawn labels
def _drawn_width_pt(name: str) -> float:
    """``name``'s width (pt) drawn as an x tick label under the active rc."""
    fig, ax = plt.subplots()
    ax.set_xticks([0], [name])
    fig.canvas.draw()
    box = ax.get_xticklabels()[0].get_window_extent(get_renderer(fig))
    return box.width * 72.0 / fig.dpi


def _measured_pt(name: str) -> float:
    from dartwork_mpl.style._canvas import _name_widths_pt

    measured = _name_widths_pt([name])
    assert measured is not None
    return measured[0][0]


@pytest.mark.parametrize(
    ("name", "rc"),
    [
        (r"Price \$100", {}),
        ("Price $100", {}),
        (r"Rate $x^2$ net", {}),
        ("Line one\nand a longer two", {}),
        (r"Rate $x^2$ net", {"text.parse_math": False}),
    ],
    ids=["escaped-dollar", "plain-dollar", "mathtext", "lines", "parse-off"],
)
@pytest.mark.parametrize("preset", ["report", "presentation"])
def test_a_name_measures_as_its_tick_label_draws(
    preset: str, name: str, rc: dict
) -> None:
    """The text a tick label draws: '\\$' is a dollar, '$...$' math unless
    ``text.parse_math`` is off, the widest of several lines."""
    dm.style.use(preset)
    with matplotlib.rc_context(rc):
        assert _measured_pt(name) == pytest.approx(
            _drawn_width_pt(name), abs=0.01
        )


def test_a_dollar_spelt_either_way_takes_the_same_canvas() -> None:
    """``'Price $100'`` and ``r'Price \\$100'`` draw alike, so they size
    alike (the escaped one took 12 cm, not 9)."""
    dm.style.use("report")
    plain = ["Price $100"] * 5
    escaped = [r"Price \$100"] * 5
    assert dm.figsize_for(
        n_points=5, n_series=1, labels=escaped
    ) == dm.figsize_for(n_points=5, n_series=1, labels=plain)


def _have_tex() -> bool:
    import shutil

    return all(shutil.which(tool) for tool in ("latex", "dvipng"))


TEX_NAMES = [rf"$\displaystyle x_{{{i}}}$ share" for i in range(5)]


def _sized(names: list[str]) -> tuple[float, float]:
    """``figsize_for`` for five positions named ``names``; failing to size
    them is a failure of the test, not an error in it."""
    try:
        return dm.figsize_for(n_points=5, n_series=1, labels=names)
    except ValueError as error:
        pytest.fail(f"figsize_for could not size {names[0]!r}: {error}")


@pytest.mark.skipif(not _have_tex(), reason="needs latex and dvipng")
def test_with_usetex_a_name_measures_as_tex_draws_it() -> None:
    """``text.usetex``: TeX lays the label out, so TeX measures it;
    ``\\displaystyle`` is TeX's alone and mathtext cannot read it."""
    dm.style.use("report")
    with matplotlib.rc_context({"text.usetex": True}):
        assert _sized(TEX_NAMES)
        assert _measured_pt(TEX_NAMES[0]) == pytest.approx(
            _drawn_width_pt(TEX_NAMES[0]), abs=0.01
        )


def test_names_nothing_can_measure_leave_the_canvas_as_without_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``text.usetex`` with no TeX to run: matplotlib cannot draw the labels
    either. ``figsize_for`` does not guess with another engine; it gives
    the canvas it gives without names."""
    dm.style.use("presentation")
    monkeypatch.setenv("PATH", "")
    names = [rf"$\displaystyle y_{{{i}}}$ unmeasured share" for i in range(5)]
    with matplotlib.rc_context({"text.usetex": True}):
        assert _sized(names) == dm.figsize_for(n_points=5, n_series=1)
