"""Drift detection for auto-generated bundles.

The Sphinx build validates ``llms-full.txt`` (concatenated agent
reference) and ``05-templates/_index.json`` (AI-template metadata)
against canonical sources on every run. PRs that touch those upstream
sources but forget to regenerate the authorities would silently ship a
stale dump to PyPI / GitHub-raw consumers — these tests catch that.

They re-run the same composition logic in-process and compare against
the committed artifact. Regenerate a stale authority explicitly, commit it,
and then rerun the non-writing Sphinx check.
"""

from __future__ import annotations

import importlib.util
import json
import re
import shlex
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import cast

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
_WORKFLOW_JOBS = {"ci.yml": "docs", "docs.yml": "build", "release.yml": "test"}
_COMPARISON_ARTIFACT = "color-system-comparison"
_COMPARISON_PATH = "build/color-system-comparison"
_V6_AUTHORITY_PATH = "src/dartwork_mpl/asset/color/color_v6_ssot.json"
_V6_BASELINE_COMMIT = "12d16bac22dee790bd0696ca92a814a797dc728b"
_CHECK_COMMANDS = (
    ("uv", "run", "python", "-m", "dartwork_mpl._colors._build", "--check"),
    (
        "uv",
        "run",
        "python",
        "scripts/compare_color_systems.py",
        "--output",
        _COMPARISON_PATH,
        "--check",
    ),
    (
        "uv",
        "run",
        "python",
        "docs/_static/scripts/build_categorical_explorer.py",
        "--check",
    ),
    (
        "uv",
        "run",
        "python",
        "docs/_static/scripts/build_colormap_explorer.py",
        "--check",
    ),
    (
        "uv",
        "run",
        "python",
        "docs/color_system/generate_theory_figures.py",
        "--check",
    ),
)
_SHELL_SEPARATOR = re.compile(r"\s*(?:&&|\|\||;)\s*")
_ENV_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


def _load_build_hooks() -> ModuleType:
    """Import ``docs/_ext/build_hooks.py`` without going through Sphinx."""
    spec = importlib.util.spec_from_file_location(
        "build_hooks", REPO_ROOT / "docs" / "_ext" / "build_hooks.py"
    )
    if spec is None or spec.loader is None:
        pytest.skip("docs/_ext/build_hooks.py not importable")
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("build_hooks", mod)
    spec.loader.exec_module(mod)
    return mod


def _compose_llms_full(build_hooks: ModuleType) -> str:
    """Re-run the concatenation logic to get the expected bytes."""
    parts: list[str] = [build_hooks._LLMS_FULL_HEADER]
    for header, rel in build_hooks._LLMS_FULL_SOURCES:
        parts.append(header)
        if rel is None:
            continue
        src = REPO_ROOT / rel
        if not src.exists():
            pytest.fail(
                f"llms-full source missing in repo: {rel}; "
                f"build_hooks.py would also fail."
            )
        parts.append(src.read_text(encoding="utf-8"))
    return "".join(parts)


def _load_workflow(name: str) -> Mapping[str, object]:
    """Decode one GitHub Actions workflow as a mapping."""
    path = REPO_ROOT / ".github" / "workflows" / name
    decoded: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(decoded, Mapping):
        pytest.fail(f"workflow is not a mapping: {path}")
    return cast(Mapping[str, object], decoded)


def _workflow_job(
    workflow: Mapping[str, object], job_name: str
) -> Mapping[str, object]:
    """Return one structurally valid workflow job."""
    jobs = workflow.get("jobs")
    if not isinstance(jobs, Mapping):
        pytest.fail("workflow jobs must be a mapping")
    job = jobs.get(job_name)
    if not isinstance(job, Mapping):
        pytest.fail(f"workflow job is missing: {job_name}")
    return cast(Mapping[str, object], job)


def _job_steps(job: Mapping[str, object]) -> tuple[Mapping[str, object], ...]:
    """Return one job's structurally valid step mappings."""
    steps = job.get("steps")
    if not isinstance(steps, Sequence) or isinstance(steps, (str, bytes)):
        pytest.fail("workflow job steps must be a sequence")
    invalid = [step for step in steps if not isinstance(step, Mapping)]
    if invalid:
        pytest.fail(f"workflow contains invalid steps: {invalid!r}")
    return tuple(cast(Mapping[str, object], step) for step in steps)


