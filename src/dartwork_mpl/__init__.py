"""dartwork-mpl: Enhanced styling and color utilities for Matplotlib.

This package provides enhanced styling, color management, and various
utility functions for Matplotlib visualizations.
"""

# ruff: noqa: E402

# Underscore-aliased so implementation imports don't leak into the
# public namespace (``dm.version`` / ``dm.Any`` /
# ``dm.PackageNotFoundError`` used to resolve).
import warnings as _warnings
from importlib.metadata import PackageNotFoundError as _PackageNotFoundError
from importlib.metadata import version as _metadata_version
from typing import Any as _Any
from typing import NamedTuple as _NamedTuple

# Derive the version from the installed distribution metadata so there
# is a single source of truth. For a built/released wheel this always
# equals ``pyproject.toml``. For an *editable* dev checkout the metadata
# is captured at install time, so a ``pyproject.toml`` version bump only
# shows up here after reinstalling (``uv sync`` / ``pip install -e .``).
# The fallback covers running from a source tree with no installed
# metadata at all.
try:
    __version__ = _metadata_version("dartwork-mpl")
except _PackageNotFoundError:  # pragma: no cover - source-tree fallback
    __version__ = "0.0.0+unknown"

# Import submodules so they are accessible under ``dm.<submodule>``
# (validate_fixes is the auto-fix companion to validate). F401 is
# silenced because ruff's "unused-import" check can't see
# attribute-style access at the package level.
from . import (  # noqa: F401
    cmap,
    font,
    helpers,
    icon,
    lint,
    templates,
    tokens,
    validate_fixes,
)

# Import bundled agent-onboarding helpers
from .agent import AGENT_DOCS, agent_doc_path, get_agent_doc

# Axes annotation
from .annotation import arrow_axis, label_axes

# Import color module exports
from .colors import (
    Color,
    DartworkColor,
    DartworkColormap,
    color,
    cspace,
    cycle,
    cycle_cycler,
    hex,
    oklab,
    oklch,
    rgb,
)

# Config (process-wide behaviour-toggle defaults)
from .config import Config, config

# Import asset-diagnostic visualization helpers.
from .diagnostics import (
    classify_colormap,
    plot_colormaps,
    plot_colors,
    plot_fonts,
)

# Explore
from .explore import list_colormaps, list_palettes, show_palette

# Formatting utilities
from .formatting import (
    format_axis_billions,
    format_axis_currency,
    format_axis_millions,
    format_axis_myriad,
    format_axis_si,
    rotate_tick_labels,
)

# Import icon module exports
from .icon import icon_font, icon_font_path, list_icon_fonts

# I/O
from .io import save_and_show, save_formats, show

# Layout
from .layout import (
    adopt_axis_label_font,
    get_bounding_box,
    simple_layout,
    tight_crop,
)

# Prompt utilities
from .prompt import (
    copy_prompt,
    find_template,
    get_prompt,
    list_prompts,
    prompt_path,
)

# --- Explicit imports from split modules (formerly in util.py) ---
# Scaling helpers
from .scale import dpi, fs, fw, lw

# Import style module exports
from .style import Style, list_styles, load_style_dict, style, style_path

# Extended plot functions (from templates, formerly xplot)
from .templates import plot_diverging_bar

# Unit helpers (0.4+: free-form width input)
from .units import (
    Length,
    cm,
    figsize,
    figsize_grid,
    inch,
    length,
    list_aspect_tokens,
    mm,
    pt,
)

# Color utilities
from .util import make_offset, mix_colors, pseudo_alpha, set_decimal

# Academic column-width sugar (0.4+).
col1: Length = cm(9)
col2: Length = cm(17)

# Public surfaces that are provisional -- shape may change in a minor
# release without a full deprecation cycle. Documented in
# docs/development/api-stability.md. Empty today because the interactive
# UI is a subpackage, not an advertised top-level ``dm.ui`` attribute.
EXPERIMENTAL: frozenset[str] = frozenset()

# High-level composition helpers (T2 in the AI-readiness roadmap).
# These wrap the lower-level primitives above so that AI agents and
# humans alike can reach the most useful workflow utilities through a
# single ``dm.<name>`` access path. The submodule namespace
# (``dm.helpers.<name>``) remains available as well.
from .helpers import (
    check_figure_quality,
    get_palette,
    make_palette,
    optimize_legend,
    set_cycle,
    suggest_chart_type,
    validate_data,
)

