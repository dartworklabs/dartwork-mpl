"""Freeze and verify the final agentic A/B inputs without invoking either host.

``freeze --config CONFIG --output RECORD`` writes an exclusive prelaunch record.
``verify RECORD`` rechecks it. ``command RECORD --cohort primary`` emits runner
argv only when frozen inputs still match and that official run ID is unused.
Case YAML and reference solutions are never read or imported. Runtime evidence
is an operator-supplied receipt, not a claim that this helper verified login or
the current model catalog. No credentials are read and no model is called.
"""

import argparse
import ast
import hashlib
import json
import math
import os
import random
import re
import shlex
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
COHORTS = ("primary", "supplemental")
HOSTS = ("claude", "codex")
ARMS = ("noskill", "skill")
PRIMARY_IDS = (
    "e01-label-step-en",
    "e02-label-step-ko",
    "e03-panel-width",
    "e04-legend-outside",
    "e05-highlight-korea-en",
    "e06-highlight-bar-ko",
    "e07-end-labels-en",
    "e08-end-labels-ko",
    "e09-look-better-en",
    "e10-look-better-ko",
    "e11-slides-en",
    "e12-slides-ko",
    "e13-log-y-en",
    "e14-log-y-ko",
    "e15-panel-ratio",
    "g01-line-gdp",
    "g02-grouped-bar-sales",
    "g03-barh-labels-survey",
    "g04-scatter-fit-plants",
    "g05-heatmap-corr-ko",
    "g06-hist-response",
    "g07-box-exam",
    "g08-stacked-area-energy",
    "g09-small-multiples-ko",
    "g10-dashboard-kpi",
    "g11-dual-axis-ko",
    "g12-timeseries-event",
    "g13-uneven-panels",
    "g14-korean-combo",
    "g15-korean-barh",
    "g16-paper-dose",
    "g17-paper-two-panel",
    "g18-report-traffic",
    "g19-slides-share-ko",
    "g20-slides-renewables",
    "g21-size-17x9",
    "g22-size-12x8-ko",
    "g23-vague-en",
    "g24-vague-ko",
    "g25-korean-dates",
)
SUPPLEMENTAL_IDS = (
    "c01-title-en",
    "c02-title-ko",
    "c03-gridlines-en",
    "c04-width-only-en",
    "c05-legend-top-en",
    "c06-source-note-ko",
    "c07-dark-en",
    "e16-add-title-en",
    "e17-add-grid-ko",
    "e18-width-16-en",
)
DECLARED = frozenset(
    ["g03", "g07", "g11", "g15", "g20", "g24", "e04", "e08", "e10", "e14"]
)
EXPOSED = frozenset(["e04", "e08", "e10", "e14", "g20"])
NOT_USED = frozenset(["g03", "g07", "g11", "g15", "g24"])
ANALYSIS_POLICY = {
    "primary": "existing_preregistered_endpoints_unchanged",
    "supplemental": "descriptive_only",
    "clean_subset": "descriptive_only",
    "clean_subset_limit": "Not used in v13-v24 tuning; original baseline observed; not independent holdouts.",
    "masterplan": "Current user-reconciled PREREGISTERED rule; historical task-success improvement is descriptive; raw value/edit checks fail closed.",
    "missing_units_or_usage": "block_verdict",
    "retries_replacements_optional_stopping": "forbidden",
}
MAX_JSON_BYTES = 1_048_576


@dataclass(frozen=True)
class Host:
    """Explicit runtime-selected model, effort and observed CLI version."""

    model: str
    effort: str
    version: str


@dataclass(frozen=True)
class Config:
    """Validated explicit inputs; paths identify files, never credential contents."""

    raw: dict[str, object]
    wheel: Path
    wheel_sha: str
    commit: str
    hosts: dict[str, Host]
    home: Path
    evidence: Path
    evidence_sha: str
    budgets: dict[str, int | float]
    python: Path
    project_python: str
    records: Path
    work: Path
    run_ids: dict[str, str]
    seeds: dict[str, int]
    jobs: int


def _sha(path: Path) -> str:
    """Hash an existing input in bounded chunks; absent/non-file inputs fail."""
    try:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()
    except OSError as exc:
        raise ValueError(f"missing or unreadable input: {path}") from exc


def _canonical(value: object) -> bytes:
    """Give a JSON value one stable representation for the record checksum."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Reject ambiguous duplicate JSON keys instead of retaining their last value."""
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _mapping(value: object, keys: set[str], label: str) -> dict[str, object]:
    """Parse a closed mapping with exactly the declared string keys."""
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"{label}: required keys are {sorted(keys)}")
    return {key: value[key] for key in keys}


