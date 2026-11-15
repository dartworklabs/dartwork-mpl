"""Read a tracked repository file by its repository-relative path."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def read_repo_bytes(relative: str) -> bytes:
    """Return the raw bytes of ``relative`` below the repository root."""
    return (REPO_ROOT / relative).read_bytes()


def read_repo_text(relative: str) -> str:
    """Return ``relative`` below the repository root decoded as UTF-8."""
    return (REPO_ROOT / relative).read_text(encoding="utf-8")