# Native lint + migration entry points (T4). The ``dm.lint`` name is
# the module itself (so ``dm.lint.lint(...)`` and
# ``dm.lint.migrate_legacy_code(...)`` already work). These aliases
# expose the two most common functions at the top level under
# unambiguous names so an offline agent can call ``dm.lint_code(...)``
# without spinning up the MCP server.
from .lint import lint as lint_code
from .lint import migrate_legacy_code

# Validation entry points
from .validate import validate_figure
from .validate_fixes import validate_with_fixes

# Define __all__ for explicit exports. The order is intentionally
# grouped by module/concern (Color → Icon → Style → …), not
# alphabetical, so that readers scanning the public surface see
# related names together. RUF022 is silenced for that reason.

__all__ = [  # noqa: RUF022
    # API stability markers
    "EXPERIMENTAL",
    # Config
    "Config",
    "config",
    # Color module
    "Color",
    "color",
    "cspace",
    "cycle",
    "cycle_cycler",
    "hex",
    "oklab",
    "oklch",
    "rgb",
    "DartworkColor",
    "DartworkColormap",
    # Icon module
    "icon_font",
    "icon_font_path",
    "list_icon_fonts",
    # Style module
    "Style",
    "list_styles",
    "load_style_dict",
    "style",
    "style_path",
    # Bundled agent-onboarding helpers
    "AGENT_DOCS",
    "agent_doc_path",
    "get_agent_doc",
    # Scaling helpers
    "dpi",
    "fs",
    "fw",
    "lw",
    # Layout
    "adopt_axis_label_font",
    "simple_layout",
    "tight_crop",
    "get_bounding_box",
    # Color utilities
    "mix_colors",
    "pseudo_alpha",
    # Units (0.4+)
    "cm",
    "inch",
    "mm",
    "pt",
    "length",
    "col1",
    "col2",
    "Length",
    "figsize",
    "figsize_grid",
    "list_aspect_tokens",
    "tokens",
    # Units (legacy helpers, kept for compatibility)
    "make_offset",
    # Formatting
    "set_decimal",
    "format_axis_millions",
    "format_axis_myriad",
    "format_axis_billions",
    "format_axis_currency",
    "format_axis_si",
    "rotate_tick_labels",
    # I/O
    "save_formats",
    "save_and_show",
    "show",
    # Explore
    "list_palettes",
    "list_colormaps",
    "show_palette",
    # Axes annotation
    "label_axes",
    "arrow_axis",
    # Prompt utilities
    "prompt_path",
    "get_prompt",
    "list_prompts",
    "copy_prompt",
    "find_template",
    # Validation
    "validate_figure",
    "validate_with_fixes",
    "validate_fixes",
    # Helpers (high-level composition utilities)
    "validate_data",
    "make_palette",
    "get_palette",
    "set_cycle",
    "optimize_legend",
    "suggest_chart_type",
    "check_figure_quality",
    # Native lint + migration (T4)
    "lint_code",
    "migrate_legacy_code",
    # Extended plots
    "plot_diverging_bar",
    # Asset diagnostics (from diagnostics)
    "plot_colormaps",
    "plot_colors",
    "plot_fonts",
    "classify_colormap",
]

# --- Monkey-patch matplotlib.axes.Axes.twinx to always show right spine ---
import matplotlib as mpl
import matplotlib.axes

# Reentrance guard: ``importlib.reload(dartwork_mpl)`` would otherwise
# capture the already-patched function as ``_original_twinx`` and recurse
# infinitely on the next ``ax.twinx()`` call. We tag the wrapper with
# ``__dm_patched__`` and skip re-patching when that marker is present.
if not getattr(matplotlib.axes.Axes.twinx, "__dm_patched__", False):
    _original_twinx = matplotlib.axes.Axes.twinx

    def _patched_twinx(
        self: matplotlib.axes.Axes, *args: _Any, **kwargs: _Any
    ) -> matplotlib.axes.Axes:
        ax2 = _original_twinx(self, *args, **kwargs)
        ax2.spines["right"].set_visible(True)
        ax2.spines["right"].set_linewidth(
            mpl.rcParams.get("axes.linewidth", 0.3)
        )
        return ax2

    _patched_twinx.__dm_patched__ = True  # type: ignore[attr-defined]
    matplotlib.axes.Axes.twinx = _patched_twinx  # type: ignore[method-assign,assignment]


