"""Determinism + drift gate for the committed build artifact."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from dartwork_mpl.colors import _generated


def test_generated_tables_shape():
    assert len(_generated.PALETTE) == 16
    assert all(len(row) == 10 for row in _generated.PALETTE.values())
    assert set(_generated.CYCLES) == {"default", "print"}
    assert len(_generated.CMAPS_256) == 42
    assert all(len(v) == 256 for v in _generated.CMAPS_256.values())


def test_generated_matches_ssot_palette(v5_ssot):
    for fam, row in v5_ssot["palette"].items():
        assert list(_generated.PALETTE[fam]) == row, fam


def test_rebuild_is_byte_identical(tmp_path):
    src = Path("src/dartwork_mpl/colors/_generated.py")
    before = src.read_bytes()
    env = dict(os.environ)
    # Isolation: force the subprocess interpreter to resolve
    # `dartwork_mpl` from *this* worktree's src, not the shared venv's
    # editable-install target (a sibling clone). Without this, the
    # rebuild would target the wrong package copy entirely.
    src_dir = str(Path("src").resolve())
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        f"{src_dir}{os.pathsep}{existing}" if existing else src_dir
    )
    r = subprocess.run(
        [sys.executable, "-m", "dartwork_mpl.colors._build"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert src.read_bytes() == before, (
        "rebuild drifted — nondeterminism or stale commit"
    )
