from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = REPO_ROOT / "examples"
EXAMPLES = sorted(EXAMPLES_DIR.glob("*.py"))


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda path: path.name)
def test_example_script_smoke(example: Path) -> None:
    env = os.environ.copy()
    src_path = str(REPO_ROOT / "src")
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        src_path
        if not existing_pythonpath
        else os.pathsep.join((src_path, existing_pythonpath))
    )
    env["MPLBACKEND"] = "Agg"

    result = subprocess.run(
        [sys.executable, str(example)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        stderr_tail = "\n".join(result.stderr.splitlines()[-40:])
        pytest.fail(
            f"{example.name} exited with {result.returncode}\n\n"
            f"Last 40 lines of stderr:\n{stderr_tail}"
        )
