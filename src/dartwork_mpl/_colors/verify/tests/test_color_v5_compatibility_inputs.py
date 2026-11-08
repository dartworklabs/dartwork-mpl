"""The compatibility generator reads only its listed inputs, never writes one.

``scripts/freeze_color_v5_compatibility.py`` evaluates the v5 runtime from a
closed list of baseline files (``BASELINE_RUNTIME_INPUTS``) through the
shared ``scripts/frozen_baseline_inputs.py``. The extraction checks run on a
synthetic Git repository under ``tmp_path``; none reads the real accepted
commit or produces an archive, and a check that must refuse before Git runs
replaces ``subprocess.run`` with a stand-in that fails if called.

The output checks require ``--output`` and refuse a protected destination
and its aliases. They point the generator only at a synthetic protected
sentinel (``_protected_inputs`` is replaced), never at a real accepted file,
and stand-ins stop Git, extraction, compute and writes.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterator
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]
GENERATOR_PATH = REPO_ROOT / "scripts/freeze_color_v5_compatibility.py"
LISTED = "src/dartwork_mpl/listed.py"
UNLISTED = "src/dartwork_mpl/unlisted.py"
DOCS_DECOY = "docs/decoy.md"
ALIAS = "src/dartwork_mpl/alias.py"
DIRECTORY = "src/dartwork_mpl/pkg"
SENTINEL_BYTES = b"SYNTHETIC PROTECTED SENTINEL\n"
PROBE_TEXT_INPUTS = (
    "src/dartwork_mpl/asset/mplstyle/theme-dark.mplstyle",
    "src/dartwork_mpl/mcp/prompts.py",
    "src/dartwork_mpl/mcp/resources.py",
    "src/dartwork_mpl/mcp/tools.py",
)


@pytest.fixture(scope="module")
def generator() -> ModuleType:
    """Load the generator module without running its entry point."""
    specification = importlib.util.spec_from_file_location(
        "compatibility_generator_inputs_test", GENERATOR_PATH
    )
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def _git(repo: Path, *args: str) -> str:
    """Run Git in the synthetic repository with no user or system config."""
    environment = {
        **os.environ,
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "synthetic",
        "GIT_AUTHOR_EMAIL": "synthetic@example.invalid",
        "GIT_COMMITTER_NAME": "synthetic",
        "GIT_COMMITTER_EMAIL": "synthetic@example.invalid",
    }
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture
def synthetic_commit(tmp_path: Path) -> tuple[Path, str]:
    """Commit a listed file, decoys, a symlink and a directory."""
    repo = tmp_path / "repo"
    files = {
        LISTED: "VALUE = 'listed'\n",
        f"{DIRECTORY}/inner.py": "VALUE = 'inner'\n",
        UNLISTED: "VALUE = 'unlisted decoy'\n",
        DOCS_DECOY: "documentation decoy\n",
    }
    for relative, text in files.items():
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    (repo / ALIAS).symlink_to("../../docs/decoy.md")
    _git(repo, "init", "-q")
    _git(repo, "add", "--", *files, ALIAS)
    _git(repo, "commit", "-q", "--no-gpg-sign", "-m", "synthetic")
    return repo, _git(repo, "rev-parse", "HEAD")


@pytest.fixture
def no_git(
    generator: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> Iterator[None]:
    """Fail the test if the generator starts any process."""

    def refuse(*args: object, **kwargs: object) -> object:
        raise AssertionError(f"git was started: {args!r}")

    monkeypatch.setattr(generator.subprocess, "run", refuse)
    yield


def _files_below(root: Path) -> list[str]:
    """List the files this test's own destination holds."""
    if not root.exists():
        return []
    return sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() or path.is_symlink()
    )


def test_listed_file_is_extracted_byte_for_byte_and_nothing_else(
    generator: ModuleType, synthetic_commit: tuple[Path, str], tmp_path: Path
) -> None:
    """Positive control: exactly the listed file, with its committed bytes."""
    repo, commit = synthetic_commit
    destination = tmp_path / "destination"

    generator._extract_baseline_inputs(
        commit, destination, inputs=(LISTED,), repo=repo
    )

    assert _files_below(destination) == [LISTED]
    assert (destination / LISTED).read_bytes() == (repo / LISTED).read_bytes()