def _json_bytes(path: Path) -> tuple[dict[str, object], bytes]:
    """Read bounded JSON with duplicate-key and nonfinite-number rejection."""
    try:
        with path.open("rb") as stream:
            content = stream.read(MAX_JSON_BYTES + 1)
        if len(content) > MAX_JSON_BYTES:
            raise ValueError(f"JSON input too large: {path}")
        value: object = json.loads(content, object_pairs_hook=_unique)
        if not isinstance(value, dict):
            raise ValueError("JSON root must be an object")
        _canonical(
            value
        )  # rejects NaN and infinity before values are interpreted
        return {str(k): v for k, v in value.items()}, content
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"missing or invalid JSON input: {path}") from exc


def _text(value: object, label: str) -> str:
    """Require an explicitly supplied, nonempty, single-line string."""
    if (
        not isinstance(value, str)
        or not value.strip()
        or any(c in value for c in "\x00\n\r")
    ):
        raise ValueError(f"{label}: nonempty string required")
    return value


def _path(value: object, label: str) -> Path:
    """Normalize an absolute path while preserving venv invocation symlinks."""
    path = Path(_text(value, label))
    if not path.is_absolute():
        raise ValueError(f"{label}: absolute path required")
    return Path(os.path.abspath(path))


def _integer(value: object, label: str, low: int, high: int) -> int:
    """Parse a bounded integer; booleans are never numeric configuration."""
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{label}: integer in [{low}, {high}] required")
    return value


def _digest(value: object, label: str, length: int = 64) -> str:
    """Require an explicit lowercase full-length hexadecimal identity."""
    text = _text(value, label)
    if not re.fullmatch(rf"[0-9a-f]{{{length}}}", text):
        raise ValueError(f"{label}: full lowercase hexadecimal digest required")
    return text


def _parse(raw: dict[str, object]) -> Config:
    """Parse the complete experiment configuration; absent fields never default."""
    cfg = _mapping(
        raw,
        {
            "schema_version",
            "wheel",
            "harness_commit",
            "models",
            "auth",
            "runtime_evidence",
            "budgets",
            "execution",
            "controls",
        },
        "config",
    )
    if type(cfg["schema_version"]) is not int or cfg["schema_version"] != 1:
        raise ValueError("config.schema_version must be 1")
    wheel = _mapping(cfg["wheel"], {"path", "sha256"}, "config.wheel")
    evidence = _mapping(
        cfg["runtime_evidence"], {"path", "sha256"}, "config.runtime_evidence"
    )
    models = _mapping(cfg["models"], set(HOSTS), "config.models")
    hosts = {}
    for name in HOSTS:
        host = _mapping(
            models[name],
            {"id", "effort", "host_version"},
            f"config.models.{name}",
        )
        hosts[name] = Host(
            *(
                _text(host[k], f"config.models.{name}.{k}")
                for k in ("id", "effort", "host_version")
            )
        )
    auth = _mapping(cfg["auth"], {"codex_home"}, "config.auth")
    budget = _mapping(
        cfg["budgets"],
        {
            "timeout_s",
            "claude_max_turns",
            "claude_max_budget_usd",
            "codex_token_budget",
        },
        "config.budgets",
    )
    amount = budget["claude_max_budget_usd"]
    if (
        not isinstance(amount, (int, float))
        or isinstance(amount, bool)
        or not math.isfinite(amount)
        or amount <= 0
    ):
        raise ValueError(
            "config.budgets.claude_max_budget_usd must be positive and finite"
        )
    budgets: dict[str, int | float] = {"claude_max_budget_usd": float(amount)}
    for key in ("timeout_s", "claude_max_turns", "codex_token_budget"):
        budgets[key] = _integer(
            budget[key], f"config.budgets.{key}", 1, 2**63 - 1
        )
    execution = _mapping(
        cfg["execution"],
        {
            "python",
            "project_python",
            "records_root",
            "work_root",
            "run_ids",
            "seeds",
            "reps",
            "jobs",
        },
        "config.execution",
    )
    if type(execution["reps"]) is not int or execution["reps"] != 2:
        raise ValueError("config.execution.reps must be 2")
    run_ids = _mapping(
        execution["run_ids"], set(COHORTS), "config.execution.run_ids"
    )
    seeds = _mapping(execution["seeds"], set(COHORTS), "config.execution.seeds")
    names = {
        c: _text(run_ids[c], f"config.execution.run_ids.{c}") for c in COHORTS
    }
    if len(set(names.values())) != 2 or any(
        not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", n)
        for n in names.values()
    ):
        raise ValueError(
            "config.execution.run_ids must be distinct safe directory names"
        )
    controls = _mapping(
        cfg["controls"],
        {
            "hide_grading",
            "codex_subagents",
            "github_mcp_disabled",
            "subscription_only",
            "latest_generation_verified",
            "no_retries",
        },
        "config.controls",
    )
    if any(
        value is not (key != "codex_subagents")
        for key, value in controls.items()
    ):
        raise ValueError(
            "config.controls require subscriptions, current models, isolation and no subagents/retries"
        )
    return Config(
        raw,
        _path(wheel["path"], "config.wheel.path"),
        _digest(wheel["sha256"], "config.wheel.sha256"),
        _digest(cfg["harness_commit"], "config.harness_commit", 40),
        hosts,
        _path(auth["codex_home"], "config.auth.codex_home"),
        _path(evidence["path"], "config.runtime_evidence.path"),
        _digest(evidence["sha256"], "config.runtime_evidence.sha256"),
        budgets,
        _path(execution["python"], "config.execution.python"),
        _text(execution["project_python"], "config.execution.project_python"),
        _path(execution["records_root"], "config.execution.records_root"),
        _path(execution["work_root"], "config.execution.work_root"),
        names,
        {
            c: _integer(seeds[c], f"config.execution.seeds.{c}", 0, 2**63 - 1)
            for c in COHORTS
        },
        _integer(execution["jobs"], "config.execution.jobs", 1, 7),
    )


