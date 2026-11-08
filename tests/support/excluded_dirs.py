"""Walk test inputs without listing excluded directories, and watch for leaks.

``walk_files`` is the structural tool: it decides on every directory before
listing it, so a pruned tree such as ``docs/superpowers`` is never listed,
stat-ed or read by the walk.

``watch_access`` is auxiliary evidence for regression tests that run on a
private synthetic tree. While active it records -- and refuses with
``PermissionError`` -- in-process access at or below the given roots through
the patched ``os.stat``, ``os.lstat``, ``os.scandir`` and ``os.listdir`` and
through this interpreter's ``open``, listing, glob and copy audit events. It
does not see C-level calls that bypass the ``os`` module attributes, a
reference to those functions bound before the watch began, ``os.DirEntry``
type checks, or any child process (an exec'd Sphinx, ``git``, another
Python). It is therefore never the proof that a real tree was left alone;
that proof is giving the code under test a root without the excluded files.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

# Audit events and the argument positions that name a filesystem path.
_AUDITED: dict[str, tuple[int, ...]] = {
    "open": (0,),
    "os.listdir": (0,),
    "os.scandir": (0,),
    "glob.glob": (0,),
    "shutil.copyfile": (0, 1),
    "shutil.copytree": (0, 1),
}
_PATCHED = ("stat", "lstat", "scandir", "listdir")
_watches: list[tuple[tuple[str, ...], list[tuple[str, str]]]] = []
_hook = {"installed": False}


def walk_files(root: Path, prune: Callable[[Path], bool]) -> list[Path]:
    """Return every non-directory entry below ``root``, sorted.

    ``prune(directory)`` runs before ``directory`` is listed; ``True`` skips
    it and everything below it. Symlinked directories are not followed, as
    with ``Path.rglob``.
    """
    found: list[Path] = []
    for current, dirs, files in os.walk(root):
        base = Path(current)
        dirs[:] = sorted(name for name in dirs if not prune(base / name))
        found.extend(base / name for name in files)
    return sorted(found)


def _normal(path: object) -> str | None:
    """Return an absolute, normalised path string without touching disk."""
    if isinstance(path, int) or not isinstance(path, str | bytes | os.PathLike):
        return None
    return os.path.normpath(os.path.abspath(os.fsdecode(path)))


def _check(operation: str, path: object) -> None:
    """Record and refuse ``operation`` when ``path`` is inside a watched root."""
    target = _normal(path)
    if target is None:
        return
    for roots, seen in _watches:
        if any(target == r or target.startswith(r + os.sep) for r in roots):
            seen.append((operation, target))
            raise PermissionError(f"{operation} reached excluded {target}")


def _audit(event: str, args: tuple[object, ...]) -> None:
    """Forward the path arguments of the audited events to ``_check``."""
    if not _watches or event not in _AUDITED:
        return
    for index in _AUDITED[event]:
        if index < len(args):
            _check(event, args[index])


def _guard(name: str, original: Callable[..., Any]) -> Callable[..., Any]:
    """Wrap one ``os`` function so its path argument is checked first."""

    def guarded(*args: Any, **kwargs: Any) -> Any:
        _check(f"os.{name}", args[0] if args else kwargs.get("path", "."))
        return original(*args, **kwargs)

    return guarded


@contextmanager
def watch_access(*roots: Path) -> Iterator[list[tuple[str, str]]]:
    """Record and refuse in-process access at or below ``roots``.

    Yields the list of ``(operation, path)`` records. A caller that swallows
    the ``PermissionError`` (``os.walk`` and ``Path.rglob`` do) still leaves
    its record, so assert the list is empty.
    """
    if not _hook["installed"]:
        sys.addaudithook(_audit)
        _hook["installed"] = True
    normal = tuple(str(_normal(root)) for root in roots)
    seen: list[tuple[str, str]] = []
    watch = (normal, seen)
    originals = {name: getattr(os, name) for name in _PATCHED}
    _watches.append(watch)
    for name, original in originals.items():
        setattr(os, name, _guard(name, original))
    try:
        yield seen
    finally:
        for name, original in originals.items():
            setattr(os, name, original)
        _watches.remove(watch)
