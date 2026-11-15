"""A box's four edges, and the figure edge a figure legend reserves.

Platform vocabulary: legend says which edge it sits outside of or holds,
layout keeps the margins clear of it; pure, no matplotlib import.
"""

from .model import EDGES, Bottom, Edge, Left, Reserve, Right, Top, edge_of

__all__ = [
    "EDGES",
    "Bottom",
    "Edge",
    "Left",
    "Reserve",
    "Right",
    "Top",
    "edge_of",
]
