"""Curated palette ownership retains historical lookup and serialization contracts."""

import inspect
import pickle
from typing import Literal, get_type_hints

import pytest

import dartwork_mpl as dm
import dartwork_mpl._colors as owner
import dartwork_mpl.helpers as helpers
import dartwork_mpl.helpers.colors as historical


def test_owner_aliases_and_metadata():
    """The new surface is the original callable, including historical pickle identity."""
    assert hasattr(owner, "make_palette")
    f = owner.make_palette
    assert (
        f is dm.make_palette is helpers.make_palette is historical.make_palette
    )
    assert f.__module__ == "dartwork_mpl.helpers.colors"
    assert f.__name__ == f.__qualname__ == "make_palette"
    assert f.__defaults__ == ("categorical", None)
    assert f.__annotations__ == {
        "n": "int",
        "kind": "Literal['categorical', 'sequential', 'diverging']",
        "highlight": "int | None",
        "return": "list[str]",
    }
    assert get_type_hints(f) == {
        "n": int,
        "kind": Literal["categorical", "sequential", "diverging"],
        "highlight": int | None,
        "return": list[str],
    }
    assert list(inspect.signature(f).parameters) == ["n", "kind", "highlight"]
    old = b"\x80\x04\x950\x00\x00\x00\x00\x00\x00\x00\x8c\x1bdartwork_mpl.helpers.colors\x94\x8c\x0cmake_palette\x94\x93\x94."
    assert pickle.loads(old) is f
    assert pickle.dumps(f, protocol=4) == old


@pytest.mark.parametrize(
    "n,kind,highlight,expected",
    [
        (
            9,
            "categorical",
            None,
            [
                "oc.blue5",
                "oc.red5",
                "oc.green5",
                "oc.orange5",
                "oc.purple5",
                "oc.teal5",
                "oc.pink5",
                "oc.yellow5",
                "oc.blue5",
            ],
        ),
        (
            5,
            "sequential",
            None,
            ["oc.blue3", "oc.blue4", "oc.blue5", "oc.blue6", "oc.blue7"],
        ),
        (
            6,
            "sequential",
            None,
            [
                "oc.blue1",
                "oc.blue2",
                "oc.blue3",
                "oc.blue4",
                "oc.blue5",
                "oc.blue6",
            ],
        ),
        (
            5,
            "diverging",
            None,
            ["oc.red6", "oc.red4", "oc.gray5", "oc.blue4", "oc.blue6"],
        ),
        (
            8,
            "diverging",
            None,
            [
                "oc.red7",
                "oc.red5",
                "oc.red3",
                "oc.gray5",
                "oc.blue3",
                "oc.blue5",
                "oc.blue7",
                "oc.red7",
            ],
        ),
        (3, "categorical", 0.5, ["oc.blue3", "oc.red3", "oc.green3"]),
        (3, "categorical", True, ["oc.blue3", "oc.red7", "oc.green3"]),
        (3, "categorical", 1.0, ["oc.blue3", "oc.red7", "oc.green3"]),
        (3, "categorical", -1, ["oc.blue5", "oc.red5", "oc.green5"]),
    ],
)
def test_boundary_and_highlight_contract(n, kind, highlight, expected):
    """Literal boundaries and native highlight quirks survive a mechanical move."""
    assert dm.make_palette(n, kind, highlight) == expected


@pytest.mark.parametrize("n", [0, 3])
def test_results_are_fresh_lists(n):
    """Empty and populated calls never share mutable result lists."""
    a = dm.make_palette(n)
    b = dm.make_palette(n)
    assert type(a) is list and a is not b
    a.append("mutated")
    assert dm.make_palette(n) == b


def test_kind_errors_precede_count_errors():
    """Unknown kinds win over bad counts; native count/highlight errors remain."""
    with pytest.raises(ValueError, match="Unknown kind"):
        dm.make_palette(-1, "bogus")
    with pytest.raises(ValueError, match="Unknown kind"):
        dm.make_palette(None, "bogus")
    with pytest.raises(ValueError, match="non-negative"):
        dm.make_palette(-1)
    with pytest.raises(TypeError):
        dm.make_palette(3.0)
    with pytest.raises(TypeError):
        dm.make_palette(3, highlight="1")
