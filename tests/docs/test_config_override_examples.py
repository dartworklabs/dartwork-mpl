"""Shipped text never shows a bare ``dm.config.override(...)`` call.

``dm.config.override`` is a context manager: a bare call changes nothing.
Every example with arguments must read ``with dm.config.override(...)``
(review 2026-11-05, R3: ``korean.md`` and the ``config`` docstring showed
``dm.config.override(number_ladder="si")`` on its own). The generic mention
``dm.config.override(...)`` in prose is allowed.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.support.excluded_dirs import walk_files, watch_access

_REPO = Path(__file__).resolve().parents[2]
# Text that reaches users and agents: docs, the package (skills, prompt
# corpus, docstrings), the top-level guides and llms files. Design records
# (docs/superpowers, docs/adr) keep their wording.
_ROOTS = ("docs", "src/dartwork_mpl")
_TOP = (
    "README.md",
    "CHANGELOG.md",
    "AGENTS.md",
    "CLAUDE.md",
    "llms.txt",
    "llms-full.txt",
)
_SUFFIXES = {".md", ".py", ".rst", ".txt", ".yaml", ".yml"}
# Pruned before they are listed: their files are never listed, stat-ed or read.
_SKIP = ("docs/superpowers/", "docs/adr/", "docs/_build/")
_BARE = re.compile(r"(?<!with )dm\.config\.override\((?!\.\.\.\))")


def _shipped() -> list[Path]:
    files = [_REPO / name for name in _TOP if (_REPO / name).is_file()]
    skipped = {_REPO / prefix.rstrip("/") for prefix in _SKIP}
    for root in _ROOTS:
        for path in walk_files(_REPO / root, lambda d: d in skipped):
            relative = path.relative_to(_REPO).as_posix()
            if (
                path.suffix in _SUFFIXES
                and path.is_file()
                and "/tests/" not in f"/{relative}"
            ):
                files.append(path)
    return files


def test_scan_prunes_design_records_before_listing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Never list, stat or read below a skipped prefix such as docs/superpowers."""
    kept = ["README.md", "docs/guide.md", "src/dartwork_mpl/config.py"]
    skipped = [tmp_path / prefix.rstrip("/") for prefix in _SKIP]
    for path in [
        *(tmp_path / name for name in kept),
        tmp_path / "src/dartwork_mpl/slice/tests/test_x.py",
        *(directory / "decoy.md" for directory in skipped),
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("synthetic\n", encoding="utf-8")
    monkeypatch.setitem(globals(), "_REPO", tmp_path)

    with watch_access(*skipped) as accesses:
        files = _shipped()

    assert (accesses, files) == ([], [tmp_path / name for name in kept])


def test_the_scan_covers_the_known_examples() -> None:
    names = {path.relative_to(_REPO).as_posix() for path in _shipped()}
    assert "src/dartwork_mpl/config.py" in names
    assert "src/dartwork_mpl/skills/dartwork-mpl/references/korean.md" in names
    assert "docs/usage_guide/layout.md" in names


@pytest.mark.parametrize(
    ("text", "bare"),
    [
        ('dm.config.override(number_ladder="si")', True),
        ("``dm.config.override(tick_years=4)``", True),
        ('with dm.config.override(number_ladder="si"):', False),
        ("`dm.config.override(...)` is a context manager", False),
    ],
)
def test_the_pattern(text: str, bare: bool) -> None:
    assert bool(_BARE.search(text)) is bare


def test_no_bare_override_call_in_shipped_text() -> None:
    found = [
        f"{path.relative_to(_REPO)}:{number}: {line.strip()}"
        for path in _shipped()
        for number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), 1
        )
        if _BARE.search(line)
    ]
    assert found == [], "write `with dm.config.override(...):`\n" + "\n".join(
        found
    )
