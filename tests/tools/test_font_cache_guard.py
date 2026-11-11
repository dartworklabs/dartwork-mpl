"""The font-cache guard fails a session that changes an inventory it did not own.

Each end-to-end case runs a real pytest session in a fresh interpreter with
``MPLCONFIGDIR`` pointing at ``tmp_path``, so the developer's own cache is
never the subject of the test.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

from tests.support.font_cache_guard import (
    changed_font_caches,
    font_cache_digests,
)

_ROOT = Path(__file__).resolve().parents[2]
_INVENTORY = "fontlist-v3.11.0.json"


def _run_session(
    tmp_path: Path, test_body: str, *, seeded: bool
) -> subprocess.CompletedProcess[str]:
    """Run one inner pytest session with the guard and an isolated cache dir."""
    cache = tmp_path / "mplconfig"
    cache.mkdir()
    if seeded:
        (cache / _INVENTORY).write_text('{"seed": true}', encoding="utf-8")
    project = tmp_path / "project"
    project.mkdir()
    (project / "test_inner.py").write_text(
        textwrap.dedent(test_body), encoding="utf-8"
    )
    # Its own ini file makes the project the root and the conftest cut-off,
    # so collection starts here and never scans the directories above.
    (project / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    environment = {
        **os.environ,
        "MPLCONFIGDIR": str(cache),
        "PYTHONPATH": str(_ROOT),
    }
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "tests.support.font_cache_guard",
            "-p",
            "no:cacheprovider",
            "--rootdir",
            str(project),
            "-c",
            str(project / "pytest.ini"),
            str(project / "test_inner.py"),
        ],
        cwd=project,
        env=environment,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=120,
        check=False,
    )


_REWRITE = """
    import os
    from pathlib import Path

    def test_rewrites_inventory():
        cache = Path(os.environ["MPLCONFIGDIR"])
        (cache / "fontlist-v3.11.0.json").write_text("{}", encoding="utf-8")
"""

_DELETE = """
    import os
    from pathlib import Path

    def test_deletes_inventory():
        (Path(os.environ["MPLCONFIGDIR"]) / "fontlist-v3.11.0.json").unlink()
"""

_LEAVES_ALONE = """
    def test_passes():
        assert True
"""


def test_session_fails_and_names_the_file_when_a_test_rewrites_an_inventory(
    tmp_path: Path,
) -> None:
    """A passing test that rewrites an existing inventory turns the session red."""
    result = _run_session(tmp_path, _REWRITE, seeded=True)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "1 passed" in result.stdout
    assert str(tmp_path / "mplconfig" / _INVENTORY) in result.stdout


def test_session_fails_when_a_test_deletes_an_inventory(tmp_path: Path) -> None:
    """Removing an inventory that existed at the start is also a change."""
    result = _run_session(tmp_path, _DELETE, seeded=True)

    assert result.returncode == 1, result.stdout + result.stderr
    assert str(tmp_path / "mplconfig" / _INVENTORY) in result.stdout


def test_session_passes_when_the_inventory_is_untouched(tmp_path: Path) -> None:
    """The guard is silent when nothing changed."""
    result = _run_session(tmp_path, _LEAVES_ALONE, seeded=True)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "font cache changed" not in result.stdout


def test_session_passes_when_an_inventory_is_first_created(
    tmp_path: Path,
) -> None:
    """Matplotlib building a cache that did not exist is not a violation."""
    result = _run_session(tmp_path, _REWRITE, seeded=False)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "font cache changed" not in result.stdout


def test_digests_cover_only_font_inventories(tmp_path: Path) -> None:
    """Only ``fontlist-v*.json`` files are measured, keyed by their path."""
    inventory = tmp_path / _INVENTORY
    inventory.write_text("a", encoding="utf-8")
    (tmp_path / "tex.cache").write_text("b", encoding="utf-8")

    assert list(font_cache_digests(tmp_path)) == [str(inventory)]


def test_changed_reports_modified_and_missing_but_not_new() -> None:
    """A different or absent digest is a change; a path new in ``after`` is not."""
    before = {"kept": "1", "edited": "1", "removed": "1"}
    after = {"kept": "1", "edited": "2", "created": "1"}

    assert changed_font_caches(before, after) == ["edited", "removed"]


def test_inner_session_does_not_collect_outside_its_project(
    tmp_path: Path,
) -> None:
    """The inner run never scans the directories above its project.

    With ``-c /dev/null`` pytest cut conftest discovery at ``/dev`` and walked
    every ancestor of the test file from the filesystem root, so one entry it
    could not stat anywhere above (another user's directory in a shared
    ``/tmp`` on a CI runner) failed collection with exit code 4.
    """
    locked = tmp_path / "locked"
    locked.mkdir()
    (locked / "inner").write_text("x", encoding="utf-8")
    (tmp_path / "unreadable").symlink_to(locked / "inner")
    locked.chmod(0)
    try:
        result = _run_session(tmp_path, _LEAVES_ALONE, seeded=True)
    finally:
        locked.chmod(0o700)

    assert result.returncode == 0, result.stdout + result.stderr