def _shell_commands(script: str) -> tuple[tuple[str, ...], ...]:
    """Tokenize executable shell commands, excluding YAML comments."""
    logical_lines: list[str] = []
    continuation = ""
    for raw_line in script.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.endswith("\\"):
            continuation += f"{line[:-1].rstrip()} "
            continue
        logical_lines.append(f"{continuation}{line}")
        continuation = ""
    if continuation:
        logical_lines.append(continuation.rstrip())

    commands: list[tuple[str, ...]] = []
    for logical_line in logical_lines:
        for segment in _SHELL_SEPARATOR.split(logical_line):
            tokens = tuple(shlex.split(segment, comments=True, posix=True))
            while tokens and _ENV_ASSIGNMENT.match(tokens[0]):
                tokens = tokens[1:]
            if tokens:
                commands.append(tokens)
    return tuple(commands)


def _step_commands(
    steps: Sequence[Mapping[str, object]],
) -> tuple[tuple[int, tuple[str, ...]], ...]:
    """Collect tokenized commands with their owning step index."""
    commands: list[tuple[int, tuple[str, ...]]] = []
    for index, step in enumerate(steps):
        run = step.get("run")
        if not isinstance(run, str):
            continue
        commands.extend((index, command) for command in _shell_commands(run))
    return tuple(commands)


def _command_index(
    commands: Sequence[tuple[int, tuple[str, ...]]], expected: tuple[str, ...]
) -> int:
    """Return the step index of one exact command prefix."""
    for step_index, command in commands:
        if command[: len(expected)] == expected:
            return step_index
    pytest.fail(f"missing workflow command: {shlex.join(expected)}")


def _assert_v6_authority_parity(
    commands: Sequence[tuple[int, tuple[str, ...]]],
) -> None:
    """Require a pinned temporary rebuild followed by byte comparison."""
    prefix = ("uv", "run", "python", "scripts/build_color_v6_ssot.py")
    builder = next(
        (command for _index, command in commands if command[:4] == prefix), None
    )
    if builder is None:
        pytest.fail(f"missing workflow command: {shlex.join(prefix)}")
    if "--baseline-commit" not in builder or "--output" not in builder:
        pytest.fail("v6 SSOT rebuild must pin its baseline and output")
    baseline = builder[builder.index("--baseline-commit") + 1]
    output = builder[builder.index("--output") + 1]
    assert baseline == _V6_BASELINE_COMMIT
    assert output != _V6_AUTHORITY_PATH

    comparisons = [
        command
        for _index, command in commands
        if command and command[0] == "cmp"
    ]
    assert any(
        output in command and _V6_AUTHORITY_PATH in command
        for command in comparisons
    ), "v6 SSOT temporary output is not compared with the packaged authority"


def _always_expression(value: object) -> bool:
    """Recognize both supported GitHub ``always()`` spellings."""
    if not isinstance(value, str):
        return False
    normalized = value.strip()
    if normalized.startswith("${{") and normalized.endswith("}}"):
        normalized = normalized[3:-2].strip()
    return normalized == "always()"


def _comparison_upload_index(steps: Sequence[Mapping[str, object]]) -> int:
    """Return the always-running fixed comparison-artifact upload step."""
    for index, step in enumerate(steps):
        uses = step.get("uses")
        options = step.get("with")
        if not (
            isinstance(uses, str)
            and uses.startswith("actions/upload-artifact@")
            and isinstance(options, Mapping)
        ):
            continue
        if (
            options.get("name") == _COMPARISON_ARTIFACT
            and options.get("path") == _COMPARISON_PATH
            and _always_expression(step.get("if"))
        ):
            return index
    pytest.fail(
        "missing always-running upload for the fixed "
        f"{_COMPARISON_ARTIFACT!r} artifact"
    )


