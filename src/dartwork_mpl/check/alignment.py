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


def numeric_body(rows: list[AlignmentSample]) -> list[AlignmentSample]:
    """Ignore a heading or footer outside the continuous numeric body."""
    start = next((i for i, row in enumerate(rows) if row.marks), len(rows))
    end = next(
        (i for i, row in enumerate(reversed(rows)) if row.marks), len(rows)
    )
    return rows[start : len(rows) - end]


def decimal_spread(body: list[AlignmentSample]) -> float:
    """Compare equal numeric shapes within the same typography.

    A bold subtotal can be wider even when the body is already aligned.
    """
    counts = {len(row.marks) for row in body}
    if len(body) < 3 or len(counts) != 1 or 0 in counts:
        return 0.0
    by_font = sorted(body, key=lambda row: row.font_key)
    return max(
        (
            spread(stop)
            for _, rows in groupby(by_font, key=lambda row: row.font_key)
            for stop in zip(*(row.marks for row in rows), strict=True)
        ),
        default=0.0,
    )


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
            body = numeric_body(rows)
            rough = decimal_spread(body)
            edge = spread([row.x for row in rows])
            if rough >= 0.2 * em:
                rows = body
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
