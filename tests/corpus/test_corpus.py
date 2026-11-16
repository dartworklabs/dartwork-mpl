"""Every corpus script runs from an empty directory without raising."""

from __future__ import annotations

import runpy
from pathlib import Path

import matplotlib.pyplot as plt
import pytest

HERE = Path(__file__).resolve().parent
SCRIPTS = sorted([*HERE.glob("charts/*.py"), *HERE.glob("rough/*.py")])


@pytest.mark.parametrize(
    "script", SCRIPTS, ids=[f"{p.parent.name}/{p.stem}" for p in SCRIPTS]
)
def test_script_runs(
    script: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    try:
        with plt.rc_context():
            runpy.run_path(str(script), run_name="__main__")
    finally:
        plt.close("all")
