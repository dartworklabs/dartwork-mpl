"""Unrequested preset overrides in the final ``plot.py``, counted from its AST.

A dartwork-mpl preset (``dm.style.use``) owns the global look. Counted as
overrides (secondary A/B metric; none of the 40 cases asks for one):

* ``rcparams``: ``rcParams[...] = ...``, ``rcParams.update/setdefault``,
  ``rc(...)``, ``rc_context(...)``, ``rcdefaults()``;
* ``font``: ``family=``/``fontfamily=``/``fontname=``/``fontproperties=``/
  ``math_fontfamily=`` arguments, ``FontProperties(...)``, ``set_family``/
  ``set_fontfamily``/``set_fontname``, ``fontManager.addfont``, and rc keys
  under ``font.`` or ``mathtext.``;
* ``facecolor``: figure/axes background: ``facecolor=`` on figure/axes
  creation and saving, ``set_facecolor`` on a figure, axes or their
  ``patch``, and rc keys ending in ``facecolor``;
* ``style``: non-dartwork style sheets and themes (``plt.style.use``,
  ``style.context``, seaborn ``set*``, ``xkcd``).

A site is one source line; ``total`` counts distinct lines with any kind
(kinds can share a line, e.g. ``rcParams["font.family"] = ...``).
"""

from __future__ import annotations

import ast
import re

KINDS = ("rcparams", "font", "facecolor", "style")
FONT_KWARGS = {
    "family",
    "fontfamily",
    "fontname",
    "fontproperties",
    "math_fontfamily",
}
FONT_METHODS = {"set_family", "set_fontfamily", "set_fontname", "addfont"}
FACE_CREATORS = {
    "figure",
    "subplots",
    "subplot",
    "subplot_mosaic",
    "add_subplot",
    "add_axes",
    "axes",
    "savefig",
    "save_formats",
    "save_and_show",
    "subfigures",
}
STYLE_CALLS = {
    "matplotlib.pyplot.style.use",
    "matplotlib.style.use",
    "matplotlib.pyplot.style.context",
    "matplotlib.style.context",
    "matplotlib.pyplot.xkcd",
    "seaborn.set",
    "seaborn.set_theme",
    "seaborn.set_style",
    "seaborn.set_context",
}
RC_CALLS = {"rc", "rc_context", "rcdefaults"}


def _aliases(tree: ast.AST) -> dict[str, str]:
    out: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                out[a.asname or a.name.split(".")[0]] = (
                    a.name if a.asname else a.name.split(".")[0]
                )
        elif isinstance(node, ast.ImportFrom) and node.module:
            for a in node.names:
                out[a.asname or a.name] = f"{node.module}.{a.name}"
    return out


def _dotted(node: ast.AST, aliases: dict[str, str]) -> str:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(aliases.get(node.id, node.id))
    elif isinstance(node, ast.Call):
        parts.append(_dotted(node.func, aliases) + "()")
    else:
        return ""
    return ".".join(reversed(parts))


def _rc_keys(node: ast.AST) -> list[str]:
    """String keys written by an rc call or subscript (best effort)."""
    return [
        n.value
        for n in ast.walk(node)
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
    ]


def _key_kinds(keys: list[str]) -> set[str]:
    kinds = set()
    for k in keys:
        if re.match(r"^(font|mathtext)(\.|$)", k):
            kinds.add("font")
        if k.endswith("facecolor"):
            kinds.add("facecolor")
    return kinds


def _receiver_is_canvas(node: ast.AST, aliases: dict[str, str]) -> bool:
    """``fig``/``ax``-named receivers, ``<x>.patch``, ``plt.gcf()``/``gca()``.

    A bare ``patch`` (e.g. a bar in ``ax.patches``) is an artist, not a canvas.
    """
    if isinstance(node, ast.Attribute) and node.attr == "patch":
        return True
    name = _dotted(node, aliases)
    last = name.rsplit(".", 1)[-1]
    return bool(
        re.fullmatch(
            r"(ax|axs|axes|fig|figure|subfig)\w*|\w*_(ax|axes|fig)\d*", last
        )
    ) or name.endswith(("gcf()", "gca()"))


def preset_overrides(source: str, allowed: tuple[str, ...] = ()) -> dict:
    """Override sites per kind (minus ``allowed`` kinds) and ``total`` distinct lines."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return {"error": f"SyntaxError: {exc}", "total": None}
    aliases = _aliases(tree)
    sites: dict[str, set[int]] = {k: set() for k in KINDS}

    def add(kinds, node):
        for k in kinds:
            sites[k].add(node.lineno)

    for node in ast.walk(tree):
        targets = (
            node.targets
            if isinstance(node, ast.Assign)
            else [node.target]
            if isinstance(node, ast.AugAssign)
            else []
        )
        for t in targets:
            if isinstance(t, ast.Subscript) and _dotted(
                t.value, aliases
            ).endswith("rcParams"):
                add({"rcparams", *_key_kinds(_rc_keys(t.slice))}, node)
        if not isinstance(node, ast.Call):
            continue
        name = _dotted(node.func, aliases)
        last = name.rsplit(".", 1)[-1]
        if name in STYLE_CALLS:
            add({"style"}, node)
        if (
            last in RC_CALLS and not name.startswith("dartwork_mpl")
        ) or re.search(r"rcParams\.(update|setdefault|__setitem__)$", name):
            add({"rcparams", *_key_kinds(_rc_keys(node))}, node)
        if last == "FontProperties" or last in FONT_METHODS:
            add({"font"}, node)
        if any(kw.arg in FONT_KWARGS for kw in node.keywords):
            add({"font"}, node)
        if last in FACE_CREATORS and any(
            kw.arg == "facecolor" for kw in node.keywords
        ):
            add({"facecolor"}, node)
        if (
            last == "set_facecolor"
            and isinstance(node.func, ast.Attribute)
            and _receiver_is_canvas(node.func.value, aliases)
        ):
            add({"facecolor"}, node)
    out = {k: (0 if k in allowed else len(v)) for k, v in sites.items()}
    lines = set().union(*(v for k, v in sites.items() if k not in allowed))
    out["total"] = len(lines)
    out["lines"] = sorted(lines)[:30]
    return out
