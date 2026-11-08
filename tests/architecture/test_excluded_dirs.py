"""The excluded-directory helpers observe what they claim, on synthetic trees.

``tests.support.excluded_dirs`` backs the regression tests that keep the suite
out of ``docs/superpowers``. Every check here runs on a private tree created
under ``tmp_path``; none names or probes a repository directory. The watch is
auxiliary evidence: it covers the in-process operations below and nothing in a
child process (see the helper's module docstring).
"""

from __future__ import annotations

import glob
import os
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from tests.support.excluded_dirs import walk_files, watch_access


def _synthetic_tree(root: Path) -> Path:
    """Create one kept file and one excluded subtree holding a decoy."""
    excluded = root / "excluded"
    (excluded / "deep").mkdir(parents=True)
    (excluded / "deep" / "decoy.md").write_text("decoy\n", encoding="utf-8")
    (root / "kept.md").write_text("kept\n", encoding="utf-8")
    return excluded


def _open_decoy(excluded: Path) -> None:
    with open(excluded / "deep" / "decoy.md", encoding="utf-8") as stream:
        stream.read()


_OPERATIONS: dict[str, Callable[[Path], object]] = {
    "os.stat": lambda excluded: os.stat(excluded / "deep" / "decoy.md"),
    # Look the functions up at call time: a reference bound before the watch
    # began bypasses it (a documented blind spot of the helper).
    "os.lstat": lambda excluded: os.lstat(excluded),
    "os.listdir": lambda excluded: os.listdir(excluded),
    "os.scandir": lambda excluded: list(os.scandir(excluded)),
    "os.walk": lambda excluded: list(os.walk(excluded)),
    "Path.exists": lambda excluded: (excluded / "deep").exists(),
    "Path.is_file": lambda excluded: (excluded / "deep/decoy.md").is_file(),
    "Path.iterdir": lambda excluded: list(excluded.iterdir()),
    "Path.rglob": lambda excluded: list(excluded.rglob("*")),
    "open": _open_decoy,
    "Path.read_text": lambda excluded: (excluded / "deep/decoy.md").read_text(
        encoding="utf-8"
    ),
    "glob.glob": lambda excluded: glob.glob(
        str(excluded / "**"), recursive=True
    ),
    "shutil.copyfile": lambda excluded: shutil.copyfile(
        excluded / "deep" / "decoy.md", excluded.parent / "copy.md"
    ),
    "shutil.copytree": lambda excluded: shutil.copytree(
        excluded, excluded.parent / "copy"
    ),
}


@pytest.mark.parametrize("operation", sorted(_OPERATIONS))
def test_watch_records_in_process_access_below_a_root(
    operation: str, tmp_path: Path
) -> None:
    excluded = _synthetic_tree(tmp_path)
    original = os.stat
    with watch_access(excluded) as accesses:
        try:
            _OPERATIONS[operation](excluded)
        except PermissionError:
            pass
    assert accesses, f"{operation} was not observed"
    assert all(
        Path(path) == excluded or excluded in Path(path).parents
        for _, path in accesses
    )
    assert os.stat is original
    assert not (tmp_path / "copy.md").exists()
    assert not (tmp_path / "copy").exists()


def test_watch_leaves_paths_outside_the_roots_alone(tmp_path: Path) -> None:
    excluded = _synthetic_tree(tmp_path)
    with watch_access(excluded) as accesses:
        text = (tmp_path / "kept.md").read_text(encoding="utf-8")
        files = walk_files(tmp_path, lambda directory: directory == excluded)
    assert (text, files, accesses) == ("kept\n", [tmp_path / "kept.md"], [])


class _NoTouchEntry:
    """A ``DirEntry`` stand-in that refuses every metadata call when blocked."""

    def __init__(self, entry: os.DirEntry[str], blocked: str) -> None:
        self._entry = entry
        self._blocked = blocked
        self.name = entry.name
        self.path = entry.path

    def _touch(self) -> None:
        if self.name == self._blocked:
            raise AssertionError(f"metadata of pruned {self.path!r} read")

    def is_dir(self, *, follow_symlinks: bool = True) -> bool:
        self._touch()
        return self._entry.is_dir(follow_symlinks=follow_symlinks)

    def is_file(self, *, follow_symlinks: bool = True) -> bool:
        self._touch()
        return self._entry.is_file(follow_symlinks=follow_symlinks)

    def is_symlink(self) -> bool:
        self._touch()
        return self._entry.is_symlink()

    def stat(self, *, follow_symlinks: bool = True) -> os.stat_result:
        self._touch()
        return self._entry.stat(follow_symlinks=follow_symlinks)


def test_walk_files_prunes_an_entry_before_any_type_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A symlinked directory is the case os.walk stats before a caller can
    # prune it (DirEntry.is_dir follows the link). The watch cannot see
    # that call, so the entries themselves refuse it here.
    target = tmp_path / "elsewhere"
    target.mkdir()
    (target / "decoy.md").write_text("decoy\n", encoding="utf-8")
    scan = tmp_path / "scan"
    scan.mkdir()
    (scan / "kept.md").write_text("kept\n", encoding="utf-8")
    (scan / "blocked").symlink_to(target, target_is_directory=True)
    real_scandir = os.scandir

    class _Listing:
        """A scandir iterator that hands out refusing entries (any walker)."""

        def __init__(self, path: str | os.PathLike[str]) -> None:
            self._listing = real_scandir(path)

        def __enter__(self) -> _Listing:
            return self

        def __exit__(self, *exc: object) -> None:
            self._listing.close()

        def __iter__(self) -> _Listing:
            return self

        def __next__(self) -> _NoTouchEntry:
            return _NoTouchEntry(next(self._listing), "blocked")

        def close(self) -> None:
            self._listing.close()

    monkeypatch.setattr(os, "scandir", _Listing)
    files = walk_files(scan, lambda path: path.name == "blocked")
    assert files == [scan / "kept.md"]


def test_walk_files_neither_follows_nor_collects_a_linked_directory(
    tmp_path: Path,
) -> None:
    target = tmp_path / "elsewhere"
    target.mkdir()
    (target / "decoy.md").write_text("decoy\n", encoding="utf-8")
    scan = tmp_path / "scan"
    scan.mkdir()
    (scan / "kept.md").write_text("kept\n", encoding="utf-8")
    (scan / "linked").symlink_to(target, target_is_directory=True)
    assert walk_files(scan, lambda path: False) == [scan / "kept.md"]


def test_walk_files_lists_every_entry_without_a_prune(tmp_path: Path) -> None:
    excluded = _synthetic_tree(tmp_path)
    assert walk_files(tmp_path, lambda directory: False) == [
        excluded / "deep" / "decoy.md",
        tmp_path / "kept.md",
    ]
