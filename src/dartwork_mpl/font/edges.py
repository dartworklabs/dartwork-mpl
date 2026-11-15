"""Named fixes to the font table, applied after ``decide.table_plan``."""

from __future__ import annotations

from dataclasses import replace

from ..edgecase import EdgeCase
from .model import MIN_BUNDLED_FILES, Plan, Table, Weight

# Both Paperlogy files declare OS/2 weight 250, so a light request got either
# one depending on discovery order. Their names say what they are.
PAPERLOGY_WEIGHTS = {
    "Paperlogy-1Thin.ttf": Weight(100),
    "Paperlogy-2ExtraLight.ttf": Weight(200),
}


def system_copy_first(table: Table, plan: Plan) -> bool:
    """A non-bundled face sits before a bundled one."""
    seen_system = False
    for i in plan.order:
        if not table.faces[i].bundled:
            seen_system = True
        elif seen_system:
            return True
    return False


def bundled_first(table: Table, plan: Plan) -> Plan:
    """Bundled faces first, each group in its own order."""
    bundled = tuple(i for i in plan.order if table.faces[i].bundled)
    others = tuple(i for i in plan.order if not table.faces[i].bundled)
    return Plan(bundled + others, plan.weights, plan.warning)


def has_wrong_paperlogy_weight(table: Table, plan: Plan) -> bool:
    """A bundled Paperlogy Thin or ExtraLight still carries its own weight."""
    return any(
        face.bundled and PAPERLOGY_WEIGHTS.get(face.file, w) != w
        for face, w in zip(table.faces, plan.weights, strict=True)
    )


def correct_paperlogy(table: Table, plan: Plan) -> Plan:
    """The weight each Paperlogy file's name says."""
    weights = tuple(
        PAPERLOGY_WEIGHTS.get(face.file, w) if face.bundled else w
        for face, w in zip(table.faces, plan.weights, strict=True)
    )
    return Plan(plan.order, weights, plan.warning)


def bundle_emptied(table: Table, plan: Plan) -> bool:
    """Fewer bundled files than any install ships."""
    return table.bundled_files < MIN_BUNDLED_FILES


def warn_emptied(table: Table, plan: Plan) -> Plan:
    """Say the fallback chain will fall to system fonts."""
    return replace(
        plan,
        warning=f"dartwork-mpl found only {table.bundled_files} bundled font "
        "file(s). Korean and symbol text may fall back to system fonts; "
        "reinstall the package to restore them.",
    )


EDGES: tuple[EdgeCase[Table, Plan], ...] = (
    EdgeCase(
        name="paperlogy-weight-250",
        why="Paperlogy Thin and ExtraLight both declare weight 250, so a "
        "light request picked either one by discovery order",
        applies=has_wrong_paperlogy_weight,
        adjust=correct_paperlogy,
    ),
    EdgeCase(
        name="system-font-tie",
        why="matplotlib keeps the first of equally scored entries and appends "
        "bundled files, so a system copy of Roboto silently won",
        applies=system_copy_first,
        adjust=bundled_first,
    ),
    EdgeCase(
        name="emptied-bundle",
        why="an install without the font files draws Hangul and symbols in "
        "whatever the machine has, so say so once",
        applies=bundle_emptied,
        adjust=warn_emptied,
    ),
)