@pytest.mark.parametrize("command", ["archive", "ls-files", "checkout"])
def test_archive_request_is_refused_before_git_runs(
    generator: ModuleType, no_git: None, command: str, tmp_path: Path
) -> None:
    """The old whole-tree ``git archive`` request is refused, not run."""
    with pytest.raises(RuntimeError, match="not an allowed baseline read"):
        generator._run_git(command, "--format=tar", "HEAD", repo=tmp_path)


@pytest.mark.parametrize(
    ("path", "listed", "message"),
    [
        (UNLISTED, (LISTED,), "is not listed"),
        (DOCS_DECOY, (LISTED,), "is not listed"),
        ("src/dartwork_mpl/../../docs/decoy.md", None, "not a package"),
        ("/src/dartwork_mpl/listed.py", None, "not a package"),
        ("src/dartwork_mpl/*.py", None, "not a package"),
        (DOCS_DECOY, None, "not a package"),
    ],
)
def test_unlisted_or_escaping_path_is_refused_before_git_runs(
    generator: ModuleType,
    no_git: None,
    path: str,
    listed: tuple[str, ...] | None,
    message: str,
) -> None:
    """Membership and path shape are checked before any Git object read."""
    allowed = frozenset((path,) if listed is None else listed)
    with pytest.raises(RuntimeError, match=message):
        generator._read_baseline_input(
            "HEAD", path, listed=allowed, repo=REPO_ROOT
        )


@pytest.mark.parametrize(
    ("path", "message"),
    [
        (ALIAS, r"not a regular file \(mode 120000\)"),
        (DIRECTORY, r"not a regular file \(mode 040000\)"),
        ("src/dartwork_mpl/absent.py", "is missing from"),
    ],
    ids=["symlink", "directory", "missing"],
)
def test_alias_directory_and_missing_inputs_are_refused(
    generator: ModuleType,
    synthetic_commit: tuple[Path, str],
    tmp_path: Path,
    path: str,
    message: str,
) -> None:
    """Refuse instead of following an alias or expanding a directory."""
    repo, commit = synthetic_commit
    destination = tmp_path / "destination"

    with pytest.raises(RuntimeError, match=message):
        generator._extract_baseline_inputs(
            commit, destination, inputs=(path,), repo=repo
        )

    assert _files_below(destination) == []


