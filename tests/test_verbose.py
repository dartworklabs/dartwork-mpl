"""What the library changes on its own is said on stderr, unless ``dm.quiet()``."""

from __future__ import annotations

import logging
from collections.abc import Iterator

import matplotlib.pyplot as plt
import pytest
from matplotlib.figure import Figure

import dartwork_mpl as dm


@pytest.fixture(autouse=True)
def default_level() -> Iterator[None]:
    """Each test starts loud, as a fresh import is."""
    dm.verbose()
    yield
    dm.verbose()


def test_a_line_is_printed_once_with_its_slice(
    capsys: pytest.CaptureFixture[str],
) -> None:
    logging.getLogger("dartwork_mpl.layout").info("turned %s", "x labels")
    err = capsys.readouterr().err
    assert err.startswith("dartwork-mpl: layout: ")
    assert err.count("turned x labels") == 1


def test_quiet_stops_the_lines_and_verbose_brings_them_back(
    capsys: pytest.CaptureFixture[str],
) -> None:
    dm.quiet()
    logging.getLogger("dartwork_mpl.layout").info("turned %s", "x labels")
    assert capsys.readouterr().err == ""
    dm.verbose()
    logging.getLogger("dartwork_mpl.layout").info("turned %s", "x labels")
    assert "turned x labels" in capsys.readouterr().err


def crowded_numbers() -> Figure:
    """Eight long numbers as categories on a narrow axis: they turn."""
    fig, ax = plt.subplots(figsize=dm.figsize("8cm", "wide"))
    ax.bar([f"{n},000,000" for n in range(1, 9)], range(1, 9))
    ax.set_title("Revenue")
    return fig


def test_a_layout_that_turns_tick_labels_says_so(
    capsys: pytest.CaptureFixture[str],
) -> None:
    fig = crowded_numbers()
    dm.simple_layout(fig)
    plt.close(fig)
    err = capsys.readouterr().err
    assert "turned the x tick labels" in err
    assert '"Revenue"' in err


def test_a_quiet_layout_says_nothing(
    capsys: pytest.CaptureFixture[str],
) -> None:
    dm.quiet()
    fig = crowded_numbers()
    dm.simple_layout(fig)
    plt.close(fig)
    assert capsys.readouterr().err == ""


def test_an_edge_case_that_fires_is_said_once(
    capsys: pytest.CaptureFixture[str],
) -> None:
    fig, ax = plt.subplots()
    ax.bar(["a", "b"], [3, 4])
    ax.bar(["a", "b"], [2, 1], bottom=[3, 4])
    dm.label_bars(ax)
    dm.simple_layout(fig)
    plt.close(fig)
    assert capsys.readouterr().err.count("stacked-segments-totals") == 1
