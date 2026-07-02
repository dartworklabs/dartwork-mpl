"""Shared data types used by every visual-validation check.

Each check function in :mod:`dartwork_mpl.validate._checks` returns a
list of :class:`VisualWarning`. The orchestrator merges them and prints
their ``__str__`` output to stdout for AI-agent consumption.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar

# Re-exported from the shared internal helper so the layout engine and
# the validation checks suppress the identical exception set (the two
# used to carry private copies that could drift).
from .._helpers import BBOX_ERRORS

__all__ = ["BBOX_ERRORS", "Severity", "VisualWarning"]


class Severity(str, Enum):
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class VisualWarning:
    """A single visual issue detected in a figure (e.g., overflow, overlap)."""

    severity: Severity
    check_id: str
    message: str
    detail: dict[str, Any] = field(default_factory=dict)

    # Icons per severity for structured log output.
    _ICONS: ClassVar[dict[Severity, str]] = {
        Severity.WARNING: "⚠️ ",
        Severity.INFO: "💡",
    }

    def __str__(self) -> str:
        icon = self._ICONS.get(self.severity, "")
        return f"[VISUAL] {icon} {self.check_id}: {self.message}"
