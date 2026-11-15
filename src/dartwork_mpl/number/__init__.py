"""The scale a number prints in: the factor, prefix and suffix of a tick.

Platform vocabulary: ticks reports an axis's scale and labels prints bar
values in it; pure, no matplotlib import.
"""

from .model import AffixedZero, BareZero, ScaleZero, TickScale

__all__ = ["AffixedZero", "BareZero", "ScaleZero", "TickScale"]
