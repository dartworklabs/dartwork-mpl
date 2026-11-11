"""Fail the test session when it changes a matplotlib font inventory it did not own.

Matplotlib keeps one ``fontlist-v*.json`` per cache directory and every later
process trusts it. A test that rewrites the developer's real inventory makes
unrelated font tests fail from the *next* run on, far from the cause (#668:
on macOS ``XDG_CACHE_HOME`` does not move the cache, so a test that believed
it wrote to ``tmp_path`` wrote to ``~/.matplotlib``). CI runs on Linux with a
per-run ``MPLCONFIGDIR`` and never saw it.

The guard hashes the inventories when the session starts and again when it
ends. An inventory that existed at the start and is different or gone at the
end fails the session and names the file. One that is first created during
the session is matplotlib building its cache and is allowed.

Loaded from the root ``conftest.py``; with pytest-xdist only the controller
measures, since every worker shares the same cache directory.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import matplotlib as mpl
import pytest

_START_DIGESTS = pytest.StashKey[dict[str, str]]()
_CHANGED = pytest.StashKey[list[str]]()


def font_cache_digests(cache_dir: Path) -> dict[str, str]:
    """SHA-256 of each font inventory in ``cache_dir``, keyed by its path."""
    return {
        str(path): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(cache_dir.glob("fontlist-v*.json"))
    }


def changed_font_caches(
    before: dict[str, str], after: dict[str, str]
) -> list[str]:
    """Inventories present in ``before`` whose content differs or is gone in ``after``."""
    return [
        path for path, digest in before.items() if after.get(path) != digest
    ]


def _is_xdist_worker(config: pytest.Config) -> bool:
    return hasattr(config, "workerinput")


def pytest_sessionstart(session: pytest.Session) -> None:
    """Record the inventories before any test runs."""
    if _is_xdist_worker(session.config):
        return
    session.config.stash[_START_DIGESTS] = font_cache_digests(
        Path(mpl.get_cachedir())
    )


@pytest.hookimpl(tryfirst=True)
def pytest_sessionfinish(session: pytest.Session) -> None:
    """Fail the session if an inventory that existed at the start was changed."""
    before = session.config.stash.get(_START_DIGESTS, None)
    if before is None:
        return
    changed = changed_font_caches(
        before, font_cache_digests(Path(mpl.get_cachedir()))
    )
    session.config.stash[_CHANGED] = changed
    if changed and session.exitstatus == pytest.ExitCode.OK:
        session.exitstatus = pytest.ExitCode.TESTS_FAILED


def pytest_terminal_summary(
    terminalreporter: pytest.TerminalReporter, config: pytest.Config
) -> None:
    """Name the changed inventories and how to recover."""
    changed = config.stash.get(_CHANGED, [])
    if not changed:
        return
    terminalreporter.section("matplotlib font cache changed", sep="=", red=True)
    for path in changed:
        terminalreporter.line(f"changed during this session: {path}", red=True)
    terminalreporter.line(
        "A test (or a process it started) rewrote a font inventory outside "
        "its own temporary directory. Point it at tmp_path with MPLCONFIGDIR; "
        "delete the file above to let matplotlib rebuild it.",
        red=True,
    )
