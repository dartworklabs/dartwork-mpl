"""Shared internal helpers.

Small utilities used by multiple modules. Not part of the public API.
"""

from __future__ import annotations

from pathlib import Path


def create_parent_path(path: str | Path) -> None:
    """Create parent directory if it doesn't exist.

    Parameters
    ----------
    path : str or Path
        Path whose parent directory will be created.
    """
    path = Path(path)
    if not path.parent.exists():
        path.parent.mkdir(parents=True)
