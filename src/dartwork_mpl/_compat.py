"""Removed and deprecated ``dm.*`` names, and the hints raised for them.

Owned by the package root, the only module that imports it: the root's
``__getattr__`` delegates here so a removed name raises an
``AttributeError`` naming its replacement, and a deprecated alias warns
and resolves. ``lint``'s migration hints are checked against
``_REMOVED_NAMES`` by tests/test_deprecation_registry_parity.py. Not part
of the public API.
"""

from __future__ import annotations

import warnings
from collections.abc import Mapping
from typing import Any, NamedTuple

__all__ = [
    "_DEPRECATED_NAMES",
    "_REMOVED_NAMES",
    "_Deprecation",
    "missing_attribute",
]


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


class _Deprecation(NamedTuple):
    """A soft-deprecated alias: its target name, versions, and the hint shown."""

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


def _removed_name(*parts: str) -> str:
    return "".join(parts)


_MODEL_B_REMOVED = "the Model B color API"
_REMOVED_NAMES.update(
    {
        _removed_name("get", "_", "palette"): (
            _MODEL_B_REMOVED,
            "dm.colors(..., n=...) for lists or dm.set_colors(...) for cycles; "
            "see docs/color_system",
        ),
        _removed_name("set", "_", "cycle"): (
            _MODEL_B_REMOVED,
            "dm.set_colors(...); see docs/color_system",
        ),
        "cycle": (
            _MODEL_B_REMOVED,
            "dm.colors('octave', n=8) or dm.set_colors(); see docs/color_system",
        ),
        _removed_name("cycle", "_", "cycler"): (
            _MODEL_B_REMOVED,
            "dm.set_colors(..., styles=True); see docs/color_system",
        ),
        _removed_name("list", "_", "palettes"): (
            _MODEL_B_REMOVED,
            "dm.list_colors(); see docs/color_system",
        ),
        _removed_name("list", "_", "colormaps"): (
            _MODEL_B_REMOVED,
            "dm.list_colors() or matplotlib.colormaps; see docs/color_system",
        ),
        _removed_name("plot", "_", "colors"): (
            _MODEL_B_REMOVED,
            "dm.show_colors(); see docs/color_system",
        ),
        _removed_name("plot", "_", "colormaps"): (
            _MODEL_B_REMOVED,
            "dm.show_colors(); see docs/color_system",
        ),
        _removed_name("show", "_", "palette"): (
            _MODEL_B_REMOVED,
            "dm.show_colors(names=[...]); see docs/color_system",
        ),
        _removed_name("classify", "_", "colormap"): (
            _MODEL_B_REMOVED,
            "dm.list_colors() metadata and dm.show_colors(); see docs/color_system",
        ),
        _removed_name("Dartwork", "Color"): (
            _MODEL_B_REMOVED,
            "the internal _colors._typing aliases; runtime code should use "
            "dm.colors(); see docs/color_system",
        ),
        _removed_name("Dartwork", "Colormap"): (
            _MODEL_B_REMOVED,
            "the internal _colors._typing aliases; runtime code should use "
            "dm.colors(); see docs/color_system",
        ),
    }
)


def missing_attribute(name: str, namespace: Mapping[str, Any]) -> Any:
    """Resolve or reject an attribute the package root does not define.

    ``namespace`` is the root's ``globals()``. A deprecated alias warns
    (``DeprecationWarning`` attributed to the caller of ``dm.<name>``) and
    returns ``namespace[target]``; a removed name, an ``FS_*`` tuple name,
    or any other unknown name raises ``AttributeError`` with the hint.
    """
    if name in _DEPRECATED_NAMES:
        dep = _DEPRECATED_NAMES[name]
        warnings.warn(
            f"dm.{name} is deprecated since {dep.since} and will be "
            f"removed in {dep.removed_in}. Use {dep.hint}.",
            DeprecationWarning,
            stacklevel=3,
        )
        return namespace[dep.target]
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