def inventory(cases_dir: Path) -> dict[str, list[str]]:
    """Validate the exact 40/10 population using filenames, never YAML bodies."""
    if not cases_dir.is_dir():
        raise ValueError("case roster directory is missing")
    found = sorted(p.stem for p in cases_dir.glob("*.yaml") if p.is_file())
    expected = set(PRIMARY_IDS) | set(SUPPLEMENTAL_IDS)
    if len(found) != 50 or set(found) != expected:
        raise ValueError(
            f"case roster differs: missing={sorted(expected - set(found))}; extra={sorted(set(found) - expected)}"
        )
    return {
        "primary": sorted(PRIMARY_IDS),
        "supplemental": sorted(SUPPLEMENTAL_IDS),
    }


def provenance(cohorts: dict[str, list[str]]) -> list[dict[str, object]]:
    """Separate historical declarations from the user-declared tuning exposure."""
    return [
        {
            "case": case,
            "cohort": cohort,
            "declared_held_out": case[:3] in DECLARED,
            "tuning_exposure": "exposed"
            if case[:3] in EXPOSED
            else "not_used_in_v13_v24"
            if case[:3] in NOT_USED
            else "not_assessed",
            "baseline_observed": True if cohort == "primary" else None,
        }
        for cohort in COHORTS
        for case in cohorts[cohort]
    ]


def planned_units(cases: list[str], seed: int) -> list[str]:
    """Match the runner's fresh case/host/arm/rep loop and seeded permutation."""
    units = [
        f"{host}/{case}/{arm}-r{rep}"
        for case in sorted(cases)
        for host in HOSTS
        for arm in ARMS
        for rep in (1, 2)
    ]
    random.Random(seed).shuffle(units)
    return units


def _run(argv: list[str], repo: Path) -> str:
    """Execute bounded read-only Git/version queries with no inherited stdin."""
    try:
        result = subprocess.run(
            argv,
            cwd=repo,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=20,
            check=True,
        )
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        raise ValueError(f"cannot verify runtime/harness: {argv[:2]}") from exc


