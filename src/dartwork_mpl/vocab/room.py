"""The room a column of text keeps from what it stands beside.

In em of the column's type. ``near`` is where the column is set, ``far``
the distance past which it reads as floating rather than belonging.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Room:
    """The distance a column is set at, and the one past which it floats."""

    near: float
    far: float


#: Beside marks or a plot's edge: about what tick labels keep from their
#: axis. In the one-shot sweep of 2026-11-23 the columns nobody minded sat
#: up to 1.5 em from their plot, the ones called loose from 2 em.
BESIDE_PLOT = Room(near=1.0, far=1.6)

#: Beside another text (the column before it, tick labels): under 1 em two
#: texts on a row read as one phrase, so columns stand further apart. The
#: gutters nobody minded were up to 2.4 em, the ones called a little wide
#: from 2.5 em.
BESIDE_TEXT = Room(near=1.5, far=2.5)
