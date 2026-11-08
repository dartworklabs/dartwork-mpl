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


def test_walk_files_lists_every_entry_without_a_prune(tmp_path: Path) -> None:
    excluded = _synthetic_tree(tmp_path)
    assert walk_files(tmp_path, lambda directory: False) == [
        excluded / "deep" / "decoy.md",
        tmp_path / "kept.md",
    ]
