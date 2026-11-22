"""Judge clear columns of similarly sized text beside a plot."""

from __future__ import annotations

from collections.abc import Sequence
from itertools import groupby, pairwise
from statistics import median

from .findings import Findings
from .model import AlignmentSample, Facts


def spread(values: Sequence[float]) -> float:
    """The distance between the extreme values."""
    return max(values) - min(values)


def columns(
    samples: tuple[AlignmentSample, ...],
) -> list[list[AlignmentSample]]:
    """Nearby anchors with one horizontal alignment and a similar font size."""
    result: list[list[AlignmentSample]] = []
    for _, family in groupby(
        sorted(samples, key=lambda s: s.align.mpl), key=lambda s: s.align
    ):
        column: list[AlignmentSample] = []
        for sample in sorted(family, key=lambda s: s.x):
            if column and (
                sample.x - column[0].x > 0.35 * column[0].text.em
                or abs(sample.text.em / column[0].text.em - 1) > 0.12
            ):
                result.append(column)
                column = []
            column.append(sample)
        if column:
            result.append(column)
    return result


def misalignment(facts: Facts, found: Findings) -> Findings:
    """An apparent column with noticeably ragged numeric stops or edges."""
    for samples in facts.alignment:
        for column in columns(samples):
            if len(column) < 3:
                continue
            rows = sorted(column, key=lambda row: row.y)
            em = median(t.text.em for t in rows)
            if any(b.y - a.y < 0.85 * em for a, b in pairwise(rows)):
                continue
            counts = {len(row.marks) for row in rows}
            stops = (
                [
                    spread(stop)
                    for stop in zip(*(row.marks for row in rows), strict=True)
                ]
                if len(counts) == 1 and 0 not in counts
                else []
            )
            rough = max(stops, default=0.0)
            edge = spread([row.x for row in rows])
            if rough >= 0.2 * em and (
                len(stops) > 1 or not rows[0].tidy_value_edge
            ):
                gap = rough / em
                detail = "decimal positions"
                how = "decimal"
            elif 0.08 * em <= edge <= 0.35 * em:
                gap = edge / em
                detail = "edges"
                how = rows[0].align.mpl
            else:
                continue
            found = found.flag(
                "TEXT_MISALIGNMENT",
                f"Axes[{rows[0].text.panel}]: {len(rows)} texts form a column "
                f"whose {detail} differ by up to {gap:.2f} em",
                [row.text for row in rows],
                fix=f'pass those texts to dm.align_texts(texts, "{how}")',
            )
    return found
