"""Removed ``dm.*`` names: the one registry of their migration metadata.

Every fact about a removed public name is written here once, and nowhere
else by hand:

- ``_REMOVED_NAMES`` / ``_REMOVED_PREFIXES``: the release that removed a
  name (or a family of names sharing a prefix) and what to use instead;
- ``_CODEMOD_HINTS``: the ``# TODO(dm-migrate):`` comments of
  ``dm.migrate_legacy_code``, each with the names it annotates and how
  they are used (referenced, called, subscripted, imported from);
- ``_LINT_RULES``: the anti-pattern catalog rules that report removed
  names, each with its names, its form and its published text.

Each consumer derives its own detection and wording from these records:

- the package root's ``__getattr__`` calls ``missing_attribute``;
- ``dartwork_mpl.lint.migrate`` compiles ``_CODEMOD_HINTS`` into the
  codemod's hint catalog;
- ``dartwork_mpl.lint.detect`` gives each ``_LINT_RULES`` entry the static
  detector of its form;
- ``scripts/generate_removed_name_rules.py`` writes ``_LINT_RULES`` into
  ``asset/prompt/02-anti-patterns.yaml`` at development time.

The installed package only reads this module and the shipped catalog; no
import or call writes a file. tests/contracts/test_deprecation_registry_parity.py
checks the structure and fails when the shipped catalog differs from what
the generator would write; tests/contracts/test_removed_names_golden.py
checks every consumer's output against a record of main.

The names are spelled out in full. Earlier copies wrote the 0.6.0 colour
names in pieces (``"get" "_" "palette"``, ``"\\u0070"`` escapes) so that a
plain-text search of the source for them found only real callers, a one-off
check of the 0.6.0 colour redesign. No test enforced it and the names were
already spelled out in tests, docs and the codemod; a search for callers
should exclude this file and the catalog. Only the catalog text of that
rule's pattern keeps the escaped spelling (``published_pattern``), because
the MCP ``dartwork-mpl://guide/anti-patterns`` resource serves the catalog's
bytes and they stay as main published them.

Deprecation policy: docs/development/api-stability.md. Migration paths:
docs/migration.md.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal, NamedTuple, NoReturn, TypeAlias

__all__ = [
    "_CODEMOD_HINTS",
    "_LINT_RULES",
    "_REMOVED_NAMES",
    "_REMOVED_PREFIXES",
    "CodemodForm",
    "CodemodHint",
    "LintForm",
    "LintRule",
    "Removal",
    "RemovedPrefix",
    "detection_pattern",
    "missing_attribute",
]

CodemodForm: TypeAlias = Literal["reference", "call", "subscript", "import"]
"""How the codemod finds a name: ``dm.<name>``, ``dm.<name>(``,
``dm.<name>[`` or ``from dm.<name> import ...``."""

LintForm: TypeAlias = Literal["reference", "call", "figsize"]
"""How a lint rule finds a name: ``dm.<name>``, ``dm.<name>(`` or a
``dm.<name>`` inside a Figure constructor's ``figsize=(...)`` tuple."""

_SUFFIX: Mapping[str, str] = MappingProxyType(
    {"reference": r"\b", "import": r"\b", "call": r"\s*\(", "subscript": r"\["}
)


class Removal(NamedTuple):
    """A removed name: the release that removed it and what to use instead."""

    removed_in: str
    replacement: str


class RemovedPrefix(NamedTuple):
    """A removed family of names that share a prefix, such as ``FS_*``."""

    what: str
    removed_in: str
    replacement: str


def detection_pattern(
    names: Sequence[str],
    form: CodemodForm | LintForm,
    *,
    under: str | None = None,
    capturing: bool = False,
) -> str:
    """The regular expression that finds ``names`` used in ``form``.

    A name ending in ``*`` is a prefix family (``FS_*``): its prefix and one
    or more capitals or underscores. ``under`` also accepts the name reached
    through that ``dm`` submodule path (``dm.<under>.<name>``). Several names
    form a non-capturing group unless ``capturing`` keeps the capturing group
    a published pattern already has.
    """
    tokens = [
        re.escape(name[:-1]) + "[A-Z_]+"
        if name.endswith("*")
        else re.escape(name)
        for name in names
    ]
    alternation = "|".join(tokens)
    if capturing:
        group = f"({alternation})"
    elif len(tokens) > 1:
        group = f"(?:{alternation})"
    else:
        group = alternation
    if form == "figsize":
        return rf"figsize\s*=\s*\([^)]*{group}"
    qualifier = "" if under is None else rf"(?:{re.escape(under)}\.)?"
    return rf"\bdm\.{qualifier}{group}{_SUFFIX[form]}"


@dataclass(frozen=True)
class CodemodHint:
    """One ``# TODO(dm-migrate):`` comment and the removed names it marks."""

    names: tuple[str, ...]
    form: CodemodForm
    text: str

    @property
    def pattern(self) -> str:
        """The regular expression the codemod searches a statement with."""
        return detection_pattern(self.names, self.form)


@dataclass(frozen=True)
class LintRule:
    """One anti-pattern catalog rule that reports removed names."""

    id: str
    names: tuple[str, ...]
    form: LintForm
    message: str
    why: str | None = None
    fix_suggestion: str | None = None
    under: str | None = None
    capturing: bool = False
    severity: Literal["critical"] = "critical"
    published_pattern: str | None = None
    """The YAML scalar the catalog prints for ``pattern``, when it is not the
    plain single-quoted form; it must parse to ``pattern``."""

    @property
    def pattern(self) -> str:
        """The catalog regex: the rule's documentation and fallback detector."""
        return detection_pattern(
            self.names, self.form, under=self.under, capturing=self.capturing
        )


# The 0.3 width tokens (SW/MW/TW/DW/WIDTHS), figure-size tuples (FS_*), the
# cm2in helper, the figure constructors (subplots/figure), the
# agent_utils/xplot module aliases and the 0.4.1 helper removals were
# removed across 0.4.x; the install_llm_txt installer family in 0.5;
# auto_layout in 0.5.4; the old colour vocabulary in 0.6.0.
_REMOVED_NAMES: Mapping[str, Removal] = MappingProxyType(
    {
        "SW": Removal(
            "0.4", "dm.col1 / dm.col2 / dm.cm(...) (e.g. width='9cm')"
        ),
        "MW": Removal("0.4", "dm.cm(...) (e.g. width='12cm')"),
        "TW": Removal("0.4", "dm.cm(...) (e.g. width='14.5cm')"),
        "DW": Removal("0.4", "dm.col2 / dm.cm(...) (e.g. width='17cm')"),
        "WIDTHS": Removal("0.4", "iterate explicit widths inline"),
        "cm2in": Removal(
            "0.4", "dm.cm(...) (returns a Length; e.g. dm.figsize('13cm', ...))"
        ),
        "subplots": Removal(
            "0.4",
            "plt.subplots(figsize=dm.figsize('<n>cm', '<aspect>')) with a "
            "separate dm.style.use(...)",
        ),
        "figure": Removal(
            "0.4",
            "plt.figure(figsize=dm.figsize('<n>cm', '<aspect>')) with a "
            "separate dm.style.use(...)",
        ),
        "agent_utils": Removal(
            "0.4", "dm.helpers (the agent_utils module was renamed to helpers)"
        ),
        "xplot": Removal(
            "0.4", "dm.templates (e.g. dm.templates.plot_diverging_bar)"
        ),
        "auto_layout": Removal(
            "0.5.4",
            "dm.simple_layout(fig, margin=...) (the legacy `padding` inches "
            "argument maps to `margin`; `max_iter`/`tolerance` are obsolete — "
            "simple_layout is direct-calc)",
        ),
        "install_llm_txt": Removal(
            "0.5",
            "dm.agent_doc_path(name) / dm.get_agent_doc(name), or the MCP "
            "dartwork-mpl://guide/* resources",
        ),
        "uninstall_llm_txt": Removal(
            "0.5",
            "dm.get_agent_doc(name) / the MCP resources (the corpus is read "
            "at runtime — there is no install to undo)",
        ),
        "INSTALL_TARGETS": Removal(
            "0.5",
            "dm.get_agent_doc(name) / the MCP resources (install targets no "
            "longer exist)",
        ),
        "style_spines": Removal(
            "0.4.1",
            "raw matplotlib spine calls (ax.spines[s].set_color(...) / "
            ".set_linewidth(...)); see docs/usage_guide/recipes.md",
        ),
        "add_grid": Removal(
            "0.4.1",
            "ax.grid(True, color='oc.gray3', alpha=0.3, linewidth=0.5) plus "
            "ax.set_axisbelow(True)",
        ),
        "minimal_axes": Removal(
            "0.4.1", "the minimal-axes recipe in docs/usage_guide/recipes.md"
        ),
        "auto_select_colors": Removal(
            "0.4.1",
            "dm.make_palette(n, kind=..., highlight=...) (arguments renamed: "
            "n_series→n, color_type→kind, highlight_index→highlight)",
        ),
        "named": Removal(
            "0.4.1",
            "dm.color(...) (accepts token names, hex, rgb()/oklch()/oklab())",
        ),
        "format_axis_percent": Removal(
            "0.4.1",
            "ax.yaxis.set_major_formatter(ticker.PercentFormatter(xmax=1.0)) "
            "(from matplotlib import ticker)",
        ),
        "format_axis_labels": Removal(
            "0.4.1",
            'ax.yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}")) '
            "(from matplotlib import ticker)",
        ),
        "format_axis_thousands": Removal(
            "0.4.1",
            "ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: "
            'f"{x:,.0f}")) (from matplotlib import ticker)',
        ),
        "add_frame": Removal(
            "0.4.1",
            "fig.patches.append(plt.Rectangle((0, 0), 1, 1, fill=False, "
            "transform=fig.transFigure))",
        ),
        "add_value_labels": Removal(
            "0.4.1",
            "dm.label_bars(ax) (values on bars); dm.annotate_value(ax, x, y, "
            "text) for a point or a line end",
        ),
        "set_xmargin": Removal(
            "0.4.1", "ax.set_xmargin(...) (the matplotlib Axes method)"
        ),
        "set_ymargin": Removal(
            "0.4.1", "ax.set_ymargin(...) (the matplotlib Axes method)"
        ),
        "hide_spines": Removal(
            "0.4.1",
            'for s in ("top", "right"): ax.spines[s].set_visible(False)',
        ),
        "hide_all_spines": Removal(
            "0.4.1", "for s in ax.spines: ax.spines[s].set_visible(False)"
        ),
        "show_only_spines": Removal(
            "0.4.1",
            'for s in ax.spines: ax.spines[s].set_visible(s in ("left", "bottom"))',
        ),
        "remove_grid": Removal("0.4.1", "ax.grid(False)"),
        "save_figure": Removal(
            "0.4.1",
            "fig.savefig(...) (or dm.save_formats(fig, path) for multi-format)",
        ),
        "create_figure_with_style": Removal(
            "0.4.1",
            'dm.style.use(style); plt.subplots(figsize=dm.figsize("<n>cm", '
            '"<aspect>"))',
        ),
        "get_palette": Removal(
            "0.6.0",
            "dm.colors(..., n=...) for lists or dm.set_colors(...) for cycles; "
            "see docs/color_system",
        ),
        "set_cycle": Removal(
            "0.6.0", "dm.set_colors(...); see docs/color_system"
        ),
        "cycle": Removal(
            "0.6.0",
            "dm.colors('octave', n=8) or dm.set_colors(); see docs/color_system",
        ),
        "cycle_cycler": Removal(
            "0.6.0", "dm.set_colors(..., styles=True); see docs/color_system"
        ),
        "list_palettes": Removal(
            "0.6.0", "dm.list_colors(); see docs/color_system"
        ),
        "list_colormaps": Removal(
            "0.6.0",
            "dm.list_colors() or matplotlib.colormaps; see docs/color_system",
        ),
        "plot_colors": Removal(
            "0.6.0", "dm.show_colors(); see docs/color_system"
        ),
        "plot_colormaps": Removal(
            "0.6.0", "dm.show_colors(); see docs/color_system"
        ),
        "show_palette": Removal(
            "0.6.0", "dm.show_colors(names=[...]); see docs/color_system"
        ),
        "classify_colormap": Removal(
            "0.6.0",
            "dm.list_colors() metadata and dm.show_colors(); see docs/color_system",
        ),
        "DartworkColor": Removal(
            "0.6.0",
            "documented color inputs such as color names, hex strings or RGB(A) tuples; "
            "see docs/color_system",
        ),
        "DartworkColormap": Removal(
            "0.6.0",
            "matplotlib.colors.Colormap for colormap objects; see docs/color_system",
        ),
        "set_palette_version": Removal(
            "0.6.0",
            "the current color catalog (no palette-version switch exists); "
            "see docs/color_system",
        ),
    }
)

# Removed families keyed by prefix; any ``dm.<prefix>...`` name matches.
_REMOVED_PREFIXES: Mapping[str, RemovedPrefix] = MappingProxyType(
    {
        "FS_": RemovedPrefix(
            "0.3 figure-size tuple",
            "0.4",
            "figsize=dm.figsize('<n>cm', '<aspect>')",
        )
    }
)

_MODEL_B_COLOR_NAMES = (
    "get_palette",
    "set_cycle",
    "cycle",
    "cycle_cycler",
    "list_palettes",
    "list_colormaps",
    "plot_colors",
    "plot_colormaps",
    "show_palette",
    "classify_colormap",
    "DartworkColor",
    "DartworkColormap",
)

_LEGACY_WRAPPER_NAMES = (
    "format_axis_percent",
    "format_axis_labels",
    "format_axis_thousands",
    "add_frame",
    "add_value_labels",
    "set_xmargin",
    "set_ymargin",
    "hide_spines",
    "hide_all_spines",
    "show_only_spines",
    "remove_grid",
    "save_figure",
    "create_figure_with_style",
)

# In comment order: when several hints mark one statement they are written
# in this order. ``dartwork_mpl.lint.migrate`` adds its two hints for
# native calls (a raw ``figsize=(w, h)`` tuple, ``tight_layout()``) right
# after the figure-constructor hint.
_CODEMOD_HINTS: tuple[CodemodHint, ...] = (
    CodemodHint(
        ("cm2in",),
        "reference",
        "dm.cm2in removed in 0.4 (it returned inches). Inside a figsize, "
        'use figsize=dm.figsize("<n>cm", "<aspect>"); elsewhere use '
        "dm.cm(<n>), which returns a Length, not a float.",
    ),
    CodemodHint(
        ("SW", "MW", "TW", "DW"),
        "reference",
        "dm.SW/MW/TW/DW removed in 0.4; use dm.col1, dm.col2, or dm.cm(<num>).",
    ),
    CodemodHint(
        ("FS_*",),
        "reference",
        "dm.FS_* tuples removed; use figsize=dm.figsize(<width>, <aspect>).",
    ),
    CodemodHint(
        ("WIDTHS",),
        "subscript",
        'dm.WIDTHS removed; pick a width string (e.g. "9cm") instead.',
    ),
    CodemodHint(
        ("subplots", "figure"),
        "call",
        "dm.subplots / dm.figure removed; use "
        "plt.subplots(figsize=dm.figsize(<width>, <aspect>)) "
        "(call dm.style.use(...) separately for styling).",
    ),
    CodemodHint(
        ("agent_utils",),
        "import",
        "dm.agent_utils removed; surfaces moved to dm.lint, "
        "dm.validate_figure, dm.helpers, etc.",
    ),
    CodemodHint(
        ("xplot",),
        "reference",
        "dm.xplot removed; templates now live in dm.templates / "
        "dm.helpers (see docs/migration.md).",
    ),
    CodemodHint(
        ("auto_layout",),
        "call",
        "dm.auto_layout removed in 0.5.4; use "
        "dm.simple_layout(fig, margin=...) (legacy padding maps to "
        "margin; max_iter/tolerance are obsolete).",
    ),
    CodemodHint(
        ("install_llm_txt", "uninstall_llm_txt", "INSTALL_TARGETS"),
        "reference",
        "install_llm_txt family removed in 0.5; use "
        "dm.get_agent_doc(name) / dm.agent_doc_path(name) or the MCP "
        "dartwork-mpl://guide/* resources.",
    ),
    CodemodHint(
        ("style_spines", "add_grid", "minimal_axes"),
        "reference",
        "dm.style_spines/add_grid/minimal_axes removed in 0.4.1; inline "
        "the raw matplotlib calls (see docs/usage_guide/recipes.md).",
    ),
    CodemodHint(
        ("format_axis_percent",),
        "call",
        "dm.format_axis_percent removed in 0.4.1; use "
        "ax.yaxis.set_major_formatter(ticker.PercentFormatter(xmax=1.0)) "
        "(from matplotlib import ticker).",
    ),
    CodemodHint(
        ("format_axis_labels",),
        "call",
        "dm.format_axis_labels removed in 0.4.1; use "
        'ax.yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}")) '
        "(from matplotlib import ticker).",
    ),
    CodemodHint(
        ("format_axis_thousands",),
        "call",
        "dm.format_axis_thousands removed in 0.4.1; use "
        'ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f"{x:,.0f}")) '
        "(from matplotlib import ticker).",
    ),
    CodemodHint(
        ("add_frame",),
        "call",
        "dm.add_frame removed in 0.4.1; use "
        "fig.patches.append(plt.Rectangle((0, 0), 1, 1, fill=False, "
        "transform=fig.transFigure)).",
    ),
    CodemodHint(
        ("add_value_labels",),
        "call",
        "dm.add_value_labels removed in 0.4.1; use dm.label_bars(ax) for "
        "values on bars, or dm.annotate_value(ax, x, y, text) for a point "
        "or a line end.",
    ),
    CodemodHint(
        ("set_xmargin",),
        "call",
        "dm.set_xmargin removed in 0.4.1; use ax.set_xmargin(...) "
        "(the matplotlib Axes method).",
    ),
    CodemodHint(
        ("set_ymargin",),
        "call",
        "dm.set_ymargin removed in 0.4.1; use ax.set_ymargin(...) "
        "(the matplotlib Axes method).",
    ),
    CodemodHint(
        ("hide_spines",),
        "call",
        "dm.hide_spines removed in 0.4.1; use "
        'for s in ("top", "right"): ax.spines[s].set_visible(False).',
    ),
    CodemodHint(
        ("hide_all_spines",),
        "call",
        "dm.hide_all_spines removed in 0.4.1; use "
        "for s in ax.spines: ax.spines[s].set_visible(False).",
    ),
    CodemodHint(
        ("show_only_spines",),
        "call",
        "dm.show_only_spines removed in 0.4.1; use "
        'for s in ax.spines: ax.spines[s].set_visible(s in ("left", "bottom")).',
    ),
    CodemodHint(
        ("remove_grid",),
        "call",
        "dm.remove_grid removed in 0.4.1; use ax.grid(False).",
    ),
    CodemodHint(
        ("save_figure",),
        "call",
        "dm.save_figure removed in 0.4.1; use fig.savefig(...) "
        "(or dm.save_formats(fig, path) for multi-format).",
    ),
    CodemodHint(
        ("create_figure_with_style",),
        "call",
        "dm.create_figure_with_style removed in 0.4.1; use "
        'dm.style.use(style); plt.subplots(figsize=dm.figsize("<n>cm", '
        '"<aspect>")).',
    ),
    CodemodHint(
        ("auto_select_colors",),
        "reference",
        "dm.auto_select_colors renamed in 0.4.1; use "
        "dm.make_palette(n, kind=..., highlight=...).",
    ),
    CodemodHint(
        ("named",),
        "call",
        "dm.named removed in 0.4.1; use dm.color(...) (accepts token "
        "names, hex, rgb()/oklch()/oklab()).",
    ),
    CodemodHint(
        _MODEL_B_COLOR_NAMES,
        "reference",
        "Version 0.6.0 removed this color API vocabulary; use dm.colors(...), "
        "dm.set_colors(...), dm.list_colors(), or dm.show_colors().",
    ),
    CodemodHint(
        ("set_palette_version",),
        "reference",
        "dm.set_palette_version was removed in 0.6.0; there is no palette-version "
        "switch. Review the current color catalog and docs/migration.md.",
    ),
)

# In catalog order. A message or why keeps its catalog line breaks.
_LINT_RULES: tuple[LintRule, ...] = (
    LintRule(
        "dm-subplots-removed",
        ("subplots", "figure"),
        "call",
        message=(
            "`dm.subplots` and `dm.figure` were REMOVED — accessing them now\n"
            "raises `AttributeError`. Use `plt.subplots(figsize=dm.figsize(...))`\n"
            "(or `plt.figure(figsize=dm.figsize(...))` for custom GridSpec).\n"
            "Apply style separately via `dm.style.use(...)`."
        ),
        why=(
            "Both functions were thin wrappers around `plt.subplots` / `plt.figure`\n"
            "that bundled style mutation, polymorphic `width=`, and a deny-list\n"
            "of legacy kwargs. Removing them keeps the matplotlib API native and\n"
            "reduces dartwork-mpl's surface to a single sizing helper."
        ),
        fix_suggestion='plt.subplots(figsize=dm.figsize("13cm", "standard"))',
    ),
    LintRule(
        "cm2in-figsize",
        ("cm2in",),
        "figsize",
        message=(
            "`figsize=(dm.cm2in(...), dm.cm2in(...))` is the legacy 0.3\n"
            "pattern: `dm.cm2in` itself raises `AttributeError`. Use\n"
            '`figsize=dm.figsize("<n>cm", "<aspect>")` instead.'
        ),
        fix_suggestion='figsize=dm.figsize("9cm", "standard")',
    ),
    LintRule(
        "dm-spines-removed",
        ("style_spines", "add_grid", "minimal_axes"),
        "call",
        message=(
            "`dm.style_spines`, `dm.add_grid`, and `dm.minimal_axes` were\n"
            "REMOVED in 0.4.1 (#156). They were thin matplotlib wrappers\n"
            "whose only contribution was curated default kwargs. Inline the\n"
            "raw matplotlib calls instead, or copy a snippet from\n"
            "`docs/usage_guide/recipes.md` (publication grid, minimal axes,\n"
            "thin gray spines)."
        ),
        fix_suggestion="see docs/usage_guide/recipes.md",
    ),
    LintRule(
        "dm-legacy-wrappers-removed",
        _LEGACY_WRAPPER_NAMES,
        "call",
        message=(
            "These legacy `dm.*` helpers were REMOVED in 0.4.1. They were\n"
            "thin formatter, spine, margin, and figure wrappers around native\n"
            "matplotlib calls. Inline the matplotlib API directly, or use the\n"
            "recipes in `docs/migration.md` / `docs/usage_guide/recipes.md`;\n"
            "dartwork-mpl keeps recipes and utilities rather than wrapper\n"
            "functions for simple matplotlib operations."
        ),
        fix_suggestion="see docs/migration.md",
    ),
    LintRule(
        "dm-auto-select-colors-renamed",
        ("auto_select_colors",),
        "call",
        message=(
            "`auto_select_colors` was renamed to `make_palette` in 0.4.1\n"
            "(#156) for vocabulary alignment with `make_offset`.\n"
            "Argument cleanup at the same time:\n"
            "`n_series` → `n`, `color_type` → `kind`,\n"
            "`highlight_index` → `highlight`."
        ),
        fix_suggestion='dm.make_palette(n, kind="categorical")',
        under="helpers.colors",
    ),
    LintRule(
        "dm-auto-layout-removed",
        ("auto_layout",),
        "call",
        message=(
            "`dm.auto_layout` was REMOVED in 0.5.4 — accessing it now raises\n"
            "`AttributeError`. Use `dm.simple_layout(fig, margin=...)`: the\n"
            "legacy `padding` inches argument maps to `margin`;\n"
            "`max_iter`/`tolerance` are obsolete (simple_layout is\n"
            "direct-calc)."
        ),
        fix_suggestion="dm.simple_layout(fig)",
    ),
    LintRule(
        "dm-named-renamed",
        ("named",),
        "call",
        message=(
            "`dm.named` was REMOVED in 0.4.1 — the replacement is\n"
            "`dm.color(...)`, a single string-parser entry point that accepts\n"
            "token names, hex, and `rgb()`/`oklch()`/`oklab()` functional\n"
            "strings."
        ),
        fix_suggestion='dm.color("oc.red5")',
    ),
    LintRule(
        "dm-model-b-color-api-removed",
        (*_MODEL_B_COLOR_NAMES, "set_palette_version"),
        "reference",
        message=(
            "Version 0.6.0 removed the old palette, cycle, diagnostic,\n"
            "and color-class vocabulary; there is no palette-version switch.\n"
            "For current color operations use `dm.colors(...)`,\n"
            "`dm.set_colors(...)`, `dm.list_colors()`, or `dm.show_colors()`."
        ),
        fix_suggestion='dm.colors("blue", n=5)',
        # The catalog bytes main published (MCP anti-patterns resource): a
        # double-quoted scalar with escaped letters. It parses to ``pattern``.
        published_pattern=(
            r'"\\bdm\\.(?:get_\u0070alette|set_\u0063ycle|cycle|'
            r"cycle_\u0063ycler|list_\u0070alettes|list_\u0063olormaps|"
            r"plot_\u0063olors|plot_\u0063olormaps|show_\u0070alette|"
            r"classify_\u0063olormap|Dartwork\u0043olor|Dartwork\u0043olormap|"
            r'set_palette_version)\\b"'
        ),
    ),
    LintRule(
        "dm-removed-namespaces",
        ("agent_utils", "xplot"),
        "reference",
        message=(
            "`dm.agent_utils` and `dm.xplot` were REMOVED in 0.4. The\n"
            "agent_utils surfaces moved to `dm.lint` / `dm.validate_figure` /\n"
            "`dm.helpers`; the xplot templates now live in `dm.templates`\n"
            "(e.g. `dm.templates.plot_diverging_bar`). See docs/migration.md."
        ),
        fix_suggestion="see docs/migration.md",
    ),
    LintRule(
        "dm-install-llm-txt-removed",
        ("install_llm_txt", "uninstall_llm_txt", "INSTALL_TARGETS"),
        "reference",
        message=(
            "The `install_llm_txt` installer family\n"
            "(`install_llm_txt`/`uninstall_llm_txt`/`INSTALL_TARGETS`) was\n"
            "REMOVED in 0.5. The agent-doc corpus is read at runtime — use\n"
            "`dm.get_agent_doc(name)` / `dm.agent_doc_path(name)`, or the MCP\n"
            "`dartwork-mpl://guide/*` resources."
        ),
        fix_suggestion='dm.get_agent_doc("llms")',
    ),
    LintRule(
        "deprecated-width-token",
        ("SW", "MW", "TW", "DW", "FS_*", "WIDTHS"),
        "reference",
        message=(
            "`dm.SW/MW/TW/DW/FS_*/WIDTHS` were REMOVED in 0.4.0 — accessing\n"
            "them now raises `AttributeError`. Use\n"
            '`figsize=dm.figsize("<n>cm", "<aspect>")`, or `dm.col1`/`dm.col2`\n'
            "for academic columns."
        ),
        # The published pattern has always used a capturing group;
        # load_rules() returns it to callers as ``detector_value``.
        capturing=True,
    ),
)


def missing_attribute(name: str) -> NoReturn:
    """Reject an attribute the package root does not define.

    A removed name, a name in a removed prefix family, or any other unknown
    name raises ``AttributeError``; a removed one names its release and
    replacement.
    """
    removal = _REMOVED_NAMES.get(name)
    if removal is not None:
        raise AttributeError(
            f"dm.{name} was removed in {removal.removed_in}. "
            f"Use {removal.replacement}. See docs/migration.md."
        )
    for prefix, family in _REMOVED_PREFIXES.items():
        if name.startswith(prefix):
            raise AttributeError(
                f"dm.{name} ({family.what}) was removed in "
                f"{family.removed_in}. Use {family.replacement}. "
                f"See docs/migration.md."
            )
    raise AttributeError(f"module 'dartwork_mpl' has no attribute '{name}'")
