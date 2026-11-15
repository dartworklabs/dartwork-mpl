"""Figure measurement that two or more slices share.

Platform code: it knows matplotlib's renderer and artist extents and nothing
about any capability, and it imports no slice. A calculation one slice alone
uses lives in that slice.

- :mod:`.model`: an Axes' two axes (:data:`Which`) as types;
- :mod:`.renderer`: a measurement renderer and the errors measuring raises;
- :mod:`.figure`: what a (Sub)Figure holds and its figure-level artists;
- :mod:`.axes`: an Axes' titles and drawn tick labels, its twins and shares;
- :mod:`.ink`: what an artist actually draws, where its clip lets it.
"""

from .axes import (
    axes_titles,
    axis_of,
    drawn_tick_labels,
    draws_axis,
    is_3d,
    is_rectilinear,
    same_position_axes,
    shared_axes,
)
from .figure import (
    drawn_in_tree,
    figure_axes,
    figure_legends,
    holders_shown,
    iter_figure_level_extents,
    panel_letters,
    record_panel_letters,
)
from .ink import (
    UNCLIPPED,
    clip_path_px,
    clip_region,
    cut_to_clip,
    discs_meet,
    drawn_collection_outlines,
    drawn_ink_meets,
    drawn_patch_box,
    drawn_scatter_discs,
    line_draws_markers,
    line_draws_stroke,
    marker_radius_pt,
    patch_inks,
    text_inks,
    within_clip_path,
)
from .model import (
    Letter,
    Letters,
    Which,
    X,
    Y,
    bars_along,
    parse_axes,
    parse_which,
    which,
)
from .renderer import BBOX_ERRORS, canvas_renderer, get_renderer

__all__ = [
    "BBOX_ERRORS",
    "UNCLIPPED",
    "Letter",
    "Letters",
    "Which",
    "X",
    "Y",
    "axes_titles",
    "axis_of",
    "bars_along",
    "canvas_renderer",
    "clip_path_px",
    "clip_region",
    "cut_to_clip",
    "discs_meet",
    "drawn_collection_outlines",
    "drawn_in_tree",
    "drawn_ink_meets",
    "drawn_patch_box",
    "drawn_scatter_discs",
    "drawn_tick_labels",
    "draws_axis",
    "figure_axes",
    "figure_legends",
    "get_renderer",
    "holders_shown",
    "is_3d",
    "is_rectilinear",
    "iter_figure_level_extents",
    "line_draws_markers",
    "line_draws_stroke",
    "marker_radius_pt",
    "panel_letters",
    "parse_axes",
    "parse_which",
    "patch_inks",
    "record_panel_letters",
    "same_position_axes",
    "shared_axes",
    "text_inks",
    "which",
    "within_clip_path",
]
