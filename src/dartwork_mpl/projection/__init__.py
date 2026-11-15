"""An Axes' projection: plain 2D, 3D or curved.

Platform vocabulary: one pure type for what check, layout, labels, ticks and
geometry each ask of an Axes' projection, with no matplotlib import.
"""

from .model import Curved, Projection, Rectilinear, ThreeD, parse_projection

__all__ = ["Curved", "Projection", "Rectilinear", "ThreeD", "parse_projection"]
