"""The style slice's types, and the one place a preset request is parsed.

A preset is a named chain of style layers (``.mplstyle`` files under
``assets/``): ``report-kr`` is ``base`` + ``font-report`` + ``lang-kr``.
``dm.fs`` / ``dm.lw`` / ``dm.fw`` move a preset's base size, line width or
weight by steps, so a chart keeps its proportions when the preset changes.
"""

from __future__ import annotations

import difflib
import json
from collections.abc import Collection, Iterator, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import ClassVar, Protocol, runtime_checkable

#: Slides over a journal column (23.4 cm / 9 cm): the presentation presets
#: are the scientific ones with every point size times this.
SLIDE_SCALE = 2.6
KOREAN_LAYER = "lang-kr"
SLIDE_FAMILY = "presentation"

# ``rcParams['font.weight']`` may be a name; dartwork-mpl's reading of each.
WEIGHTS: Mapping[str, int] = {
    "ultralight": 100,
    "light": 200,
    "normal": 400,
    "regular": 400,
    "book": 400,
    "medium": 500,
    "roman": 500,
    "semibold": 600,
    "demibold": 600,
    "demi": 600,
    "bold": 700,
    "heavy": 800,
    "extra bold": 800,
    "black": 900,
}
NORMAL_WEIGHT = 400


@dataclass(frozen=True)
class Locale:
    """Which convention the role colours ``dc.pos`` / ``dc.neg`` follow.

    ``value`` is the colour slice's name for it.
    """

    value: str

    DEFAULT: ClassVar[Locale]
    KR: ClassVar[Locale]


Locale.DEFAULT = Locale("default")  # gains green, losses red
Locale.KR = Locale("kr")  # gains red, losses blue


@dataclass(frozen=True)
class Preset:
    """A preset's name and its style layers, applied in order."""

    name: str
    layers: tuple[str, ...]

    @property
    def family(self) -> str:
        """The name without its ``-kr`` suffix: ``presentation-kr`` ->
        ``presentation``."""
        return self.name.removesuffix("-kr")


@dataclass(frozen=True)
class Chain:
    """What ``dm.style.use`` applies: presets, their layers, the locale."""

    presets: tuple[Preset, ...]
    layers: tuple[str, ...]
    locale: Locale


def _closest(name: str, known: Collection[str]) -> str | None:
    match = difflib.get_close_matches(name.strip().lower(), known, 1, 0.5)
    return match[0] if match else None


@runtime_checkable
class Items(Protocol):
    """A value read for its items, in order (a list of preset names)."""

    def __iter__(self) -> Iterator[object]:
        """The items."""
        ...


@dataclass(frozen=True)
class Registry:
    """The shipped presets by name."""

    presets: Mapping[str, Preset]

    @classmethod
    def from_json(cls, text: str) -> Registry:
        """The registry ``presets.json`` describes (name -> layer list)."""
        raw: dict[str, list[str]] = json.loads(text)
        return cls(
            MappingProxyType(
                {name: Preset(name, tuple(raw[name])) for name in raw}
            )
        )

    def parse(self, request: object) -> tuple[Preset, ...]:
        """One preset name or a list of them, as presets.

        ``TypeError`` for a name that is not a string; ``KeyError`` naming the
        presets, with a did-you-mean, for an unknown one.
        """
        names: list[str] = []
        listed = (
            request
            if isinstance(request, Items) and not isinstance(request, str)
            else (request,)
        )
        for name in listed:
            if not isinstance(name, str):
                raise TypeError(
                    f"preset name must be str, got {type(name).__name__}"
                )
            names.append(name)
        return tuple(self.preset(name) for name in names)

    def preset(self, name: str) -> Preset:
        """The preset ``name``; ``KeyError`` with a did-you-mean if none."""
        if name in self.presets:
            return self.presets[name]
        known = sorted(self.presets)
        hint = _closest(name, known)
        raise KeyError(
            f"Preset {name!r} not found. Available presets: {known}."
            + (f" Did you mean {hint!r}?" if hint else "")
        )


def override_key(key: str, known: Collection[str]) -> str:
    """The rcParam a ``dm.style.use`` keyword names.

    ``font_size`` is ``font.size``; ``legend_title_fontsize`` is
    ``legend.title_fontsize``, whose own name has an underscore. An unknown
    key comes back unchanged so matplotlib names it in its error.
    """
    if key in known:
        return key
    dotted = key.replace("_", ".")
    if dotted in known:
        return dotted
    return next((rc for rc in known if rc.replace(".", "_") == key), key)


@dataclass(frozen=True)
class Points:
    """A size in PostScript points: a font size, a line width, a step."""

    pt: float


@dataclass(frozen=True)
class Steps:
    """How many steps ``dm.fs`` / ``dm.lw`` / ``dm.fw`` move from the base."""

    n: float


@dataclass(frozen=True)
class Weight:
    """A numeric font weight (100-900)."""

    value: int

    @classmethod
    def parse(cls, value: object) -> Weight:
        """``rcParams['font.weight']``: a number or a name (``"light"``)."""
        if isinstance(value, str):
            return cls(WEIGHTS.get(value.lower(), NORMAL_WEIGHT))
        if isinstance(value, int | float):
            return cls(int(value))
        raise TypeError(f"font.weight must be a number or a name: {value!r}")


@dataclass(frozen=True)
class Active:
    """The presets the last ``dm.style.use`` applied, and whether the live
    rcParams still hold them (a native ``plt.rcdefaults()`` drops them)."""

    presets: tuple[Preset, ...]
    in_force: bool