def test_runtime_payload_extracts_the_listed_inputs_and_no_archive(
    generator: ModuleType, no_git: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The runtime path asks only for ``BASELINE_RUNTIME_INPUTS``.

    The extraction stand-in records the call and stops before the probe, so
    no baseline file is read and no process starts.
    """
    calls: list[tuple[str, Path]] = []

    def record(commit: str, destination: Path) -> None:
        calls.append((commit, destination))
        raise RuntimeError("stop before the probe")

    monkeypatch.setattr(generator, "_extract_baseline_inputs", record)

    with pytest.raises(RuntimeError, match="stop before the probe"):
        generator._baseline_runtime_payload("HEAD")

    [(commit, destination)] = calls
    assert commit == "HEAD"
    assert destination.name.startswith("dartwork-mpl-v5-compat-inputs-")
    assert destination.parent.resolve() == Path(tempfile.gettempdir()).resolve()
    assert not destination.exists()  # the temporary directory is removed


def test_runtime_input_list_is_a_closed_list_of_package_files(
    generator: ModuleType, no_git: None
) -> None:
    """Plain package files, no docs, every pinned source and probe text."""
    inputs = generator.BASELINE_RUNTIME_INPUTS
    package_sources = {
        path
        for path in generator.SOURCE_HASHES
        if path.startswith(generator.BASELINE_INPUT_PREFIX)
    }

    assert len(set(inputs)) == len(inputs)
    for path in inputs:
        generator._check_input_path(path)
    assert package_sources <= set(inputs)
    assert set(PROBE_TEXT_INPUTS) <= set(inputs)
    assert not [path for path in inputs if "superpowers" in path]
    assert generator._extract_baseline_inputs.__kwdefaults__["inputs"] is (
        inputs
    )


@pytest.fixture
def no_side_effects(
    generator: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> Iterator[None]:
    """Fail the test if ``main`` reaches Git, extraction, compute or a write."""

    def refuse(step: str) -> Callable[..., object]:
        def stand_in(*args: object, **kwargs: object) -> object:
            raise AssertionError(f"{step} was reached: {args!r}")

        return stand_in

    monkeypatch.setattr(generator.subprocess, "run", refuse("git"))
    for name, step in (
        ("_extract_baseline_inputs", "extraction"),
        ("_build_payload", "compute"),
        ("_atomic_write_text", "write"),
    ):
        monkeypatch.setattr(generator, name, refuse(step))
    yield


@pytest.fixture
def sentinel(
    generator: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """Make a synthetic file the only protected generator input."""
    path = tmp_path / "protected" / "sentinel.json"
    path.parent.mkdir()
    path.write_bytes(SENTINEL_BYTES)
    monkeypatch.setattr(generator, "_protected_inputs", lambda: (path,))
    return path


def _run_main(
    generator: ModuleType, monkeypatch: pytest.MonkeyPatch, *args: str
) -> None:
    """Run the generator's ``main`` in-process with ``args``."""
    monkeypatch.setattr(sys, "argv", [str(GENERATOR_PATH), *args])
    generator.main()


def test_missing_output_fails_before_git_extraction_or_writes(
    generator: ModuleType,
    no_side_effects: None,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """There is no default destination: ``--output`` is required."""
    with pytest.raises(SystemExit) as stopped:
        _run_main(generator, monkeypatch, "--baseline-commit", "HEAD")

    assert stopped.value.code == 2
    error = capsys.readouterr().err
    assert "--output" in error and "required" in error


def _alias(kind: str, sentinel: Path, tmp_path: Path) -> str:
    """Return one spelling or alias of ``sentinel`` as an ``--output``."""
    if kind == "exact":
        return str(sentinel)
    if kind == "dot-dot":
        return str(tmp_path / "protected" / ".." / "protected" / sentinel.name)
    if kind == "relative":
        return os.path.relpath(sentinel)
    if kind == "symlink":
        link = tmp_path / "link.json"
        link.symlink_to(sentinel)
        return str(link)
    if kind == "symlinked-parent":
        linked = tmp_path / "linked"
        linked.symlink_to(sentinel.parent, target_is_directory=True)
        return str(linked / sentinel.name)
    if kind == "hard-link":
        hard = tmp_path / "hard.json"
        os.link(sentinel, hard)
        return str(hard)
    raise AssertionError(kind)


ALIASES = (
    "exact",
    "dot-dot",
    "relative",
    "symlink",
    "symlinked-parent",
    "hard-link",
)


@pytest.mark.parametrize("kind", ALIASES)
def test_protected_destination_is_refused_before_git_and_left_unchanged(
    generator: ModuleType,
    no_side_effects: None,
    sentinel: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    """An explicit ``--output`` may not name a protected input or an alias."""
    monkeypatch.chdir(tmp_path)
    destination = _alias(kind, sentinel, tmp_path)

    with pytest.raises(ValueError, match="names a protected generator input"):
        _run_main(
            generator,
            monkeypatch,
            "--baseline-commit",
            "HEAD",
            "--output",
            destination,
        )

    assert sentinel.read_bytes() == SENTINEL_BYTES


@pytest.mark.parametrize("kind", ALIASES)
def test_writer_refuses_a_protected_alias_at_write_time(
    generator: ModuleType,
    sentinel: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    """The final write checks again, so a later alias is refused too."""
    monkeypatch.chdir(tmp_path)
    destination = Path(_alias(kind, sentinel, tmp_path))

    with pytest.raises(ValueError, match="protected generator input"):
        generator._write_output(destination, "{}\n")

    assert sentinel.read_bytes() == SENTINEL_BYTES


def test_owned_destinations_are_accepted_and_written(
    generator: ModuleType, sentinel: Path, tmp_path: Path
) -> None:
    """A new file, or an unrelated existing one, is an allowed output."""
    fresh = tmp_path / "owned" / "compatibility.json"
    existing = tmp_path / "existing.json"
    existing.write_bytes(b"old\n")

    for destination in (fresh, existing):
        generator._write_output(destination, "{}\n")
        assert destination.read_text(encoding="utf-8") == "{}\n"
    assert sentinel.read_bytes() == SENTINEL_BYTES


def test_protected_inputs_name_the_fixtures_and_every_pinned_source(
    generator: ModuleType,
) -> None:
    """Compare paths only; no file is opened or written."""
    expected = {
        generator.COMPATIBILITY_PATH,
        generator.QUALITY_PATH,
        *(generator.REPO_ROOT / path for path in generator.SOURCE_HASHES),
    }

    assert set(generator._protected_inputs()) == expected
    assert generator.COMPATIBILITY_PATH.relative_to(generator.REPO_ROOT) == (
        Path(
            "docs/superpowers/specs/assets/"
            "2026-07-14-oklab-centered-color-system/color_v5_compatibility.json"
        )
    )
