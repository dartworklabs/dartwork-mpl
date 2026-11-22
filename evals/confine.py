"""One run's private places, and the OS rule that keeps its writes inside them.

Agents treat the plot script as scratch and write it to ``/tmp/s/plot.py``
whatever ``TMPDIR`` says, so concurrent runs overwrote each other (#822).
Each run therefore gets its own root holding the project, ``HOME``,
``TMPDIR`` and the Claude config dir. On macOS ``sandbox-exec`` denies the
session every write outside that root (and reads of the shared ``/tmp``,
where another sweep's stale script may lie), so a write to ``/tmp`` fails
in front of the agent and it carries on in a place of its own. Elsewhere
nothing enforces it: the transcript is then checked for work outside the
root (``judge.strays``) and such a run is ``INVALID``.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

SANDBOX_EXEC = "/usr/bin/sandbox-exec"
SHARED_TEMP = ("/private/tmp", "/private/var/tmp")


@dataclass(frozen=True)
class Box:
    """The root of one run and the places under it."""

    root: Path

    @property
    def project(self) -> Path:
        """The agent's working directory: a uv project with the library installed."""
        return self.root / "project"

    @property
    def home(self) -> Path:
        """``HOME``: empty, so nothing of the user's is found through ``~``."""
        return self.root / "home"

    @property
    def tmp(self) -> Path:
        """``TMPDIR`` and Claude Code's own temp dir."""
        return self.root / "tmp"

    @property
    def cfg(self) -> Path:
        """``CLAUDE_CONFIG_DIR``."""
        return self.root / "cfg"


def make(label: str) -> Box:
    """A fresh root with its places; the caller removes ``box.root``."""
    root = Path(tempfile.mkdtemp(prefix=f"dmpl-eval-{label}-")).resolve()
    box = Box(root)
    for place in (box.project, box.home, box.tmp, box.cfg):
        place.mkdir()
    return box


def profile(root: str, writable: list[str]) -> str:
    """The sandbox-exec profile: write only under ``root`` and ``writable``."""

    def paths(items: list[str] | tuple[str, ...]) -> str:
        quoted = (p.replace("\\", "\\\\").replace('"', '\\"') for p in items)
        return " ".join(f'(subpath "{q}")' for q in quoted)

    return "\n".join(
        [
            "(version 1)",
            "(allow default)",
            '(deny file-write* (subpath "/"))',
            f"(deny file-read* {paths(SHARED_TEMP)})",
            f"(allow file-read* file-write* {paths([root])})",
            f"(allow file-write* {paths(['/dev', *writable])})",
        ]
    )


def enforced() -> bool:
    """Whether this machine can confine a run (macOS with ``sandbox-exec``)."""
    return sys.platform == "darwin" and shutil.which(SANDBOX_EXEC) is not None


def confine(cmd: list[str], box: Box, writable: list[str]) -> list[str]:
    """``cmd`` under the write rule where the OS has one, else unchanged."""
    if not enforced():
        return cmd
    return [SANDBOX_EXEC, "-p", profile(str(box.root), writable), *cmd]
