"""The font slice's types: matplotlib's font table as the decisions see it.

Matplotlib keeps one ``FontEntry`` per (file, family name) in
``fontManager.ttflist`` and resolves a request by scoring every entry. The
decisions here only reorder that table and correct a weight, so a
:class:`Face` keeps just what they read: the file's name, the family, the
weight and whether the file ships with dartwork-mpl.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Weight:
    """A font weight as matplotlib stores it: a number or a name."""

    value: int | str


@dataclass(frozen=True)
class Face:
    """One entry of matplotlib's font table."""

    file: str  # file name, no directory
    family: str
    weight: Weight
    bundled: bool


@dataclass(frozen=True)
class Table:
    """The font table after the bundled files were added."""

    faces: tuple[Face, ...]

    def single_weight_families(self) -> frozenset[str]:
        """Bundled family names that ship exactly one file."""
        files: dict[str, set[str]] = {}
        for face in self.faces:
            if face.bundled:
                files.setdefault(face.family, set()).add(face.file)
        return frozenset(name for name, f in files.items() if len(f) == 1)


@dataclass(frozen=True)
class Plan:
    """The table to install: positions into ``Table.faces`` in their new
    order, each with the weight it should carry."""

    order: tuple[int, ...]
    weights: tuple[Weight, ...]


@dataclass(frozen=True)
class WeightMiss:
    """Matplotlib's notice that a family lacks the requested weight."""

    family: str
    weight: Weight


@dataclass(frozen=True)
class Expected:
    """Where a weight miss is by design: bundled families that ship one
    weight, and matplotlib's math fonts looked up at the preset weight."""

    single_weight: frozenset[str]
    math: frozenset[str]
    preset_weight: Weight


def math_sets(fontset: str, fallback: str) -> set[str]:
    """The mathtext sets ``mathtext.fontset`` consults.

    A ``custom`` set falls back to ``mathtext.fallback``; the built-in sets
    (Computer Modern included) fall back to STIX.
    """
    sets = {fallback} if fontset == "custom" else {fontset, "stix"}
    if "cm" in sets:
        sets.add("stix")
    return sets