# Eagerly register the bundled fonts on import so that
# ``plt.rcParams["font.family"] = "Inter"`` (or any bundled family) resolves
# immediately after ``import dartwork_mpl`` — matching the documented
# contract. This is a one-time ~70 ms cost; the same font-manager work would
# otherwise run on the first ``dm.style.use(...)`` anyway. Colours and
# colormaps stay lazy (registered on first access) because, unlike fonts,
# they are never addressed by a bare matplotlib rcParam string.
font.ensure_loaded()


# 0.3 width tokens (SW/MW/TW/DW/WIDTHS), figure-size tuples (FS_*), the
# cm2in helper, the figure constructors (subplots/figure), the
# agent_utils/xplot module aliases, and the 0.4.1 helper removals
# (style_spines/add_grid/minimal_axes/auto_select_colors/named) were
# removed across 0.4.x; the install_llm_txt installer
# (install_llm_txt/uninstall_llm_txt/INSTALL_TARGETS) was removed in
# 0.5; auto_layout was removed in 0.5.4. Accessing any of them now
# raises AttributeError. The ``__getattr__`` hook below turns those
# bare misses into an actionable message naming the version and the
# replacement API, instead of Python's default "module has no
# attribute" string. Future removals now pass through
# ``_DEPRECATED_NAMES`` for at least two minor releases (soft alias with
# warning) before landing here (hard removal); see
# docs/development/api-stability.md. Migration paths: see
# docs/migration.md.


class _Deprecation(_NamedTuple):
    target: str
    since: str
    removed_in: str
    hint: str


# Public names that still work but emit DeprecationWarning and alias to a
# replacement. Removals now go through here for >= 2 minor releases BEFORE
# moving to _REMOVED_NAMES. Ships empty -- infrastructure for future removals.
_DEPRECATED_NAMES: dict[str, _Deprecation] = {}