def _check_inputs(cfg: Config, repo: Path) -> None:
    """Refuse changed bytes, untrusted/dirty harnesses and unsafe auth/root paths."""
    if _sha(cfg.wheel) != cfg.wheel_sha:
        raise ValueError(
            "wheel sha256 changed or differs from explicit configuration"
        )
    if _sha(cfg.evidence) != cfg.evidence_sha:
        raise ValueError("runtime evidence sha256 changed")
    if _run(["git", "rev-parse", "HEAD"], repo) != cfg.commit:
        raise ValueError("trusted harness commit changed")
    if _run(["git", "status", "--porcelain", "--untracked-files=all"], repo):
        raise ValueError("trusted harness worktree must be clean")
    if not cfg.home.is_dir() or any(
        os.path.lexists(cfg.home / name)
        for name in ("AGENTS.md", "AGENTS.override.md", "config.toml")
    ):
        raise ValueError(
            "Codex home must exist without global instructions/config"
        )
    if not cfg.python.is_file() or not os.access(cfg.python, os.X_OK):
        raise ValueError(
            "configured runner Python is missing or not executable"
        )
    roots = tuple(p.resolve() for p in (cfg.records, cfg.work, cfg.home, repo))
    if any(
        a.is_relative_to(b) or b.is_relative_to(a)
        for i, a in enumerate(roots)
        for b in roots[i + 1 :]
    ):
        raise ValueError(
            "records, work, Codex home and repository must have separate roots"
        )
    for host in HOSTS:
        if _run([host, "--version"], repo) != cfg.hosts[host].version:
            raise ValueError(
                f"{host} CLI version differs from frozen configuration"
            )


def _endpoints(repo: Path) -> str:
    """Extract only the literal preregistration text without importing the scorer."""
    try:
        tree = ast.parse(
            (repo / "evals" / "agentic" / "compare.py").read_text(
                encoding="utf-8"
            )
        )
        values = [
            ast.literal_eval(node.value)
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(t, ast.Name) and t.id == "PREREGISTERED"
                for t in node.targets
            )
        ]
        if (
            len(values) != 1
            or not isinstance(values[0], str)
            or not values[0].strip()
        ):
            raise ValueError(
                "exactly one literal PREREGISTERED text is required"
            )
        return values[0]
    except (OSError, SyntaxError, TypeError) as exc:
        raise ValueError("cannot freeze PREREGISTERED endpoint text") from exc


def _argv(cfg: Config, cohort: str, cases: list[str], repo: Path) -> list[str]:
    """Construct the existing runner's explicit, identical-arm launch arguments."""
    argv = [
        str(cfg.python),
        str(repo / "evals" / "agentic" / "run.py"),
        "--root",
        str(cfg.records),
        "--work-root",
        str(cfg.work),
        "--run-id",
        cfg.run_ids[cohort],
        "--wheel",
        str(cfg.wheel),
    ]
    for host in HOSTS:
        argv += [
            "--host",
            host,
            f"--{host}-model",
            cfg.hosts[host].model,
            f"--{host}-effort",
            cfg.hosts[host].effort,
        ]
    for case in cases:
        argv += ["--case", case]
    return [
        *argv,
        "--ab-skill-install",
        "--hide-grading",
        "--codex-no-subagents",
        "--codex-home",
        str(cfg.home),
        "--python",
        cfg.project_python,
        "--reps",
        "2",
        "--seed",
        str(cfg.seeds[cohort]),
        "--jobs",
        str(cfg.jobs),
        "--timeout",
        str(cfg.budgets["timeout_s"]),
        "--max-turns",
        str(cfg.budgets["claude_max_turns"]),
        "--max-budget-usd",
        str(cfg.budgets["claude_max_budget_usd"]),
        "--codex-token-budget",
        str(cfg.budgets["codex_token_budget"]),
    ]


def _snapshot(
    config_path: Path, repo: Path
) -> tuple[Config, dict[str, object]]:
    """Rebuild all frozen identities and planned units from explicit live inputs."""
    raw, content = _json_bytes(config_path)
    cfg = _parse(raw)
    _check_inputs(cfg, repo)
    cohorts = inventory(repo / "evals" / "agentic" / "cases")
    endpoint_text = _endpoints(repo)
    return cfg, {
        "config_path": str(config_path.resolve()),
        "config_sha256": hashlib.sha256(content).hexdigest(),
        "config": cfg.raw,
        "harness_commit": cfg.commit,
        "endpoint_text": endpoint_text,
        "endpoint_sha256": hashlib.sha256(
            endpoint_text.encode("utf-8")
        ).hexdigest(),
        "analysis_policy": ANALYSIS_POLICY,
        "provenance": provenance(cohorts),
        "cohorts": {
            name: {
                "cases": cases,
                "run_id": cfg.run_ids[name],
                "planned_units": planned_units(cases, cfg.seeds[name]),
                "argv": _argv(cfg, name, cases, repo),
            }
            for name, cases in cohorts.items()
        },
    }


