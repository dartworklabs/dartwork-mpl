"""Reject, by name, the keywords an annotation helper cannot honour (#483).

Two rules, shared by every helper that forwards ``**kwargs`` to a matplotlib
text artist:

1. A property the helper sets on the label itself raises ``TypeError``: the
   caller's value would collide inside the matplotlib call or be overridden
   without a word.
2. A name the artist does not take raises ``AttributeError`` (the kind a bare
   matplotlib property error already had), after matplotlib's own alias
   resolution, letting through the arguments of the matplotlib call itself
   (``fontdict`` for ``Axes.text``, ``arrowprops`` for ``Axes.annotate``).

Each helper supplies its own wording; this module only decides.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass, field
from typing import Any

from matplotlib import cbook
from matplotlib.axes import Axes
from matplotlib.figure import FigureBase
from matplotlib.text import Text


def call_parameters(
    function: Callable[..., Any], positional: Collection[str]
) -> frozenset[str]:
    """Keyword arguments ``function`` takes itself, other than ``positional``.

    Taken from the signature rather than listed, so the check cannot drift
    from the matplotlib in use.
    """
    return frozenset(
        name
        for name, parameter in inspect.signature(function).parameters.items()
        if parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        and name not in {"self", *positional}
    )


#: ``Axes.text`` arguments that are not ``Text`` setters. Today: ``fontdict``.
AXES_TEXT_PARAMETERS = call_parameters(Axes.text, {"x", "y", "s"})

#: ``Figure.text`` arguments that are not ``Text`` setters. Today: ``fontdict``.
FIGURE_TEXT_PARAMETERS = call_parameters(FigureBase.text, {"x", "y", "s"})

#: ``Axes.annotate`` arguments that are not ``Annotation`` setters. Today:
#: ``xytext``, ``xycoords``, ``textcoords``, ``arrowprops``, ``annotation_clip``.
AXES_ANNOTATE_PARAMETERS = call_parameters(Axes.annotate, {"text", "xy"})


def kwarg_is_accepted(
    name: str, artist: type[Text], parameters: frozenset[str]
) -> bool:
    """Report whether a call building ``artist`` takes ``name``, resolving aliases."""
    if name in parameters:
        return True
    try:
        canonical = next(iter(cbook.normalize_kwargs({name: None}, artist)))
    except TypeError:
        return False
    return callable(getattr(artist, f"set_{canonical}", None))


def reject_unusable_kwargs(
    kwargs: Mapping[str, Any],
    *,
    owned: Collection[str],
    artist: type[Text],
    parameters: frozenset[str],
    owned_error: Callable[[str], str],
    unsupported_error: Callable[[str], str],
) -> None:
    """Raise for the first keyword in ``kwargs`` that cannot take effect.

    ``owned`` names the spellings the helper sets itself (``TypeError`` with
    ``owned_error(name)``); any other name ``artist`` does not take raises
    ``AttributeError`` with ``unsupported_error(name)``. Runs before any
    artist exists, so a rejected call leaves the figure untouched.
    """
    for name in kwargs:
        if name in owned:
            raise TypeError(owned_error(name))
        if not kwarg_is_accepted(name, artist, parameters):
            raise AttributeError(unsupported_error(name))


@dataclass(frozen=True)
class KwargGuard:
    """One helper's wording around :func:`reject_unusable_kwargs`.

    ``owned`` maps each spelling the helper sets itself to the sentence that
    names the right argument instead; ``hints`` does the same for names the
    artist does not take that agents reach for (``fmt``, ``loc``). ``takes``
    lists the helper's own arguments for the unsupported-name message, and
    ``escape`` names the plain matplotlib call to write instead.
    """

    helper: str
    artist: type[Text]
    parameters: frozenset[str]
    owned: Mapping[str, str]
    takes: str
    escape: str
    hints: Mapping[str, str] = field(default_factory=dict)

    def check(
        self,
        kwargs: Mapping[str, Any],
        situational: Mapping[str, str] | None = None,
    ) -> None:
        """Raise for ``kwargs`` this call cannot honour.

        ``situational`` adds properties the helper sets only in the mode this
        call chose (an alignment ``side="auto"`` picks), with their sentences.
        """
        owned = {**self.owned, **(situational or {})}
        reject_unusable_kwargs(
            kwargs,
            owned=owned,
            artist=self.artist,
            parameters=self.parameters,
            owned_error=lambda name: (
                f"{self.helper}() sets {name!r} on the label itself, so "
                f"passing {name!r} cannot take effect. {owned[name]} "
                f"{self.escape}"
            ),
            unsupported_error=lambda name: (
                f"{self.helper}() does not support {name!r}. It takes "
                f"{self.takes}. {self.hints.get(name, '')}{self.escape}"
            ),
        )


__all__ = [
    "AXES_ANNOTATE_PARAMETERS",
    "AXES_TEXT_PARAMETERS",
    "FIGURE_TEXT_PARAMETERS",
    "KwargGuard",
    "call_parameters",
    "kwarg_is_accepted",
    "reject_unusable_kwargs",
]
