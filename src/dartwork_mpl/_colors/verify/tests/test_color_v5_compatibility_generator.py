"""Regenerate the frozen v5 compatibility manifest and compare raw bytes.

``scripts/freeze_color_v5_compatibility.py`` reads its listed baseline files
by exact path from the accepted commit and writes only to ``--output``. This
runs it once, end to end, into a file the test owns, and requires the result
to be byte-for-byte the accepted fixture. The fixture is read through the
approved-input reader, so its bytes are also checked against the existing
source pin.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from tests.support.approved_inputs import read_approved_bytes

REPO_ROOT = Path(__file__).resolve().parents[5]
GENERATOR_PATH = REPO_ROOT / "scripts/freeze_color_v5_compatibility.py"
COMPATIBILITY_INPUT = (
    "docs/superpowers/specs/assets/2026-07-14-oklab-centered-color-system/"
    "color_v5_compatibility.json"
)
BASELINE_COMMIT = "12d16bac22dee790bd0696ca92a814a797dc728b"


# Not ``approved_input``: the generator reads its listed baseline files
# (``BASELINE_RUNTIME_INPUTS``) by exact path from the accepted commit, so it
# needs full Git history and runs in the full-history ``test`` job only. Every
# output, including the baseline files it extracts, stays below ``tmp_path``,
# and the child runs from an empty folder there, not from the repository.
@pytest.mark.color_pipeline
def test_generator_rebuilds_the_accepted_bytes_without_candidate_code(
    tmp_path: Path,
) -> None:
    """One owned run matches the fixture; a wrong commit is refused."""
    owned_temporary = tmp_path / "generator-tmp"
    owned_temporary.mkdir()
    workdir = tmp_path / "cwd"
    workdir.mkdir()
    # A candidate ``dartwork_mpl`` ahead of everything else on PYTHONPATH:
    # the generator itself must not import the package, and its probe runs
    # under ``python -I``, which ignores PYTHONPATH.
    import_trap = tmp_path / "import-trap" / "dartwork_mpl"
    import_trap.mkdir(parents=True)
    (import_trap / "__init__.py").write_text(
        "raise RuntimeError('candidate package import is forbidden')\n",
        encoding="utf-8",
    )
    environment = {
        **os.environ,
        "TMPDIR": str(owned_temporary),
        "PYTHONPATH": str(import_trap.parent),
    }
    output = tmp_path / "compatibility.json"

    completed = subprocess.run(
        [
            sys.executable,
            str(GENERATOR_PATH),
            "--baseline-commit",
            BASELINE_COMMIT,
            "--output",
            str(output),
        ],
        cwd=workdir,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout == f"wrote {output.resolve()}\n"
    assert output.read_bytes() == read_approved_bytes(COMPATIBILITY_INPUT)
    # The extracted baseline inputs lived in a temporary directory below the
    # owned TMPDIR and are gone once the run finishes; the child's working
    # folder is left as it was.
    assert list(owned_temporary.iterdir()) == []
    assert list(workdir.iterdir()) == []

    bad = tmp_path / "bad.json"
    refused = subprocess.run(
        [
            sys.executable,
            str(GENERATOR_PATH),
            "--baseline-commit",
            f"{BASELINE_COMMIT}^",
            "--output",
            str(bad),
        ],
        cwd=workdir,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert refused.returncode == 2
    assert re.fullmatch(
        "compatibility baseline error: baseline commit must resolve to "
        f"{BASELINE_COMMIT}; got [0-9a-f]{{40}}\n",
        refused.stderr,
    )
    assert refused.stdout == ""
    assert not bad.exists()
    assert list(owned_temporary.iterdir()) == []
    assert list(workdir.iterdir()) == []
