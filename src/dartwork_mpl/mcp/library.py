"""The reading tools' shell: guidance, search and lookup over what the other slices ship.

Templates and guide pages come from the guide slice (``search``, ``read``,
``references``), presets from the style slice, colours from the colour
slice's ``list_colors`` / ``colors`` / ``color`` and rules from the lint
catalog. Nothing here is copied; every answer is read on demand.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from functools import cache
from importlib.metadata import version

import yaml

from .. import guide as guidance
from ..color import color, colors, list_colors
from ..style import load_style_dict
from ..style import presets as style_presets
from . import decide
from .model import (
    PRESET_PURPOSES,
    Entries,
    Entry,
    Kind,
    Lint,
    LintFinding,
    Query,
    words,
)

TOOLS = (
    "Tools: guide(topic) reads one page; search_reference(query, kind) finds"
    " templates, presets, colours and lint rules; get_reference(kind, id)"
    " returns one; lint(code) checks a script without running it; render(code)"
    " runs it once and returns the PNG, the check report and the bundle paths."
)


def topics() -> list[str]:
    """The guide page names ``guide(topic)`` accepts."""
    return [
        r.id.removeprefix("guide/")
        for r in guidance.references()
        if r.id.startswith("guide/") and r.id != "guide/skill"
    ]


def guide(topic: str | None) -> str:
    """The skill with a short header, or one reference page."""
    if topic is None or topic.strip() in {"", "skill"}:
        header = (
            f"dartwork-mpl {version('dartwork-mpl')}. Topics: {', '.join(topics())}."
            f" Presets: {', '.join(style_presets)}.\n{TOOLS}\n\n"
        )
        return header + guidance.read("guide/skill")
    return guidance.read("guide/" + topic.strip().removeprefix("guide/"))


def lint(code: str) -> Lint:
    """The guide slice's lint as the report's findings."""
    return tuple(
        LintFinding(f.rule_id, f.severity.value, f.line, f.message, f.fix)
        for f in guidance.lint(code)
    )


@cache
def rules() -> dict[str, dict[str, str]]:
    """The lint catalog's rules by id: severity, message and fix."""
    data = yaml.safe_load(guidance.read("guide/anti-patterns"))
    return {
        str(r["id"]): {
            "id": str(r["id"]),
            "severity": str(r["severity"]),
            "message": " ".join(str(r["message"]).split()),
            "fix": str(r.get("fix") or ""),
        }
        for r in data["rules"]
    }


@cache
def entries() -> Entries:
    """Every preset, colour family and lint rule a search can return."""
    presets = (
        Entry(
            Kind.PRESET,
            name,
            " + ".join(styles),
            words(
                " ".join(
                    [
                        name,
                        *styles,
                        PRESET_PURPOSES.get(name.removesuffix("-kr"), ""),
                    ]
                    + (["korean"] if name.endswith("-kr") else [])
                )
            ),
        )
        for name, styles in style_presets.items()
    )
    colors = (
        Entry(
            Kind.COLOR,
            f"dc.{c['name']}",
            f"{c['kind']} colour family"
            + (
                f", {c['discrete_size']} designed steps"
                if c["discrete_size"]
                else ""
            ),
            words(f"{c['name']} {c['kind']} color colour palette family"),
        )
        for c in list_colors()
    )
    catalog = (
        Entry(Kind.RULE, r["id"], r["message"], words(" ".join(r.values())))
        for r in rules().values()
    )
    return (*presets, *colors, *catalog)


def search(query: str, kind: str | None) -> list[dict[str, str]]:
    """Ranked hits, templates first, at most five of each kind."""
    parsed = Query.parse(query, kind)
    templates: list[Entry] = []
    if parsed.kind in {None, Kind.TEMPLATE}:
        ranked = guidance.search(query, limit=len(guidance.references()))
        templates = [
            Entry(
                Kind.TEMPLATE,
                r.id.removeprefix("template/"),
                r.summary,
                r.words,
            )
            for r in ranked
            if r.id.startswith("template/")
        ][: parsed.limit]
    others = (
        decide.rank(parsed, entries())
        if parsed.kind is not Kind.TEMPLATE
        else ()
    )
    return [e.to_json() for e in (*templates, *others)]


def get(kind: str, id: str) -> str:
    """One reference: a template's source, or a preset, colour or rule as JSON."""
    found = Kind.parse(kind)
    ref = id.strip()
    if found is Kind.TEMPLATE:
        return guidance.read("template/" + ref.removeprefix("template/"))
    if found is Kind.PRESET:
        if ref not in style_presets:
            raise ValueError(
                f"no preset {ref!r}; presets: {list(style_presets)}"
            )
        styles = style_presets[ref]
        values: dict[str, object] = {}
        for name in styles:
            values.update(load_style_dict(name))
        return dumps({"preset": ref, "styles": styles, "rcParams": values})
    if found is Kind.RULE:
        if ref not in rules():
            raise ValueError(
                f"no rule {ref!r}; search_reference(kind='rule') lists them"
            )
        return dumps(rules()[ref])
    families = {f"dc.{c['name']}": c for c in list_colors()}
    family = families.get(ref) or families.get(f"dc.{ref}")
    if family is None:
        return dumps({"color": ref, "hex": color(ref).to_hex()})
    steps = family["discrete_size"] or 10
    return dumps(
        {
            "family": f"dc.{family['name']}",
            "kind": family["kind"],
            "colors": colors(str(family["name"]), n=int(str(steps))),
        }
    )

    """Indented JSON text; values JSON cannot hold (a colour cycle) as text."""
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)
    """Indented JSON text."""
    return json.dumps(data, indent=2, ensure_ascii=False)
