"""A save's named special cases, applied after ``decide.plan``."""

from __future__ import annotations

from dataclasses import replace

from ..edgecase import EdgeCase
from .model import SavePlan, SaveRequest, Write


def sets_a_timestamp(request: SaveRequest, plan: SavePlan) -> bool:
    """The caller's metadata names a key the plan would blank."""
    keys = request.metadata_keys
    return any(w.writer.timestamp_key in keys for w in plan.writes)


def keep_caller_metadata(request: SaveRequest, plan: SavePlan) -> SavePlan:
    """The caller's metadata, untouched, wherever it names the timestamp."""
    keys = request.metadata_keys

    def keep(write: Write) -> Write:
        if write.writer.timestamp_key in keys:
            return replace(write, metadata=request.metadata)
        return write

    return SavePlan(tuple(keep(w) for w in plan.writes))


def has_ambient_salt(request: SaveRequest, plan: SavePlan) -> bool:
    """``rcParams["svg.hashsalt"]`` is already set."""
    return request.ambient_salt


def keep_ambient_salt(request: SaveRequest, plan: SavePlan) -> SavePlan:
    """No per-file salt: the global one stays in force."""
    return SavePlan(tuple(replace(w, salt=None) for w in plan.writes))


EDGES: tuple[EdgeCase[SaveRequest, SavePlan], ...] = (
    EdgeCase(
        name="caller-timestamp",
        why=(
            "a caller's metadata={'CreationDate': ...} was blanked out of "
            "the PDF along with matplotlib's own date"
        ),
        example="test_decide.py::test_caller_timestamp_wins_only_where_it_applies",
        applies=sets_a_timestamp,
        adjust=keep_caller_metadata,
    ),
    EdgeCase(
        name="ambient-svg-salt",
        why=(
            "a build's own svg.hashsalt was replaced by the file-name salt, "
            "changing the SVG ids it had pinned"
        ),
        example="test_decide.py::test_ambient_svg_salt_is_left_in_force",
        applies=has_ambient_salt,
        adjust=keep_ambient_salt,
    ),
)
