"""Compare a wheel's complete package payload with the tracked release inputs.

Run from the repository root after building the wheel. The exclusions and forced
indexes below mirror pyproject.toml; packaging tests exercise that build policy
through the actual release shell. Requires only Python 3.10's standard library.
"""

import argparse
import difflib
import subprocess
import sys
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath


def expected_members(tracked: list[str]) -> set[str]:
    """Keep tracked package files except the declared colocated-test exclusions."""
    expected = set()
    for name in tracked:
        path = PurePosixPath(name)
        # wheel.exclude: **/tests/**, **/test_*.py, **/conftest.py
        if (
            "tests" in path.parts
            or (path.name.startswith("test_") and path.suffix == ".py")
            or path.name == "conftest.py"
        ):
            continue
        expected.add(name.removeprefix("src/"))
    # wheel.force-include: the consumer AGENTS/CLAUDE entries above remain
    # ordinary tracked package data and must not be excluded from parity.
    expected.update(
        {
            "dartwork_mpl/asset/agent/llms.txt",
            "dartwork_mpl/asset/agent/llms-full.txt",
        }
    )
    return expected


def main() -> int:
    """Check the local git index and ZIP; print a diff and fail on any mismatch."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    args = parser.parse_args()
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z", "--", "src/dartwork_mpl"],
            check=True,
            capture_output=True,
            text=True,
        )
        tracked = [name for name in result.stdout.split("\0") if name]
        if not tracked:
            print(
                "No tracked src/dartwork_mpl files; run from the repository root.",
                file=sys.stderr,
            )
            return 1
        expected = expected_members(tracked)
        with zipfile.ZipFile(args.wheel) as archive:
            members = [
                entry.filename
                for entry in archive.infolist()
                if entry.filename.startswith("dartwork_mpl/")
                and not entry.is_dir()
            ]
    except (OSError, subprocess.CalledProcessError, zipfile.BadZipFile) as exc:
        print(f"Cannot check wheel payload: {exc}", file=sys.stderr)
        return 1

    duplicates = sorted(
        name for name, count in Counter(members).items() if count > 1
    )
    actual = set(members)
    if actual != expected or duplicates:
        print(
            "Wheel payload differs from tracked package release inputs:",
            file=sys.stderr,
        )
        sys.stderr.writelines(
            difflib.unified_diff(
                [name + "\n" for name in sorted(expected)],
                [name + "\n" for name in sorted(actual)],
                fromfile="expected-package",
                tofile="wheel-package",
            )
        )
        if duplicates:
            print(
                "Duplicate package members: " + ", ".join(duplicates),
                file=sys.stderr,
            )
        return 1
    print(
        f"Wheel payload matches {len(expected)} tracked/force-included package files."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
