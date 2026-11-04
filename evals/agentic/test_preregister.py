"""Prelaunch records preserve the original population and reject changed inputs."""

import hashlib
import json
import os
import random
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import preregister  # noqa: E402


def _sha(path: Path) -> str:
    """Hash a small test input without relying on the implementation's helper."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(repo: Path, *args: str) -> str:
    """Operate only on the tiny disposable repository owned by this test."""
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=True, stdin=subprocess.DEVNULL
    ).strip()


@pytest.fixture
def registration(tmp_path, monkeypatch):
    """Supply explicit real-file inputs and a clean disposable harness commit."""
    repo = tmp_path / "repo"
    cases = repo / "evals" / "agentic" / "cases"
    cases.mkdir(parents=True)
    for original in (HERE / "cases").glob("*.yaml"):
        (cases / original.name).write_text("[deliberately invalid YAML\n")
    (cases.parent / "compare.py").write_text(
        'PREREGISTERED = "Frozen test endpoints; no grading module import."\n'
    )
    _git(repo, "init", "-q")
    _git(repo, "add", ".")
    _git(
        repo,
        "-c",
        "user.name=fixture",
        "-c",
        "user.email=fixture@localhost",
        "commit",
        "-qm",
        "fixture",
    )
    wheel = tmp_path / "final.whl"
    wheel.write_bytes(b"a final wheel's exact bytes")
    evidence = tmp_path / "runtime-receipt.json"
    evidence.write_text(
        '{"verified_subscriptions": true, "latest_models": true}\n'
    )
    home = tmp_path / "authenticated-codex-home"
    home.mkdir()
    host_bin = tmp_path / "host-bin"
    host_bin.mkdir()
    for host in ("claude", "codex"):
        executable = host_bin / host
        executable.write_text(
            f"#!{sys.executable}\nimport sys\n"
            "if sys.argv[1:] != ['--version']: raise SystemExit(2)\n"
            f"print('fixture {host} 1.0')\n"
        )
        executable.chmod(0o755)
    monkeypatch.setenv(
        "PATH", str(host_bin) + os.pathsep + os.environ.get("PATH", "")
    )
    records = tmp_path / "records"
    records.mkdir()
    config = {
        "schema_version": 1,
        "wheel": {"path": str(wheel), "sha256": _sha(wheel)},
        "harness_commit": _git(repo, "rev-parse", "HEAD"),
        "models": {
            host: {
                "id": f"runtime-selected-{host}",
                "effort": "high",
                "host_version": f"fixture {host} 1.0",
            }
            for host in ("claude", "codex")
        },
        "auth": {"codex_home": str(home)},
        "runtime_evidence": {"path": str(evidence), "sha256": _sha(evidence)},
        "budgets": {
            "timeout_s": 300,
            "claude_max_turns": 20,
            "claude_max_budget_usd": 5.0,
            "codex_token_budget": 1500000,
        },
        "execution": {
            "python": sys.executable,
            "project_python": "3.12",
            "records_root": str(records),
            "work_root": str(tmp_path / "work"),
            "run_ids": {
                "primary": "final-primary",
                "supplemental": "final-extra",
            },
            "seeds": {"primary": 20261104, "supplemental": 20261105},
            "reps": 2,
            "jobs": 2,
        },
        "controls": {
            "hide_grading": True,
            "codex_subagents": False,
            "github_mcp_disabled": True,
            "subscription_only": True,
            "latest_generation_verified": True,
            "no_retries": True,
        },
    }
    source = tmp_path / "config.json"
    source.write_text(json.dumps(config))
    return {
        "repo": repo,
        "cases": cases,
        "wheel": wheel,
        "evidence": evidence,
        "home": home,
        "config": config,
        "source": source,
        "record": records / "prelaunch.json",
    }


def _rewrite(registration):
    """Persist an intentionally changed configuration for a boundary check."""
    registration["source"].write_text(json.dumps(registration["config"]))


@pytest.mark.parametrize(
    "location", ["outside", "work", "primary", "supplemental", "symlink"]
)
def test_prelaunch_record_must_be_hidden_outside_official_run_directories(
    registration, location
):
    """No launch record can be exposed or create an official run directory."""
    r = registration
    execution = r["config"]["execution"]
    records = Path(execution["records_root"])
    if location in ("primary", "supplemental"):
        output = records / execution["run_ids"][location] / "prelaunch.json"
    elif location == "work":
        output = Path(execution["work_root"]) / "prelaunch.json"
    elif location == "symlink":
        public = r["source"].parent / "public"
        public.mkdir()
        (records / "escape").symlink_to(public, target_is_directory=True)
        output = records / "escape" / "prelaunch.json"
    else:
        output = r["source"].parent / "visible-prelaunch.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    with pytest.raises(ValueError, match="prelaunch record"):
        preregister.freeze(r["source"], output, r["repo"])
    assert not output.exists()


def test_copied_visible_record_cannot_be_verified_or_emit_launch_argv(
    registration,
):
    """A valid checksum does not authorize exposing the frozen grading record."""
    r = registration
    preregister.freeze(r["source"], r["record"], r["repo"])
    visible = r["source"].parent / "visible-copy.json"
    visible.write_bytes(r["record"].read_bytes())
    for operation in (
        lambda: preregister.verify(visible, r["repo"]),
        lambda: preregister.command(visible, "primary", r["repo"]),
    ):
        with pytest.raises(ValueError, match="prelaunch record"):
            operation()


def test_frozen_record_is_hidden_by_actual_runner_sandbox(registration):
    """The real runner mount order hides the record and retains project input."""
    if not shutil.which("bwrap"):
        pytest.skip("requires the eval harness's bwrap dependency")
    import run as runner

    r = registration
    preregister.freeze(r["source"], r["record"], r["repo"])
    execution = r["config"]["execution"]
    project = Path(execution["work_root"]) / "agent"
    project.mkdir(parents=True)
    (project / "input.txt").write_text("own input")
    script = (
        "from pathlib import Path; "
        f"assert not Path({str(r['record'])!r}).exists(); "
        "assert Path('input.txt').read_text() == 'own input'"
    )
    command = runner.sandbox_wrap(
        [sys.executable, "-c", script],
        project,
        [
            r["repo"],
            Path(execution["records_root"]),
            Path(execution["work_root"]),
        ],
    )
    subprocess.run(
        command,
        cwd=project,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=True,
        timeout=20,
    )
    assert r["record"].is_file()


def test_filename_inventory_has_exact_primary_and_supplemental_partitions(
    registration,
):
    """Invalid YAML bodies are irrelevant to the fixed 40/10 filename roster."""
    cohorts = preregister.inventory(registration["cases"])
    assert len(cohorts["primary"]) == 40
    assert len(cohorts["supplemental"]) == 10
    assert set(cohorts["primary"]).isdisjoint(cohorts["supplemental"])
    assert {x[:3] for x in cohorts["primary"]} == {
        *(f"g{i:02}" for i in range(1, 26)),
        *(f"e{i:02}" for i in range(1, 16)),
    }


@pytest.mark.parametrize(
    "mutation", ["missing", "duplicate", "renamed", "extra"]
)
def test_changed_filename_roster_is_rejected(registration, mutation):
    """A missing, duplicate-prefix, renamed or extra file cannot change the population."""
    cases = registration["cases"]
    original = next(cases.glob("g01-*.yaml"))
    if mutation == "missing":
        original.unlink()
    elif mutation == "renamed":
        original.rename(cases / "g01-new-name.yaml")
    else:
        (
            cases
            / (
                "g01-duplicate.yaml"
                if mutation == "duplicate"
                else "g26-extra.yaml"
            )
        ).touch()
    with pytest.raises(ValueError, match="roster"):
        preregister.inventory(cases)


def test_freeze_has_320_primary_and_80_supplemental_units_with_honest_provenance(
    registration,
):
    """Exposure is separate from declarations; extra cases never enter the primary."""
    r = registration
    record = preregister.freeze(r["source"], r["record"], r["repo"])
    snap = record["snapshot"]
    assert len(snap["cohorts"]["primary"]["planned_units"]) == 320
    assert len(snap["cohorts"]["supplemental"]["planned_units"]) == 80
    provenance = {row["case"][:3]: row for row in snap["provenance"]}
    assert sum(x["declared_held_out"] for x in provenance.values()) == 10
    for prefix in ("e04", "e08", "e10", "e14", "g20"):
        assert provenance[prefix]["declared_held_out"] is True
        assert provenance[prefix]["tuning_exposure"] == "exposed"
    clean = {"g03", "g07", "g11", "g15", "g24"}
    assert {
        p
        for p, row in provenance.items()
        if row["tuning_exposure"] == "not_used_in_v13_v24"
    } == clean
    assert all(provenance[p]["baseline_observed"] is True for p in clean)
    assert snap["analysis_policy"]["supplemental"] == "descriptive_only"
    assert snap["analysis_policy"]["clean_subset"] == "descriptive_only"
    assert preregister.verify(r["record"], r["repo"]) == snap
    assert r["record"].stat().st_mode & 0o222 == 0


def test_seeded_order_matches_runner_loop_for_generated_seeds(registration):
    """Case/host/arm/rep ordering stays reproducible over multiple seeded permutations."""
    cases = preregister.inventory(registration["cases"])["primary"]
    expected = [
        f"{host}/{case}/{arm}-r{rep}"
        for case in sorted(cases)
        for host in ("claude", "codex")
        for arm in ("noskill", "skill")
        for rep in (1, 2)
    ]
    for seed in random.Random(7142).sample(range(100000), 12):
        ordered = preregister.planned_units(cases, seed)
        reference = expected.copy()
        random.Random(seed).shuffle(reference)
        assert ordered == reference
        assert set(ordered) == set(expected)
        assert len(set(ordered)) == 320


@pytest.mark.parametrize(
    "target", ["wheel", "evidence", "source", "endpoint", "harness"]
)
def test_changed_frozen_input_prevents_command_emission(registration, target):
    """A byte change or moved trusted commit invalidates the prelaunch record."""
    r = registration
    preregister.freeze(r["source"], r["record"], r["repo"])
    if target == "harness":
        _git(
            r["repo"],
            "-c",
            "user.name=fixture",
            "-c",
            "user.email=fixture@localhost",
            "commit",
            "--allow-empty",
            "-qm",
            "moved",
        )
    else:
        path = (
            r[target]
            if target != "endpoint"
            else r["cases"].parent / "compare.py"
        )
        with path.open("ab") as stream:
            stream.write(b"\nchanged")
    with pytest.raises(ValueError):
        preregister.command(r["record"], "primary", r["repo"])


@pytest.mark.parametrize("missing", ["wheel", "source", "evidence"])
def test_missing_input_prevents_freeze(registration, missing):
    """Missing inputs are not rebuilt or defaulted into an apparently valid run."""
    r = registration
    r[missing].unlink()
    with pytest.raises(ValueError):
        preregister.freeze(r["source"], r["record"], r["repo"])
    assert not r["record"].exists()


@pytest.mark.parametrize(
    "missing", ["models", "budgets", "auth", "runtime_evidence"]
)
def test_missing_configuration_section_is_rejected(registration, missing):
    """Models, budgets, auth and runtime provenance always require explicit inputs."""
    r = registration
    del r["config"][missing]
    _rewrite(r)
    with pytest.raises(ValueError, match="config"):
        preregister.freeze(r["source"], r["record"], r["repo"])


@pytest.mark.parametrize(
    "control",
    [
        "hide_grading",
        "github_mcp_disabled",
        "subscription_only",
        "latest_generation_verified",
        "no_retries",
    ],
)
def test_disabling_a_required_control_is_rejected(registration, control):
    """Unsafe or unverified evaluation conditions cannot produce launch argv."""
    r = registration
    r["config"]["controls"][control] = False
    _rewrite(r)
    with pytest.raises(ValueError, match="control"):
        preregister.freeze(r["source"], r["record"], r["repo"])


@pytest.mark.parametrize(
    "field,value", [("jobs", 0), ("jobs", 8), ("reps", 1), ("reps", 3)]
)
def test_repetition_and_concurrency_boundaries_are_enforced(
    registration, field, value
):
    """The experiment has two repetitions and bounded explicit concurrency."""
    r = registration
    r["config"]["execution"][field] = value
    _rewrite(r)
    with pytest.raises(ValueError, match=field):
        preregister.freeze(r["source"], r["record"], r["repo"])


def test_existing_record_and_reused_selected_run_are_refused(registration):
    """A frozen record cannot be overwritten and a run cannot be resumed/replaced."""
    r = registration
    preregister.freeze(r["source"], r["record"], r["repo"])
    original = r["record"].read_bytes()
    with pytest.raises(ValueError, match="exists"):
        preregister.freeze(r["source"], r["record"], r["repo"])
    assert r["record"].read_bytes() == original
    primary = Path(r["config"]["execution"]["records_root"]) / "final-primary"
    primary.mkdir(parents=True)
    with pytest.raises(ValueError, match="exists"):
        preregister.command(r["record"], "primary", r["repo"])
    argv = preregister.command(r["record"], "supplemental", r["repo"])
    assert "final-extra" in argv
    assert "--dry-run" not in argv
    assert "--codex-no-subagents" in argv and "--hide-grading" in argv
    assert argv.count("--case") == 10


def test_frozen_record_tampering_is_rejected(registration):
    """Editing provenance or unit membership invalidates the record checksum."""
    r = registration
    record = preregister.freeze(r["source"], r["record"], r["repo"])
    record["snapshot"]["provenance"][0]["tuning_exposure"] = (
        "independently_held_out"
    )
    os.chmod(r["record"], 0o600)
    r["record"].write_text(json.dumps(record))
    with pytest.raises(ValueError, match="integrity"):
        preregister.command(r["record"], "primary", r["repo"])


def test_command_keeps_the_configured_virtualenv_interpreter(registration):
    """Resolving a venv's Python symlink would launch without its dependencies."""
    r = registration
    preregister.freeze(r["source"], r["record"], r["repo"])
    argv = preregister.command(r["record"], "primary", r["repo"])
    result = subprocess.check_output(
        [argv[0], "-c", "import sys; print(sys.prefix)"],
        text=True,
        stdin=subprocess.DEVNULL,
    ).strip()
    assert result == sys.prefix


def test_frozen_units_match_the_existing_runner_plan(registration):
    """The actual runner, rather than a copied algorithm, decides seeded order."""
    import run as runner

    cases = preregister.inventory(registration["cases"])["primary"]
    seed = 20261104
    jobs = runner.plan_jobs(
        {"plans": []},
        [{"id": c} for c in cases],
        ["claude", "codex"],
        ["noskill", "skill"],
        2,
        seed,
    )
    assert preregister.planned_units(cases, seed) == [
        runner.unit_id(host, case["id"], arm, rep)
        for case, host, arm, rep in jobs
    ]
