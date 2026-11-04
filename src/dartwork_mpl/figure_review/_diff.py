"""Neutral differences between two figure summaries.

Nothing here decides whether a change was wanted: a change is ``allowed`` only
when its path matches a pattern the caller passed (``*`` is the only wildcard,
so ``axes[0]`` means that Axes and ``axes[*]`` any). The agent reading the list
interprets it.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

__all__ = ["Change", "diff_summaries", "flatten", "matches"]


@dataclass(frozen=True)
class Change:
    """One summary entry that differs from the baseline.

    ``path`` names the entry (``axes[0].ylabel.text``); ``before`` / ``after``
    are the baseline and current values, ``None`` when the entry is new or
    gone. ``allowed`` is ``True`` when ``path`` matches an ``allow=`` pattern.
    """

    path: str
    before: Any
    after: Any
    allowed: bool

    def to_dict(self) -> dict[str, Any]:
        """The change as a JSON-ready mapping."""
        return {
            "path": self.path,
            "before": self.before,
            "after": self.after,
            "allowed": self.allowed,
        }


def flatten(tree: Any, prefix: str = "") -> dict[str, Any]:
    """Map every leaf of a summary to its path, in document order.

    Mappings add ``.key``; lists of mappings add ``[i]``; any other value,
    including a list of scalars, is one leaf.
    """
    out: dict[str, Any] = {}
    if isinstance(tree, Mapping):
        if not tree and prefix:
            out[prefix] = {}
        for key, value in tree.items():
            out.update(
                flatten(value, f"{prefix}.{key}" if prefix else str(key))
            )
    elif (
        isinstance(tree, list)
        and tree
        and all(isinstance(item, Mapping) for item in tree)
    ):
        for i, item in enumerate(tree):
            out.update(flatten(item, f"{prefix}[{i}]"))
    else:
        out[prefix] = tree
    return out


def _pattern(text: str) -> re.Pattern[str]:
    """``*`` matches any run of characters; everything else, ``[`` too, is literal."""
    return re.compile(".*".join(re.escape(part) for part in text.split("*")))


def matches(path: str, pattern: str) -> bool:
    """Whether an ``allow=`` pattern covers ``path`` (``axes[*].ylabel.*``)."""
    return _pattern(pattern).fullmatch(path) is not None


def diff_summaries(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    allow: Iterable[str] = (),
) -> list[Change]:
    """Every leaf that differs, in the order the summaries list them."""
    patterns = [_pattern(p) for p in allow]
    old = flatten(before)
    new = flatten(after)
    missing = object()
    changes: list[Change] = []
    for path in dict.fromkeys([*old, *new]):
        a = old.get(path, missing)
        b = new.get(path, missing)
        if a == b:
            continue
        changes.append(
            Change(
                path=path,
                before=None if a is missing else a,
                after=None if b is missing else b,
                allowed=any(p.fullmatch(path) for p in patterns),
            )
        )
    return changes
