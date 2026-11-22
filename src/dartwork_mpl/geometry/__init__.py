"""Figure measurement that two or more slices share.

Platform code: it knows matplotlib's renderer and artist extents and nothing
about any capability, and it imports no slice. A calculation one slice alone
uses lives in that slice.

- :mod:`.model`: matplotlib's names for an Axes' titles as types;
- :mod:`.renderer`: a measurement renderer and the errors measuring raises;
- :mod:`.figure`: what a (Sub)Figure holds and its figure-level artists;
- :mod:`.axes`: an Axes' titles and drawn tick labels, its twins and shares;
- :mod:`.ink`: what an artist actually draws, where its clip lets it;
- :mod:`.data_ink`: a plot's data ink by key, and what a box meets.
"""

from .axes import (
    axes_titles,
    axis_of,
    drawn_tick_labels,
    draws_axis,
    in_view_tick_labels,
    label_side,
    projection,
    same_position_axes,
    shared_axes,
)
from .data_ink import DataInk, ToPx
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
    artist_shown,
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
from .model import CentreTitle, LeftTitle, RightTitle, TitleLoc
from .renderer import BBOX_ERRORS, canvas_renderer, get_renderer
from .text_anchors import follows_mark

__all__ = [
    "BBOX_ERRORS",
    "UNCLIPPED",
    "CentreTitle",
    "DataInk",
    "LeftTitle",
    "RightTitle",
    "TitleLoc",
    "ToPx",
    "artist_shown",
    "axes_titles",
    "axis_of",
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
    "follows_mark",
    "get_renderer",
    "holders_shown",
    "in_view_tick_labels",
    "iter_figure_level_extents",
    "label_side",
    "line_draws_markers",
    "line_draws_stroke",
    "marker_radius_pt",
    "panel_letters",
    "patch_inks",
    "projection",
    "record_panel_letters",
    "same_position_axes",
    "shared_axes",
    "text_inks",
    "within_clip_path",
]
