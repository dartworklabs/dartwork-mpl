"""What the library changed that nobody asked for, one line each.

A slice that changes a figure, rcParams or a file on its own (turns tick
labels, hides a value label, drops a timestamp) writes one INFO line on its
logger, ``dartwork_mpl.<slice>``, where it does so: what it did, to what,
why, and what to try. The lines print on stderr by default, because an
agent only learns what happened from what it can read; :func:`quiet` turns
them off and :func:`verbose` on again. A line is formatted only when its
logger is enabled.

What importing the package does (registering fonts and colours) is the
same on every run and is written at DEBUG, which is not printed.
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from matplotlib.axes import Axes

__all__ = ["axes_name", "quiet", "verbose"]

ROOT = "dartwork_mpl"
PREFIX = "dartwork-mpl: "


class _Stderr(logging.Handler):
    """Write to the ``sys.stderr`` of the moment (a test may swap it)."""

    def emit(self, record: logging.LogRecord) -> None:
        """One line on stderr."""
        try:
            sys.stderr.write(self.format(record) + "\n")
        except (OSError, ValueError):  # a closed stream: logging reports it
            self.handleError(record)


class _Line(logging.Formatter):
    """``dartwork-mpl: <slice>: <message>``."""

    def format(self, record: logging.LogRecord) -> str:
        """The record's message after the prefix and its slice's name."""
        where = record.name.removeprefix(ROOT + ".")
        return f"{PREFIX}{where}: {record.getMessage()}"


HANDLER = _Stderr()
HANDLER.setFormatter(_Line())
HANDLER.set_name(ROOT)
LOG = logging.getLogger(ROOT)
# Once per process: a test runner may import the package under a second name.
if ROOT not in {handler.get_name() for handler in LOG.handlers}:
    LOG.addHandler(HANDLER)
    LOG.setLevel(logging.INFO)


def quiet() -> None:
    """Stop printing what dartwork-mpl changes on its own.

    By default every action the library takes that your code did not ask
    for by name (tick labels turned by ``dm.simple_layout``, a value label
    hidden for room, a legend moved, a preset replacing an rcParams edit)
    prints one line on stderr prefixed ``dartwork-mpl:``: what it did, to
    which Axes, why, and what to try. After this call they are not printed;
    :func:`verbose` prints them again.

    The lines are ``logging`` records at INFO on the ``dartwork_mpl``
    logger, so the standard API routes or filters them too.
    """
    LOG.setLevel(logging.WARNING)


def verbose() -> None:
    """Print what dartwork-mpl changes on its own again, after :func:`quiet`."""
    LOG.setLevel(logging.INFO)


def axes_name(ax: Axes) -> str:
    """``Axes 0 ("Revenue")``: its place among its figure's Axes, and its
    title when it has one."""
    fig = ax.get_figure(root=True)
    siblings = list(fig.axes) if fig is not None else []
    place = f"Axes {siblings.index(ax)}" if ax in siblings else "an Axes"
    titles = (
        ax.get_title("center"),
        ax.get_title("left"),
        ax.get_title("right"),
    )
    title = next((t for t in titles if t.strip()), None)
    return place if title is None else f'{place} ("{title}")'
