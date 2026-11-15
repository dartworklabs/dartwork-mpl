"""The legend's named special cases, applied after the ``decide`` functions.

Each decision has its own facts and plan types and its own registry:
``ENTRY_EDGES`` for which entries a legend shows, ``TITLE_EDGES`` for the
pad of the Axes titles.
"""

from __future__ import annotations

from ..edgecase import EdgeCase
from .plans import EntryFacts, EntryPlan, TitleFacts, TitlePad


def has_twins(facts: EntryFacts, plan: EntryPlan) -> bool:
    """The Axes has twins drawn in its box."""
    return len(facts.owners) > 1


def merge_twins(facts: EntryFacts, plan: EntryPlan) -> EntryPlan:
    """Every twin's entries once, on the twin drawn last; theirs removed."""
    owners = facts.owners
    host = max(range(len(owners)), key=lambda i: owners[i].rank)
    seen: set[str] = set()
    picks: list[tuple[int, int]] = []
    for i in sorted(range(len(owners)), key=lambda i: owners[i].rank[1]):
        for j, label in enumerate(owners[i].entries.labels):
            if label not in seen:
                seen.add(label)
                picks.append((i, j))
    remove = tuple(
        i for i, o in enumerate(owners) if i != host and o.legend is not None
    )
    return EntryPlan(host=host, picks=tuple(picks), remove=remove)


def has_legend_above(facts: TitleFacts, plan: TitlePad) -> bool:
    """Axes titles with a legend above the Axes."""
    return bool(facts.legends_above)


def lift_titles(facts: TitleFacts, plan: TitlePad) -> TitlePad:
    """Raise the titles so their baseline sits the title gap above the legend."""
    pad = max(title.pad for title in facts.titles)
    needed = 0.0
    for title in facts.titles:
        for legend in facts.legends_above:
            beside = (
                title.box.x1 <= legend.x0 - facts.gap
                or title.box.x0 >= legend.x1 + facts.gap
            )
            if beside or title.box.y1 <= legend.y0:
                continue
            needed = max(needed, legend.y1 + facts.gap - title.base_y)
    return TitlePad(needed) if needed > pad + 0.5 else plan


ENTRY_EDGES: tuple[EdgeCase[EntryFacts, EntryPlan], ...] = (
    EdgeCase(
        name="twin-merge",
        why=(
            "a twinx pair drew two legends, the left one under the right "
            "Axes' line"
        ),
        example="test_edges.py::"
        "test_twin_merge_puts_every_entry_on_the_twin_drawn_last",
        applies=has_twins,
        adjust=merge_twins,
    ),
)

TITLE_EDGES: tuple[EdgeCase[TitleFacts, TitlePad], ...] = (
    EdgeCase(
        name="title-over-above-legend",
        why=(
            "a legend placed above the Axes was drawn over the Axes title, "
            "which matplotlib keeps where it was"
        ),
        example="test_edges.py::"
        "test_title_over_above_legend_lifts_the_titles_over_it",
        applies=has_legend_above,
        adjust=lift_titles,
    ),
)
