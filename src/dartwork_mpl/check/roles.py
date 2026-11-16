"""What a text is in its figure: a title, an axis label, a tick label ...

Each role says whether the user placed it (``free``) and whether it is a
tick label (``tick``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class Title:
    """``ax.set_title``: one of an Axes' titles."""

    word: ClassVar[str] = "title"
    free: ClassVar[bool] = False
    tick: ClassVar[bool] = False

    def __str__(self) -> str:
        """The words a finding names it by."""
        return self.word


@dataclass(frozen=True)
class AxisLabel:
    """An x or y axis label."""

    word: ClassVar[str] = "axis label"
    free: ClassVar[bool] = False
    tick: ClassVar[bool] = False

    def __str__(self) -> str:
        """The words a finding names it by."""
        return self.word


@dataclass(frozen=True)
class TickLabel:
    """A tick label."""

    word: ClassVar[str] = "tick label"
    free: ClassVar[bool] = False
    tick: ClassVar[bool] = True

    def __str__(self) -> str:
        """The words a finding names it by."""
        return self.word


@dataclass(frozen=True)
class FreeText:
    """A text the user placed: ``ax.text``, an annotation, a value."""

    word: ClassVar[str] = "text"
    free: ClassVar[bool] = True
    tick: ClassVar[bool] = False

    def __str__(self) -> str:
        """The words a finding names it by."""
        return self.word


@dataclass(frozen=True)
class PanelLetter:
    """A panel letter (``dm.label_axes``)."""

    word: ClassVar[str] = "panel letter"
    free: ClassVar[bool] = False
    tick: ClassVar[bool] = False

    def __str__(self) -> str:
        """The words a finding names it by."""
        return self.word


@dataclass(frozen=True)
class FigureText:
    """A text judged only against the canvas: a suptitle, ``fig.text``, a
    legend entry."""

    word: ClassVar[str] = "figure text"
    free: ClassVar[bool] = False
    tick: ClassVar[bool] = False

    def __str__(self) -> str:
        """The words a finding names it by."""
        return self.word


#: What a text is in its figure. ``free``: a text the user placed;
#: ``tick``: a tick label.
Role = Title | AxisLabel | TickLabel | FreeText | PanelLetter | FigureText
