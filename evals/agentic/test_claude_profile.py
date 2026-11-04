"""Selected Claude profiles retain subscription identity without exposing context.

These checks use synthetic files and Python children, never a host model call.
Run explicitly with ``pytest evals/agentic/test_claude_profile.py``.
"""

import json
import random
import shutil
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run as runner


def config():
    """Capture the same per-run configuration as the CLI without launching it."""
    return runner.config_from(
        Namespace(
            claude_model="synthetic",
            codex_model="synthetic",
            claude_effort="high",
            codex_effort="high",
            max_turns=20,
            max_budget_usd=5,
            timeout=300,
            codex_token_budget=1000,
            codex_no_subagents=True,
            python="3.12",
            hide_grading=True,
            codex_home=None,
        )
    )


@pytest.fixture
def profiles(tmp_path, monkeypatch):
    """Keep all profile bytes synthetic, including distinct default credentials."""
    user = tmp_path / "user"
    selected = user / "selected-claude"
    default = user / ".claude"
    for root in (selected, default):
        root.mkdir(parents=True)
        (root / ".credentials.json").write_text("synthetic-" + root.name)
        (root / "projects").mkdir()
        (root / "projects" / "old.jsonl").write_text("prior session")
        (root / "history.jsonl").write_text("prior history")
        (root / "skills" / "user-skill").mkdir(parents=True)
        (root / "skills" / "user-skill" / "SKILL.md").write_text("global skill")
        (root / "CLAUDE.md").write_text("global instructions")
    monkeypatch.setenv("HOME", str(user))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(selected))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "synthetic-api-key")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "synthetic-auth-token")
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-other-key")
    return selected, default


def test_selected_profile_survives_allowlist_without_payment_credentials(
    tmp_path, profiles
):
    """The launcher preserves only the selected profile, not ambient API keys."""
    env = runner.base_env(tmp_path)
    child = subprocess.run(
        [
            sys.executable,
            "-c",
            "import os,json; print(json.dumps(dict(os.environ)))",
        ],
        env=env,
        capture_output=True,
        text=True,
        check=True,
        timeout=20,
    )
    observed = json.loads(child.stdout)
    assert observed.get("CLAUDE_CONFIG_DIR") == str(profiles[0])
    assert (
        not {"ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "OPENAI_API_KEY"}
        & observed.keys()
    )


def test_selected_instruction_sources_are_excluded_and_reported(profiles):
    """The selected and default CLAUDE.md sources include symlink targets."""
    selected, default = profiles
    target = selected.parent / "shared-instructions.md"
    target.write_text("shared instructions")
    (selected / "CLAUDE.md").unlink()
    (selected / "CLAUDE.md").symlink_to(target)
    cfg = config()
    command = runner.claude_cmd("synthetic request", cfg)
    excluded = json.loads(command[command.index("--settings") + 1])[
        "claudeMdExcludes"
    ]
    assert str(selected / "**") in excluded
    assert str(default / "**") in excluded
    assert str(target) in excluded
    context = runner.host_context("claude", Path("/unused"), selected)
    assert context[str(selected / "CLAUDE.md")] == "present, excluded"


def test_profile_selection_does_not_allow_unrelated_environment_keys(
    tmp_path, monkeypatch, profiles
):
    """Seeded arbitrary credential names stay outside the child allowlist."""
    rng = random.Random(527)
    keys = {
        prefix + "_" + "".join(rng.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=12))
        for prefix in ("ANTHROPIC", "CLAUDE", "OPENAI", "SECRET")
        for _ in range(8)
    }
    for key in keys:
        monkeypatch.setenv(key, "synthetic-credential")
    env = runner.base_env(tmp_path)
    assert keys.isdisjoint(env), "seed=527"
    assert env["CLAUDE_CONFIG_DIR"] == str(profiles[0])