def _unused(cfg: Config, cohort: str) -> None:
    """Deny replay, extension or replacement of an already allocated official ID."""
    if cohort not in COHORTS:
        raise ValueError("unknown cohort")
    if os.path.lexists(cfg.records / cfg.run_ids[cohort]):
        raise ValueError(
            f"official run directory already exists: {cfg.run_ids[cohort]}"
        )


def _record_location(cfg: Config, path: Path) -> None:
    """Keep grading details under the runner's hidden root, beside its run IDs."""
    target = path.resolve()
    records = cfg.records.resolve()
    if target == records or not target.is_relative_to(records):
        raise ValueError(
            "prelaunch record must stay inside the hidden records root"
        )
    if any(
        target.is_relative_to((cfg.records / name).resolve())
        for name in cfg.run_ids.values()
    ):
        raise ValueError(
            "prelaunch record must be outside official run directories"
        )


def freeze(
    config_path: Path, output_path: Path, repo: Path = REPO
) -> dict[str, object]:
    """Exclusively persist a checksummed record inside the hidden records root."""
    if os.path.lexists(output_path):
        raise ValueError("prelaunch output already exists")
    if output_path.resolve().is_relative_to(repo.resolve()):
        raise ValueError(
            "keep the prelaunch record outside the trusted repository"
        )
    cfg, snapshot = _snapshot(config_path.resolve(), repo.resolve())
    _record_location(cfg, output_path)
    for cohort in COHORTS:
        _unused(cfg, cohort)
    record: dict[str, object] = {
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "snapshot": snapshot,
    }
    record["sha256"] = hashlib.sha256(_canonical(record)).hexdigest()
    try:
        with output_path.open("x", encoding="utf-8") as stream:
            stream.write(
                json.dumps(
                    record, ensure_ascii=False, indent=2, allow_nan=False
                )
                + "\n"
            )
            stream.flush()
            os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), 0o444)
    except OSError as exc:
        raise ValueError(
            f"cannot exclusively write prelaunch record: {output_path}"
        ) from exc
    return record


def _verified(
    record_path: Path, repo: Path
) -> tuple[Config, dict[str, object]]:
    """Validate integrity then compare with a fresh snapshot of the frozen inputs."""
    raw, _ = _json_bytes(record_path)
    record = _mapping(
        raw, {"frozen_at", "snapshot", "sha256"}, "prelaunch record"
    )
    digest = hashlib.sha256(
        _canonical({k: v for k, v in record.items() if k != "sha256"})
    ).hexdigest()
    if record["sha256"] != digest or not isinstance(record["snapshot"], dict):
        raise ValueError("prelaunch record integrity check failed")
    path = _path(record["snapshot"].get("config_path"), "prelaunch config_path")
    cfg, expected = _snapshot(path, repo.resolve())
    _record_location(cfg, record_path)
    if record["snapshot"] != expected:
        raise ValueError(
            "frozen input/config/roster/endpoints/provenance changed"
        )
    return cfg, expected


def verify(record_path: Path, repo: Path = REPO) -> dict[str, object]:
    """Recheck frozen inputs without changing records or starting any host."""
    return _verified(record_path, repo)[1]


def command(record_path: Path, cohort: str, repo: Path = REPO) -> list[str]:
    """Return launch argv only for matching frozen inputs and an unused cohort ID."""
    cfg, _ = _verified(record_path, repo)
    _unused(cfg, cohort)
    cases = list(PRIMARY_IDS if cohort == "primary" else SUPPLEMENTAL_IDS)
    return _argv(cfg, cohort, sorted(cases), repo.resolve())


def main() -> int:
    """Expose freeze/verify/command without any model-execution subcommand."""
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    new = sub.add_parser("freeze")
    new.add_argument("--config", type=Path, required=True)
    new.add_argument("--output", type=Path, required=True)
    for name in ("verify", "command"):
        item = sub.add_parser(name)
        item.add_argument("record", type=Path)
        if name == "command":
            item.add_argument("--cohort", choices=COHORTS, required=True)
            item.add_argument("--shell", action="store_true")
    args = parser.parse_args()
    try:
        if args.action == "freeze":
            result = freeze(args.config, args.output)
            print(
                json.dumps(
                    {"record": str(args.output), "sha256": result["sha256"]}
                )
            )
        elif args.action == "verify":
            verify(args.record)
            print("Frozen inputs verified; no host launched.")
        else:
            argv = command(args.record, args.cohort)
            print(
                shlex.join(argv) + " </dev/null"
                if args.shell
                else json.dumps(argv)
            )
    except ValueError as exc:
        parser.exit(2, f"preregister: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
