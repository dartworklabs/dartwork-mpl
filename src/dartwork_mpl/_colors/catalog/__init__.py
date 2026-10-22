"""Colour catalogue: the shipped palette, colormap and family values.

Responsibility: what the shipped catalogue *contains* — the generated
palette, cycles and 256-step colormaps (``_colors/_generated.py``, whose
path the build pins), the family taxonomy and the discrete colour forms.
Read-only values; registering them with matplotlib is the registry's job.

Surface: ``PALETTE``, ``CYCLES``, ``CMAPS_256``, ``FAMILIES``, ``Family``
(the union of ``SequentialFamily``, ``MultiHueFamily``, ``DivergingFamily``,
``CyclicFamily`` and ``QualitativeFamily``), ``FamilyKind``, the family-kind
name tuples (``SEQUENTIAL``, ``MULTI_HUE``,
``DIVERGING``, ``CYCLIC``, ``QUALITATIVE``), ``discrete_colors``,
``DIVERGING_CANONICALS`` and ``GENERATED_DIVERGING``.
"""

from .._generated import CMAPS_256, CYCLES, PALETTE
from ._discrete import (
    DIVERGING_CANONICALS,
    GENERATED_DIVERGING,
    discrete_colors,
)
from ._families import (
    CYCLIC,
    DIVERGING,
    FAMILIES,
    MULTI_HUE,
    QUALITATIVE,
    SEQUENTIAL,
    CyclicFamily,
    DivergingFamily,
    Family,
    FamilyKind,
    MultiHueFamily,
    QualitativeFamily,
    SequentialFamily,
)

__all__ = [
    "CMAPS_256",
    "CYCLES",
    "CYCLIC",
    "DIVERGING",
    "DIVERGING_CANONICALS",
    "FAMILIES",
    "GENERATED_DIVERGING",
    "MULTI_HUE",
    "PALETTE",
    "QUALITATIVE",
    "SEQUENTIAL",
    "CyclicFamily",
    "DivergingFamily",
    "Family",
    "FamilyKind",
    "MultiHueFamily",
    "QualitativeFamily",
    "SequentialFamily",
    "discrete_colors",
]