def _write_text(path: Path, text: str) -> None:
    """Write one temporary hook fixture, creating its parents."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.mark.parametrize(
    ("workflow_name", "job_name"), tuple(_WORKFLOW_JOBS.items())
)
def test_workflow_checks_color_compiler_and_comparator(
    workflow_name: str, job_name: str
) -> None:
    """Run both non-writing color gates in every shipping workflow."""
    workflow = _load_workflow(workflow_name)
    steps = _job_steps(_workflow_job(workflow, job_name))
    commands = _step_commands(steps)

    for expected in _CHECK_COMMANDS[:2]:
        _command_index(commands, expected)


@pytest.mark.parametrize(
    ("workflow_name", "job_name"), tuple(_WORKFLOW_JOBS.items())
)
def test_workflow_checks_every_generated_docs_color_asset(
    workflow_name: str, job_name: str
) -> None:
    """Check both explorers and temporary theory parity before shipping."""
    workflow = _load_workflow(workflow_name)
    steps = _job_steps(_workflow_job(workflow, job_name))
    commands = _step_commands(steps)

    for expected in _CHECK_COMMANDS[2:]:
        _command_index(commands, expected)


@pytest.mark.parametrize(
    ("workflow_name", "job_name"), tuple(_WORKFLOW_JOBS.items())
)
def test_workflow_rebuilds_v6_authority_to_a_temporary_file(
    workflow_name: str, job_name: str
) -> None:
    """Compare a pinned v6 rebuild without rewriting packaged authority."""
    workflow = _load_workflow(workflow_name)
    steps = _job_steps(_workflow_job(workflow, job_name))

    _assert_v6_authority_parity(_step_commands(steps))


@pytest.mark.parametrize(
    ("workflow_name", "job_name"), tuple(_WORKFLOW_JOBS.items())
)
def test_workflow_always_uploads_fixed_comparison_artifact(
    workflow_name: str, job_name: str
) -> None:
    """Preserve comparator JSON and HTML on both success and failure."""
    workflow = _load_workflow(workflow_name)
    steps = _job_steps(_workflow_job(workflow, job_name))
    commands = _step_commands(steps)
    comparator_index = _command_index(commands, _CHECK_COMMANDS[1])

    assert _comparison_upload_index(steps) > comparator_index


def test_release_color_checks_gate_distribution_build() -> None:
    """Keep stale or incompatible colors upstream of every publish path."""
    workflow = _load_workflow("release.yml")
    build = _workflow_job(workflow, "build")
    publish = _workflow_job(workflow, "publish")

    assert build.get("needs") == "test"
    assert publish.get("needs") == "build"


def test_llms_hook_rejects_stale_authority_without_rewriting(
    tmp_path: Path,
) -> None:
    """Make the Sphinx hook a check, not an implicit authority writer."""
    build_hooks = _load_build_hooks()
    repo = tmp_path / "repo"
    docs = repo / "docs"
    docs.mkdir(parents=True)
    app = SimpleNamespace(srcdir=str(docs))
    sources = cast(
        Sequence[tuple[str, str | None]], build_hooks._LLMS_FULL_SOURCES
    )
    for _header, relative in sources:
        if relative is not None:
            _write_text(repo / relative, f"canonical: {relative}\n")
    authority = repo / "llms-full.txt"
    _write_text(authority, "stale authority\n")
    before = authority.read_bytes()

    with pytest.raises(RuntimeError, match=r"llms-full\.txt.*stale"):
        build_hooks.generate_llms_full_txt(app)

    assert authority.read_bytes() == before


def test_template_hook_rejects_stale_authority_without_rewriting(
    tmp_path: Path,
) -> None:
    """Fail a Sphinx build instead of silently updating template metadata."""
    build_hooks = _load_build_hooks()
    repo = tmp_path / "repo"
    docs = repo / "docs"
    docs.mkdir(parents=True)
    app = SimpleNamespace(srcdir=str(docs))
    template = docs / "examples_source/09_ai_templates/plot_line.py"
    _write_text(
        template,
        '"""Example template."""\n'
        "# ai-template-meta-start\n"
        "# use_case: Compare one series\n"
        "# difficulty: beginner\n"
        "# data_shape: x and y sequences\n"
        "# tags: line, comparison\n"
        "# ai-template-meta-end\n",
    )
    authority = repo / "src/dartwork_mpl/asset/prompt/05-templates/_index.json"
    _write_text(authority, "{}\n")
    before = authority.read_bytes()

    with pytest.raises(RuntimeError, match=r"_index\.json.*stale"):
        build_hooks.generate_template_index(app)

    assert authority.read_bytes() == before


def test_template_hook_rejects_missing_source_directory(tmp_path: Path) -> None:
    """A missing canonical template root must not become a silent success."""
    build_hooks = _load_build_hooks()
    repo = tmp_path / "repo"
    docs = repo / "docs"
    docs.mkdir(parents=True)
    app = SimpleNamespace(srcdir=str(docs))

    with pytest.raises(FileNotFoundError, match="source directory is missing"):
        build_hooks.generate_template_index(app)


def test_llms_full_txt_in_sync() -> None:
    """Repo-root ``llms-full.txt`` must match the live concatenation
    of its canonical sources. A drift means a PR changed an upstream
    file without rerunning the docs build.
    """
    out = REPO_ROOT / "llms-full.txt"
    if not out.exists():
        pytest.skip("llms-full.txt not present in this checkout")
    build_hooks = _load_build_hooks()
    expected = _compose_llms_full(build_hooks)
    actual = out.read_text(encoding="utf-8")
    if expected != actual:
        # Provide an actionable diff hint without dumping 47 KB.
        first_diff = next(
            (
                i
                for i, (a, b) in enumerate(zip(expected, actual, strict=False))
                if a != b
            ),
            min(len(expected), len(actual)),
        )
        ctx_start = max(0, first_diff - 60)
        ctx_end = first_diff + 60
        pytest.fail(
            "llms-full.txt is stale. Regenerate the authority explicitly "
            "and commit it before rebuilding the docs.\n"
            f"First divergence at offset {first_diff}.\n"
            f"  expected: ...{expected[ctx_start:ctx_end]!r}...\n"
            f"  actual:   ...{actual[ctx_start:ctx_end]!r}..."
        )


def test_template_index_in_sync() -> None:
    """``05-templates/_index.json`` must mirror the metadata blocks in
    ``docs/examples_source/09_ai_templates/plot_*.py`` (basic tier) and
    ``docs/examples_source/09_ai_templates_advanced/plot_*.py`` (tier 2).
    """
    out = (
        REPO_ROOT
        / "src"
        / "dartwork_mpl"
        / "asset"
        / "prompt"
        / "05-templates"
        / "_index.json"
    )
    if not out.exists():
        pytest.skip("_index.json not yet generated in this checkout")

    build_hooks = _load_build_hooks()

    def _scan_tier(scan_dir: Path, tier: str) -> dict[str, dict[str, object]]:
        section: dict[str, dict[str, object]] = {}
        for path in sorted(scan_dir.glob("plot_*.py")):
            text = path.read_text(encoding="utf-8")
            match = build_hooks._TEMPLATE_META_RE.search(text)
            if not match:
                pytest.fail(f"meta block missing in {path.name}")
            meta = build_hooks._parse_template_meta(
                match.group(1), source=str(path.relative_to(REPO_ROOT))
            )
            stem = path.stem
            template_id = (
                stem if stem == "plot_3d" else stem.removeprefix("plot_")
            )
            meta["source_path"] = str(path.relative_to(REPO_ROOT))
            meta.setdefault("tier", tier)
            section[template_id] = meta
        return section

    basic_dir = REPO_ROOT / "docs" / "examples_source" / "09_ai_templates"
    if not basic_dir.exists():
        pytest.skip("09_ai_templates source dir missing")
    expected: dict[str, dict[str, object]] = _scan_tier(basic_dir, "basic")

    advanced_dir = (
        REPO_ROOT / "docs" / "examples_source" / "09_ai_templates_advanced"
    )
    if advanced_dir.exists():
        expected["advanced"] = _scan_tier(  # type: ignore[assignment]
            advanced_dir, "advanced"
        )

    actual = json.loads(out.read_text(encoding="utf-8"))
    if expected != actual:
        missing = set(expected) - set(actual)
        extra = set(actual) - set(expected)
        pytest.fail(
            "_index.json is stale. Regenerate the authority explicitly "
            "and commit it before rebuilding the docs.\n"
            f"  missing template ids: {sorted(missing)}\n"
            f"  extra template ids:   {sorted(extra)}"
        )
