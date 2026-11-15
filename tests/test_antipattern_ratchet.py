"""Hold anti-patterns in the repository's own plotting code to a count that only goes down.

The examples, docs scripts and bundled templates are what users and AI agents
copy, so they should follow the anti-pattern catalog like any user code. They
don't yet. Instead of fixing every file at once, this test lints each tracked
file with :func:`dartwork_mpl.lint_code` and compares its count of critical and
warning issues with ``antipattern_baseline.json``:

* a file with more issues than its baseline fails — new code must be clean;
* a file with fewer fails too, until the baseline is lowered, so a fixed issue
  can't creep back;
* a file not in the baseline has a baseline of 0.

``info`` rules (``plt-show-only`` and friends) are hints, not violations, and
are not counted. ``tests/`` and ``evals/`` show anti-patterns on purpose, and library code in
``src/dartwork_mpl/`` is not user plotting code, so both are out of scope —
except the bundled templates under ``guide/assets/``.

After fixing issues, lower the baseline with::

    uv run python tests/test_antipattern_ratchet.py --update

Never run ``--update`` to make a count go up.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

from dartwork_mpl import lint_code

ROOT = Path(__file__).resolve().parents[1]
BASELINE = Path(__file__).with_name("antipattern_baseline.json")
COUNTED = ("critical", "warning")


def in_scope(path: str) -> bool:
    """Whether a tracked ``.py`` path is plotting code users may copy."""
    # evals/ holds evaluation fixtures, including deliberately bad control
    # figures that must keep their anti-patterns; tests/ shows them on purpose.
    if path.startswith(("tests/", "evals/")):
        return False
    if path.startswith("src/dartwork_mpl/"):
        return path.startswith("src/dartwork_mpl/guide/assets/")
    return True


def tracked_files() -> list[str]:
    """Tracked ``.py`` files in scope, as repo-relative POSIX paths.

    A tracked file deleted in the working tree is code nobody can copy any
    more, so it is not linted.
    """
    listed = subprocess.run(
        ["git", "ls-files", "-z", "--", "*.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return sorted(
        p
        for p in listed.split("\0")
        if p and in_scope(p) and (ROOT / p).is_file()
    )


def issue_counts() -> dict[str, int]:
    """Critical and warning issues per in-scope file; clean files are omitted."""
    counts = {}
    for path in tracked_files():
        source = (ROOT / path).read_text(encoding="utf-8")
        n = sum(1 for i in lint_code(source) if i.severity in COUNTED)
        if n:
            counts[path] = n
    return counts


def compare(
    counts: Mapping[str, int], baseline: Mapping[str, int]
) -> list[str]:
    """One line per file whose count differs from its baseline (0 if unlisted)."""
    out = []
    for path in sorted(set(counts) | set(baseline)):
        now, base = counts.get(path, 0), baseline.get(path, 0)
        if now > base:
            out.append(
                f"{path}: {now} issues, baseline {base} — fix the new ones "
                "(`dartwork_mpl.lint_code` lists them)"
            )
        elif now < base:
            out.append(
                f"{path}: {now} issues, baseline {base} — lower the baseline "
                "(`uv run python tests/test_antipattern_ratchet.py --update`)"
            )
    return out


def test_antipattern_counts_match_baseline() -> None:
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    problems = compare(issue_counts(), baseline)
    assert not problems, "\n".join(problems)


if __name__ == "__main__":
    counts = issue_counts()
    if "--update" in sys.argv:
        BASELINE.write_text(
            json.dumps(counts, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(
            f"wrote {BASELINE.name}: {sum(counts.values())} issues "
            f"in {len(counts)} files"
        )
    else:
        problems = compare(
            counts, json.loads(BASELINE.read_text(encoding="utf-8"))
        )
        print("\n".join(problems) or "anti-pattern counts match the baseline")
        sys.exit(1 if problems else 0)