@pytest.mark.parametrize(
    "source", ["selected", "default", "explicit-default", "fresh"]
)
def test_exact_launch_isolates_profile_stores_and_preserves_bytes(
    tmp_path, monkeypatch, profiles, source
):
    """The actual bwrap child sees selected identity and no prior context."""
    if not shutil.which("bwrap"):
        pytest.skip("requires the eval harness's bwrap dependency")
    selected, default = profiles
    shared = tmp_path / "shared"
    shared.mkdir()
    if source == "selected":
        for name in ("projects", "skills"):
            (selected / name).rename(shared / name)
            (selected / name).symlink_to(
                shared / name, target_is_directory=True
            )
        (selected / "history.jsonl").rename(shared / "history.sqlite")
        (selected / "history.jsonl").symlink_to(shared / "history.sqlite")
        (selected / "CLAUDE.md").rename(shared / "CLAUDE.md")
        (selected / "CLAUDE.md").symlink_to(shared / "CLAUDE.md")
    elif source == "default":
        monkeypatch.delenv("CLAUDE_CONFIG_DIR")
        selected = default
    elif source == "explicit-default":
        selected = default
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(selected))
    else:
        selected = selected.parent / "fresh"
        selected.mkdir()
        (selected / ".credentials.json").write_text("synthetic-fresh")
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(selected))
    cfg = config()
    # Resolve selection before the ambient environment can change between units.
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "wrong-profile"))
    project = tmp_path / "work" / "opaque"
    project.mkdir(parents=True)
    unit = tmp_path / "records" / "run" / "claude" / "synthetic" / "noskill-r1"
    (project / "local.txt").write_text("own project")
    expected = (selected / ".credentials.json").read_text()
    script = (
        """
import json, os
from pathlib import Path
selected = Path(os.environ.get('CLAUDE_CONFIG_DIR', Path.home() / '.claude'))
assert ('CLAUDE_CONFIG_DIR' in os.environ) == PROFILE_SELECTED
assert selected.joinpath('.credentials.json').read_text() == EXPECTED
assert not any(k in os.environ for k in ('ANTHROPIC_API_KEY','ANTHROPIC_AUTH_TOKEN','OPENAI_API_KEY'))
for root in (selected, Path.home() / '.claude', SHARED):
    assert not (root / 'projects' / 'old.jsonl').exists(), str(root)
    assert not (root / 'skills' / 'user-skill' / 'SKILL.md').exists(), str(root)
    assert not (root / 'history.jsonl').read_text() if (root / 'history.jsonl').exists() else True
    assert not (root / 'CLAUDE.md').read_text() if (root / 'CLAUDE.md').exists() else True
assert Path('local.txt').read_text() == 'own project'
print(json.dumps({'type':'assistant','message':{'content':[{'type':'tool_use','name':'Read','input':{'file_path':str(selected / 'projects' / 'old.jsonl')}}]}}))
""".replace("PROFILE_SELECTED", repr(source != "default"))
        .replace("EXPECTED", repr(expected))
        .replace("SHARED", "Path(" + repr(str(shared)) + ")")
    )

    def prepare(case, child_project, *args):
        """Reuse synthetic input instead of installing a wheel."""
        child_project.mkdir(parents=True)
        (child_project / "local.txt").write_text("own project")
        return {}

    def run_host(argv, cwd, env, child_unit, *args):
        """Replace the model executable only; retain real environment and mounts."""
        child = subprocess.run(
            [
                *argv[: argv.index("--") + 1],
                str(Path(sys.executable).resolve()),
                "-c",
                script,
            ],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
        )
        assert child.returncode == 0, child.stderr
        (child_unit / "transcript.jsonl").write_text(child.stdout)
        raise RuntimeError(
            "synthetic launch verified; stop before artifact grading"
        )

    monkeypatch.setattr(runner, "prepare", prepare)
    monkeypatch.setattr(runner, "run_host", run_host)
    args = Namespace(
        work_root=tmp_path / "work",
        skill_dir=None,
        codex_home=None,
        dry_run=False,
    )
    case = {
        "id": "synthetic",
        "kind": "generate",
        "lang": "en",
        "held_out": False,
        "prompt": "Synthetic request",
    }
    meta = {
        "wheel": {"name": "synthetic.whl", "sha256": "0" * 64},
        "versions": {"claude": "synthetic"},
    }
    record = runner.one(
        (case, "claude", "noskill", 1), unit.parents[2], args, cfg, meta
    )
    assert (
        record.get("harness_error")
        == "RuntimeError: synthetic launch verified; stop before artifact grading"
    )
    assert record.get("claude_config_dir") == str(selected)
    assert str(selected / "projects") in record["transcript_stores"]
    assert str((selected / "projects").resolve()) in record["transcript_stores"]
    assert runner.recheck_contamination(record, unit)["contaminated"]
    for root in {default, selected} - (
        {selected} if source == "fresh" else set()
    ):
        assert (root / "projects" / "old.jsonl").read_text() == "prior session"
        assert (root / "history.jsonl").read_text() == "prior history"
        assert (root / "CLAUDE.md").read_text() == "global instructions"
        assert (
            root / "skills" / "user-skill" / "SKILL.md"
        ).read_text() == "global skill"
    assert (selected / ".credentials.json").read_text() == expected


def test_persisted_resolved_store_roots_survive_environment_and_symlink_changes(
    tmp_path, monkeypatch, profiles
):
    """Replay recognizes the original store after selection and aliases change."""
    selected, _ = profiles
    old = tmp_path / "original-transcripts"
    (selected / "projects").rename(old)
    (selected / "projects").symlink_to(old, target_is_directory=True)
    stores = runner.host_transcript_stores(tmp_path / "codex", selected)
    unit = tmp_path / "records" / "run" / "claude" / "synthetic" / "noskill-r1"
    unit.mkdir(parents=True)
    (unit / "transcript.jsonl").write_text(
        json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Read",
                            "input": {"file_path": str(old / "old.jsonl")},
                        }
                    ]
                },
            }
        )
        + "\n"
    )
    rec = {
        "project": str(tmp_path / "work" / "opaque"),
        "host": "claude",
        "transcript_stores": stores,
    }
    (selected / "projects").unlink()
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "another-profile"))
    assert runner.recheck_contamination(rec, unit)["contaminated"]


def test_codex_sqlite_symlink_remains_available_to_the_host(tmp_path, profiles):
    """Resolving transcript aliases must preserve Codex's sqlite exception."""
    if not shutil.which("bwrap"):
        pytest.skip("requires the eval harness's bwrap dependency")
    home = tmp_path / "codex"
    home.mkdir()
    target = tmp_path / "synthetic-database"
    target.write_text("synthetic sqlite bytes")
    (home / "state.sqlite").symlink_to(target)
    project = tmp_path / "project"
    project.mkdir()
    mounts, _ = runner.home_store_mounts("codex", tmp_path / "stores", home)
    child = subprocess.run(
        runner.sandbox_wrap(
            [
                str(Path(sys.executable).resolve()),
                "-c",
                "from pathlib import Path; assert Path("
                + repr(str(target))
                + ").read_text() == 'synthetic sqlite bytes'",
            ],
            project,
            [],
            mounts,
        ),
        env=runner.base_env(project, {"CODEX_HOME": str(home)}),
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert child.returncode == 0, child.stderr
    assert target.read_text() == "synthetic sqlite bytes"