# Removed names → ``(version-removed, replacement-hint)``. Keyed by exact
# attribute name; the ``FS_*`` family is handled by the prefix branch.
_REMOVED_NAMES: dict[str, tuple[str, str]] = {
    "SW": ("0.4", "dm.col1 / dm.col2 / dm.cm(...) (e.g. width='9cm')"),
    "MW": ("0.4", "dm.cm(...) (e.g. width='12cm')"),
    "TW": ("0.4", "dm.cm(...) (e.g. width='14.5cm')"),
    "DW": ("0.4", "dm.col2 / dm.cm(...) (e.g. width='17cm')"),
    "WIDTHS": ("0.4", "iterate explicit widths inline"),
    "cm2in": (
        "0.4",
        "dm.cm(...) (returns a Length; e.g. dm.figsize('13cm', ...))",
    ),
    "subplots": (
        "0.4",
        "plt.subplots(figsize=dm.figsize('<n>cm', '<aspect>')) with a "
        "separate dm.style.use(...)",
    ),
    "figure": (
        "0.4",
        "plt.figure(figsize=dm.figsize('<n>cm', '<aspect>')) with a "
        "separate dm.style.use(...)",
    ),
    "agent_utils": (
        "0.4",
        "dm.helpers (the agent_utils module was renamed to helpers)",
    ),
    "xplot": ("0.4", "dm.templates (e.g. dm.templates.plot_diverging_bar)"),
    "auto_layout": (
        "0.5.4",
        "dm.simple_layout(fig, margin=...) (the legacy `padding` inches "
        "argument maps to `margin`; `max_iter`/`tolerance` are obsolete — "
        "simple_layout is direct-calc)",
    ),
    "install_llm_txt": (
        "0.5",
        "dm.agent_doc_path(name) / dm.get_agent_doc(name), or the MCP "
        "dartwork-mpl://guide/* resources",
    ),
    "uninstall_llm_txt": (
        "0.5",
        "dm.get_agent_doc(name) / the MCP resources (the corpus is read "
        "at runtime — there is no install to undo)",
    ),
    "INSTALL_TARGETS": (
        "0.5",
        "dm.get_agent_doc(name) / the MCP resources (install targets no "
        "longer exist)",
    ),
    # 0.4.1 helper removals (#156). These were previously covered only
    # by the lint engine, so hitting them at *runtime* gave a bare
    # "no attribute" error — closing that gap keeps the migration-hint
    # contract uniform across every removed public name.
    "style_spines": (
        "0.4.1",
        "raw matplotlib spine calls (ax.spines[s].set_color(...) / "
        ".set_linewidth(...)); see docs/usage_guide/recipes.md",
    ),
    "add_grid": (
        "0.4.1",
        "ax.grid(True, color='oc.gray3', alpha=0.3, linewidth=0.5) plus "
        "ax.set_axisbelow(True)",
    ),
    "minimal_axes": (
        "0.4.1",
        "the minimal-axes recipe in docs/usage_guide/recipes.md",
    ),
    "auto_select_colors": (
        "0.4.1",
        "dm.make_palette(n, kind=..., highlight=...) (arguments renamed: "
        "n_series→n, color_type→kind, highlight_index→highlight)",
    ),
    "named": (
        "0.4.1",
        "dm.color(...) (accepts token names, hex, rgb()/oklch()/oklab())",
    ),
    # 0.4.1 formatter / spine / margin / figure wrapper removals
    # (audit rounds 2-3).
    "format_axis_percent": (
        "0.4.1",
        "ax.yaxis.set_major_formatter(ticker.PercentFormatter(xmax=1.0)) "
        "(from matplotlib import ticker)",
    ),
    "format_axis_labels": (
        "0.4.1",
        'ax.yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}")) '
        "(from matplotlib import ticker)",
    ),
    "format_axis_thousands": (
        "0.4.1",
        "ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: "
        'f"{x:,.0f}")) (from matplotlib import ticker)',
    ),
    "add_frame": (
        "0.4.1",
        "fig.patches.append(plt.Rectangle((0, 0), 1, 1, fill=False, "
        "transform=fig.transFigure))",
    ),
    "add_value_labels": (
        "0.4.1",
        "a plain loop of ax.text(bar.get_x() + bar.get_width()/2, "
        'bar.get_height(), f"{bar.get_height():.0f}", ha="center", '
        'va="bottom")',
    ),
    "set_xmargin": (
        "0.4.1",
        "ax.set_xmargin(...) (the matplotlib Axes method)",
    ),
    "set_ymargin": (
        "0.4.1",
        "ax.set_ymargin(...) (the matplotlib Axes method)",
    ),
    "hide_spines": (
        "0.4.1",
        'for s in ("top", "right"): ax.spines[s].set_visible(False)',
    ),
    "hide_all_spines": (
        "0.4.1",
        "for s in ax.spines: ax.spines[s].set_visible(False)",
    ),
    "show_only_spines": (
        "0.4.1",
        'for s in ax.spines: ax.spines[s].set_visible(s in ("left", "bottom"))',
    ),
    "remove_grid": ("0.4.1", "ax.grid(False)"),
    "save_figure": (
        "0.4.1",
        "fig.savefig(...) (or dm.save_formats(fig, path) for multi-format)",
    ),
    "create_figure_with_style": (
        "0.4.1",
        'dm.style.use(style); plt.subplots(figsize=dm.figsize("<n>cm", '
        '"<aspect>"))',
    ),
}


def __getattr__(name: str) -> _Any:
    """Surface deprecation aliases and removed-name migration hints.

    Without this, ``dm.SW`` / ``dm.cm2in`` / ``dm.subplots`` /
    ``dm.install_llm_txt`` / ``dm.FS_SINGLE`` would raise Python's
    default ``AttributeError`` with no pointer to the replacement. See
    docs/migration.md for the full mapping.
    """
    if name in _DEPRECATED_NAMES:
        dep = _DEPRECATED_NAMES[name]
        _warnings.warn(
            f"dm.{name} is deprecated since {dep.since} and will be "
            f"removed in {dep.removed_in}. Use {dep.hint}.",
            DeprecationWarning,
            stacklevel=2,
        )
        return globals()[dep.target]
    if name in _REMOVED_NAMES:
        version, hint = _REMOVED_NAMES[name]
        raise AttributeError(
            f"dm.{name} was removed in {version}. Use {hint}. "
            f"See docs/migration.md."
        )
    if name.startswith("FS_"):
        raise AttributeError(
            f"dm.{name} (0.3 figure-size tuple) was removed in 0.4. Use "
            f"figsize=dm.figsize('<n>cm', '<aspect>'). See docs/migration.md."
        )
    raise AttributeError(f"module 'dartwork_mpl' has no attribute '{name}'")
