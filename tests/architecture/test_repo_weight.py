"""The repository stays light: rendered output never goes into git.

Git keeps every version of a binary file for ever, so committed figures are
what made this repository's history 600 MB. The only binaries tracked are the
bundled fonts and the pixel baselines; everything a run renders (eval figures,
docs images, wheels) stays untracked.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BINARY = frozenset(
    {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".svgz", ".eps"}
    | {".ttf", ".otf", ".woff", ".woff2", ".zip", ".whl", ".gz", ".npy"}
)
ALLOWED = ("src/dartwork_mpl/font/assets/", "tests/visual/baseline/")
BASELINE_CAP = 3 * 1024 * 1024  # all pixel baselines together
FILE_CAP = 1024 * 1024  # any one tracked file outside the fonts
REST_CAP = 8 * 1024 * 1024  # everything tracked outside the fonts


def tracked() -> list[Path]:
    """Every tracked file still on disk, or a skip outside a git checkout."""
    done = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if done.returncode != 0:
        pytest.skip("not a git checkout")
    paths = (Path(name) for name in done.stdout.split("\0") if name)
    return [p for p in paths if (ROOT / p).is_file()]


def size(path: Path) -> int:
    return (ROOT / path).stat().st_size


def test_binaries_live_only_in_fonts_and_pixel_baselines():
    strays = [
        str(p)
        for p in tracked()
        if p.suffix.lower() in BINARY and not str(p).startswith(ALLOWED)
    ]
    assert not strays, (
        "rendered or binary files are tracked; keep them out of git: "
        + ", ".join(strays)
    )


def test_tracked_files_stay_small():
    files = tracked()
    rest = [p for p in files if not str(p).startswith(ALLOWED[0])]
    big = [f"{p} ({size(p) // 1024} KiB)" for p in rest if size(p) > FILE_CAP]
    assert not big, "a tracked file is over 1 MiB: " + ", ".join(big)
    baselines = sum(size(p) for p in files if str(p).startswith(ALLOWED[1]))
    assert baselines <= BASELINE_CAP, (
        f"pixel baselines weigh {baselines // 1024} KiB; every regeneration "
        "adds that much to history for ever, so keep scenarios few and small"
    )
    total = sum(size(p) for p in rest)
    assert total <= REST_CAP, (
        f"tracked files outside the fonts: {total // 1024} KiB"
    )
