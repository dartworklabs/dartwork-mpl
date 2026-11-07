"""The pre-commit ruff pin follows the ruff version locked in ``uv.lock``.

Dependabot's uv ecosystem moves ``uv.lock`` but does not look at
``.pre-commit-config.yaml``, so the hook's ``rev`` drifts unless a test
compares the two. A drift makes ``pre-commit`` and ``uv run ruff`` disagree on
lint and format results.
"""

import tomllib
from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parents[2]
_RUFF_HOOK_REPO = "https://github.com/astral-sh/ruff-pre-commit"


def _locked_ruff_versions() -> set[str]:
    """Return every ruff version ``uv.lock`` pins, one per marker branch."""
    lock = tomllib.loads((_ROOT / "uv.lock").read_text(encoding="utf-8"))
    return {
        package["version"]
        for package in lock["package"]
        if package["name"] == "ruff"
    }


def _hook_ruff_rev() -> str:
    """Return the ruff-pre-commit ``rev`` without its leading ``v``."""
    config = yaml.safe_load(
        (_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    )
    (rev,) = [
        repo["rev"]
        for repo in config["repos"]
        if repo["repo"] == _RUFF_HOOK_REPO
    ]
    return rev.removeprefix("v")


def test_precommit_ruff_rev_matches_the_locked_ruff_version() -> None:
    """A lock bump that leaves the hook behind fails with both values."""
    locked = _locked_ruff_versions()
    assert len(locked) == 1, f"uv.lock pins several ruff versions: {locked}"
    (version,) = locked
    rev = _hook_ruff_rev()
    assert rev == version, (
        f".pre-commit-config.yaml pins ruff-pre-commit rev v{rev} but uv.lock "
        f"locks ruff {version}. Set the ruff-pre-commit `rev:` in "
        f".pre-commit-config.yaml to v{version} (or re-lock ruff to {rev})."
    )
