"""One call for the review loop: save, validate, summarize, compare.

:func:`review` wraps what already exists and adds no check, fix or style:
it saves with :func:`~dartwork_mpl.save_formats` (the same files a plain save
writes), runs :func:`~dartwork_mpl.validate_figure` on the saved figure and
keeps every finding as returned, reads a summary of what the figure shows, and
with ``baseline=`` lists how that summary differs from an earlier review. It
never decides whether a change was requested; ``allow=`` patterns only mark
the changes the caller expected.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..io import save_formats
from ..validate import Severity, VisualWarning, validate_figure
from ._diff import Change, diff_summaries
from ._summary import summarize

if TYPE_CHECKING:
    from matplotlib.figure import Figure

__all__ = ["SCHEMA", "Change", "Review", "review"]

#: Version of the ``<stem>.review.json`` document and its summary.
SCHEMA = 1

_JSON_SUFFIX = ".review.json"
#: Printed changes before the report says how many more there are.
_PRINTED_CHANGES = 20


@dataclass(frozen=True)
class Review:
    """What :func:`review` saved, found and compared.

    ``complete`` means every check ran (no ``CHECK_FAILED`` finding); it is
    not a pass: a complete review can still hold WARNING findings.
    ``changes`` is ``None`` without a baseline.
    """

    paths: dict[str, Path]
    findings: list[VisualWarning]
    complete: bool
    incomplete_checks: list[str]
    summary: dict[str, Any]
    changes: list[Change] | None = None

    @property
    def warnings(self) -> list[VisualWarning]:
        """The WARNING findings, in the order the checks reported them."""
        return [f for f in self.findings if f.severity is Severity.WARNING]

    @property
    def unexpected(self) -> list[Change]:
        """Changes no ``allow=`` pattern matched (empty without a baseline)."""
        return [c for c in self.changes or [] if not c.allowed]

    def to_dict(self) -> dict[str, Any]:
        """The ``<stem>.review.json`` document."""
        return {
            "schema": SCHEMA,
            "paths": {k: str(v) for k, v in self.paths.items()},
            "complete": self.complete,
            "incomplete_checks": list(self.incomplete_checks),
            "findings": [
                {
                    "severity": f.severity.value,
                    "check_id": f.check_id,
                    "message": f.message,
                    "detail": f.detail,
                }
                for f in self.findings
            ],
            "summary": self.summary,
            "changes": (
                None
                if self.changes is None
                else [c.to_dict() for c in self.changes]
            ),
        }

    def __str__(self) -> str:
        """The report :func:`review` prints: files, findings, completeness, changes."""
        files = ", ".join(str(p) for k, p in self.paths.items() if k != "json")
        lines = [f"[REVIEW] saved {files} (+ {self.paths['json']})"]
        lines.append(f"[REVIEW] findings: {_count_findings(self.findings)}")
        if self.complete:
            lines.append(
                "[REVIEW] every check ran (complete is not a pass; read the findings)"
            )
        else:
            lines.append(
                "[REVIEW] incomplete: "
                + ", ".join(self.incomplete_checks)
                + " could not run"
            )
        outside = self.summary.get("outside_canvas") or []
        if outside:
            where = ", ".join(sorted({o["where"] for o in outside}))
            lines.append(
                f"[REVIEW] text outside the canvas: {len(outside)} ({where})"
            )
        if self.changes is not None:
            allowed = sum(c.allowed for c in self.changes)
            lines.append(
                f"[REVIEW] changes vs baseline: {len(self.changes)} "
                f"({allowed} allowed, {len(self.changes) - allowed} not)"
            )
            for c in self.changes[:_PRINTED_CHANGES]:
                mark = "allowed" if c.allowed else "not allowed"
                lines.append(
                    f"[REVIEW]   {c.path}: {c.before!r} -> {c.after!r} ({mark})"
                )
            if len(self.changes) > _PRINTED_CHANGES:
                lines.append(
                    f"[REVIEW]   ... {len(self.changes) - _PRINTED_CHANGES} more "
                    "(Review.changes, or 'changes' in the json)"
                )
        return "\n".join(lines)


def _count_findings(findings: list[VisualWarning]) -> str:
    """Findings grouped by severity and check id; the list itself is untouched."""
    if not findings:
        return "none"
    parts = []
    for severity in (Severity.WARNING, Severity.INFO):
        ids = Counter(f.check_id for f in findings if f.severity is severity)
        if ids:
            body = ", ".join(f"{cid} x{n}" for cid, n in ids.items())
            parts.append(f"{sum(ids.values())} {severity.value} ({body})")
    return "; ".join(parts)


def _json_path(stem: str) -> Path:
    return Path(stem + _JSON_SUFFIX)


def _baseline_summary(
    baseline: Review | str | os.PathLike[str],
) -> dict[str, Any]:
    """The summary of an earlier review: a Review, a stem or a .review.json."""
    if isinstance(baseline, Review):
        return baseline.summary
    raw = os.fspath(baseline)
    path = Path(raw) if raw.endswith(_JSON_SUFFIX) else _json_path(raw)
    if not path.is_file():
        raise ValueError(
            f"baseline review {str(path)!r} not found; run dm.review on the "
            "original figure first and pass its stem"
        )
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or document.get("schema") != SCHEMA:
        raise ValueError(
            f"{str(path)!r} is not a schema-{SCHEMA} review document"
        )
    summary = document.get("summary")
    if not isinstance(summary, dict):
        raise ValueError(f"{str(path)!r} has no summary")
    return summary


def _check_stem(fig: Figure, stem: str) -> None:
    suffix = Path(stem).suffix.lower()
    if suffix and suffix[1:] in fig.canvas.get_supported_filetypes():
        raise ValueError(
            f"stem {stem!r} ends with the image suffix {suffix!r}; pass the "
            "path without an extension (formats= picks the files)"
        )
    if stem.endswith(_JSON_SUFFIX):
        raise ValueError(f"stem {stem!r} ends with {_JSON_SUFFIX!r}")


def review(
    fig: Figure,
    stem: str | os.PathLike[str],
    *,
    baseline: Review | str | os.PathLike[str] | None = None,
    allow: Iterable[str] = (),
    formats: tuple[str, ...] = ("png", "pdf"),
    quiet: bool = False,
    **save_kwargs: Any,
) -> Review:
    """Save ``fig``, report every finding, summarize it and compare it.

    One call for the review loop of a figure or a revision:

    1. saves ``<stem>.<format>`` for each of ``formats`` with
       :func:`~dartwork_mpl.save_formats` (``**save_kwargs`` such as ``dpi=``
       or ``bbox_inches=`` pass through; the files are the ones a plain save
       writes);
    2. runs every check of :func:`~dartwork_mpl.validate_figure` on the saved
       figure and keeps the findings unchanged (``PRESET_OVERRIDE`` included);
    3. summarizes per Axes the titles, axis labels, ranges, tick labels,
       series (kind, label, count, colour, line style and a digest of the
       values), legend and free text, plus every text outside the canvas;
    4. with ``baseline=`` (an earlier :class:`Review`, its stem or its
       ``.review.json`` path) lists every summary entry that differs as a
       :class:`Change`. A change is ``allowed`` only when its path
       (``axes[0].ylabel.text``) matches one of the ``allow=`` patterns,
       where ``*`` matches any run of characters and everything else is
       literal (``axes[*].ylabel.*``); nothing is judged or fixed;
    5. writes ``<stem>.review.json`` (the :meth:`Review.to_dict` document) so
       a later script can pass the stem as ``baseline=``, and prints a short
       report unless ``quiet=True``.

    ``Review.complete`` is ``False`` when a check could not run
    (``CHECK_FAILED``); it is not a pass. A failure to save raises before any
    check runs. A stem ending in an image suffix, or a baseline that does not
    exist, raises ``ValueError`` before anything is written::

        r1 = dm.review(fig, "output/figure-v1")
        # ... the revision script redraws the figure with one change ...
        r2 = dm.review(fig, "output/figure-v2", baseline="output/figure-v1",
                       allow=["axes[0].ylabel.*"])
        r2.unexpected  # changes nobody allowed

    Returns
    -------
    Review
    """
    stem_str = os.fspath(stem)
    _check_stem(fig, stem_str)
    for name in ("validate", "validate_quiet"):
        if name in save_kwargs:
            raise TypeError(f"review validates itself; drop {name}=")
    before = None if baseline is None else _baseline_summary(baseline)
    patterns = tuple(allow)

    save_formats(fig, stem_str, formats=formats, validate=False, **save_kwargs)
    findings = validate_figure(fig, quiet=True)
    failed = [
        str(f.detail.get("check_id", "?"))
        for f in findings
        if f.check_id == "CHECK_FAILED"
    ]
    summary = summarize(fig)
    changes = (
        None if before is None else diff_summaries(before, summary, patterns)
    )

    paths = {fmt: Path(f"{stem_str}.{fmt}") for fmt in formats}
    paths["json"] = _json_path(stem_str)
    result = Review(
        paths=paths,
        findings=findings,
        complete=not failed,
        incomplete_checks=failed,
        summary=summary,
        changes=changes,
    )
    paths["json"].write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=1, default=str)
        + "\n",
        encoding="utf-8",
    )
    if not quiet:
        print(result, flush=True)
    return result
